from __future__ import annotations

from typing import Any

from agentic_systems.providers.bedrock_runtime import BedrockRuntime


class CapturingConverseClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return {
                "output": {
                    "message": {
                        "content": [
                            {
                                "toolUse": {
                                    "toolUseId": "tooluse-1",
                                    "name": "sumar",
                                    "input": {"a": 17, "b": 25},
                                }
                            }
                        ]
                    }
                },
                "stopReason": "tool_use",
                "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
                "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "req-1"},
            }
        return {
            "output": {"message": {"content": [{"text": "42"}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
            "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "req-2"},
        }


def test_bedrock_runtime_converse_builds_tool_config() -> None:
    runtime = BedrockRuntime(model_id="unit-test-model", region_name="us-east-1")
    capture = CapturingConverseClient()
    runtime.runtime = capture

    response = runtime.converse(
        messages=[{"role": "user", "content": [{"text": "suma"}]}],
        tools=[{"toolSpec": {"name": "sumar", "description": "Suma", "inputSchema": {"json": {"type": "object"}}}}],
        tool_choice={"auto": {}},
    )

    assert response["stopReason"] == "tool_use"
    request = capture.calls[0]
    assert request["modelId"] == "unit-test-model"
    assert request["messages"][0]["role"] == "user"
    assert request["toolConfig"]["tools"][0]["toolSpec"]["name"] == "sumar"
    assert request["toolConfig"]["toolChoice"] == {"auto": {}}


def test_run_direct_uses_converse_tool_use_and_tool_result_loop() -> None:
    runtime = BedrockRuntime(model_id="unit-test-model", region_name="us-east-1")
    capture = CapturingConverseClient()
    runtime.runtime = capture

    @runtime.tool
    def sumar(a: int, b: int) -> dict:
        """Suma dos enteros."""
        return {"result": a + b}

    result = runtime.run_direct("Suma 17 y 25", max_turns=3)

    assert result.final_text == "42"
    assert len(capture.calls) == 2

    first_request = capture.calls[0]
    assert "messages" in first_request
    assert "toolConfig" in first_request
    assert first_request["toolConfig"]["tools"][0]["toolSpec"]["name"] == "sumar"

    second_request = capture.calls[1]
    second_messages = second_request["messages"]
    assert any("toolUse" in block for block in second_messages[1]["content"])
    tool_result_blocks = second_messages[2]["content"]
    assert any("toolResult" in block for block in tool_result_blocks)
    tool_result = next(block["toolResult"] for block in tool_result_blocks if "toolResult" in block)
    assert tool_result["toolUseId"] == "tooluse-1"
    assert tool_result["content"][0]["json"]["data"] == {"result": 42}
