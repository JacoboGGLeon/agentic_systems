"""Framework-specific SDK objects at the documented framework options boundary."""

import asyncio
import json
from uuid import uuid4


def handoff_destination(provider, options, observed):
    from agents import Agent, Model, ModelResponse, ModelSettings, handoff
    from agents.usage import Usage
    from openai.types.responses import ResponseOutputMessage, ResponseOutputText

    class SpecialistModel(Model):
        async def get_response(self, *args, **kwargs):
            if provider == "python-runtime":
                text, usage = "SPECIALIST_OK", Usage()
            elif provider == "bedrock-runtime":
                import boto3
                from botocore.config import Config

                client = boto3.client(
                    "bedrock-runtime",
                    region_name=options["region"],
                    config=Config(
                        retries={"max_attempts": 0}, read_timeout=30, connect_timeout=10
                    ),
                )
                response = await asyncio.to_thread(
                    client.converse,
                    modelId=options["model"],
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": "Reply exactly SPECIALIST_OK. This is a handoff integration test."
                                }
                            ],
                        }
                    ],
                    inferenceConfig={"maxTokens": 128},
                )
                text = "".join(
                    block.get("text", "")
                    for block in response["output"]["message"]["content"]
                )
                counts = response.get("usage", {})
                usage = Usage(
                    requests=1,
                    input_tokens=counts.get("inputTokens", 0),
                    output_tokens=counts.get("outputTokens", 0),
                )
            else:
                raise RuntimeError("Unexpected specialist provider")
            return ModelResponse(
                output=[
                    ResponseOutputMessage(
                        id="msg_" + uuid4().hex,
                        type="message",
                        role="assistant",
                        status="completed",
                        content=[
                            ResponseOutputText(
                                type="output_text", annotations=[], text=text
                            )
                        ],
                    )
                ],
                usage=usage,
                response_id=None,
            )

        async def stream_response(self, *args, **kwargs):
            raise NotImplementedError("The conformance case uses non-streaming calls")
            yield

    if provider in {"openai-runtime", "ollama-runtime"}:
        from agents import OpenAIChatCompletionsModel
        from openai import AsyncOpenAI

        model = OpenAIChatCompletionsModel(
            model=options["model"],
            openai_client=AsyncOpenAI(
                api_key=options["api_key"],
                base_url=options["endpoint"] or "https://api.openai.com/v1",
                max_retries=0,
                timeout=30,
            ),
        )
    else:
        model = SpecialistModel()
    destination = Agent(
        name="billing_specialist",
        model=model,
        instructions="You own the response after handoff. Reply exactly SPECIALIST_OK.",
        model_settings=ModelSettings(max_tokens=128),
    )

    def record(context):
        observed.append({"from": "triage", "to": "billing_specialist"})

    return handoff(destination, on_handoff=record)


def strands_fixture_model():
    from strands.models import Model

    class EchoModel(Model):
        def __init__(self):
            self.config = {"model_id": "deterministic-a2a-fixture"}

        def update_config(self, **options):
            self.config.update(options)

        def get_config(self):
            return dict(self.config)

        async def structured_output(self, *args, **kwargs):
            raise NotImplementedError
            yield

        async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
            outputs = [
                block["toolResult"]
                for message in messages
                for block in message.get("content", [])
                if "toolResult" in block
            ]
            yield {"messageStart": {"role": "assistant"}}
            if outputs:
                yield {"contentBlockStart": {"start": {}}}
                yield {
                    "contentBlockDelta": {
                        "delta": {"text": json.dumps(outputs, ensure_ascii=False)}
                    }
                }
                yield {"contentBlockStop": {}}
                yield {"messageStop": {"stopReason": "end_turn"}}
            else:
                texts = [
                    b.get("text", "")
                    for m in messages
                    if m.get("role") == "user"
                    for b in m.get("content", [])
                ]
                payload = json.loads(texts[-1])
                yield {
                    "contentBlockStart": {
                        "start": {
                            "toolUse": {
                                "toolUseId": "call_" + uuid4().hex,
                                "name": payload["tool"],
                            }
                        }
                    }
                }
                yield {
                    "contentBlockDelta": {
                        "delta": {"toolUse": {"input": json.dumps(payload["input"])}}
                    }
                }
                yield {"contentBlockStop": {}}
                yield {"messageStop": {"stopReason": "tool_use"}}
            yield {
                "metadata": {
                    "usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
                    "metrics": {"latencyMs": 0},
                }
            }

    return EchoModel()
