from __future__ import annotations

import json
from typing import Any

import agentic_systems as toolkit
from agentic_systems.engines.bedrock import BedrockEngine


def echo(value: str) -> dict:
    return {"value": value}


class FakeBedrockConverseRuntime:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        messages = kwargs["messages"]
        tool_results = [
            block["toolResult"]
            for block in messages[-1]["content"]
            if "toolResult" in block
        ]
        if tool_results:
            value = tool_results[0]["content"][0].get("json")
            return _response([{"text": json.dumps(value)}], request_id="final")
        tool_name = kwargs["tools"][0]["toolSpec"]["name"]
        return _response(
            [
                {
                    "toolUse": {
                        "toolUseId": "bedrock-call-1",
                        "name": tool_name,
                        "input": {"value": "ok"},
                    }
                }
            ],
            request_id="tool",
        )


def _response(content: list[dict[str, Any]], *, request_id: str) -> dict[str, Any]:
    return {
        "output": {"message": {"role": "assistant", "content": content}},
        "usage": {"inputTokens": 2, "outputTokens": 3, "totalTokens": 5},
        "ResponseMetadata": {"RequestId": request_id},
    }


def test_openai_agents_owns_the_bedrock_tool_loop():
    system = toolkit.AgenticSystem(model="fake-bedrock")
    agent = system.agent(
        name="bedrock-openai",
        instructions="Use the Tool.",
        tools=[toolkit.tool(echo)],
        engine="bedrock-runtime",
        framework="openai-agents",
        policy=toolkit.RunPolicy(max_tool_calls=1),
    )
    runtime = FakeBedrockConverseRuntime()
    system._runtime = runtime
    system._engines["bedrock-runtime"] = BedrockEngine(system)

    result = agent.run({"value": "ignored"})

    assert result.ok is True
    assert result.data == {"value": "ok"}
    assert result.meta["framework_adapter"] == "openai-agents"
    assert type(result.native_result).__name__ == "RunResult"
    assert len(result.tool_events) == 1
    assert len(runtime.calls) == 2
    assert runtime.calls[0]["tools"][0]["toolSpec"]["name"] == "echo"
    assert runtime.calls[1]["tools"][0]["toolSpec"]["name"] == "echo"
    assert "toolResult" in runtime.calls[1]["messages"][-1]["content"][0]
