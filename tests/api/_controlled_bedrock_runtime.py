"""Deterministic test doubles for Agentic Systems notebooks and tests."""

from __future__ import annotations

from typing import Any


class ControlledBedrockRuntime:
    """Deterministic Bedrock Converse double for notebooks and unit tests.

    The class implements the minimal ``converse(**kwargs)`` shape used by the
    Bedrock engine. It proves tool calling, contracts, traces, evals and
    environments without contacting AWS.
    """

    def __init__(
        self,
        final_text: str = "Resultado final controlado: 42",
        *,
        tool_name: str = "sumar",
        tool_input: dict[str, Any] | None = None,
        tool_input_mapper: Any | None = None,
    ) -> None:
        self.final_text = final_text
        self.tool_name = tool_name
        self.tool_input = tool_input or {"a": 17, "b": 25}
        self.tool_input_mapper = tool_input_mapper
        self.calls: list[dict[str, Any]] = []

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        messages = kwargs.get("messages", [])
        has_tool_result = any(
            "toolResult" in block
            for message in messages
            for block in message.get("content", [])
            if isinstance(block, dict)
        )
        has_synthesis = any(
            "BedrockRuntime final synthesis instruction" in block.get("text", "")
            for message in messages
            for block in message.get("content", [])
            if isinstance(block, dict)
        )
        if kwargs.get("toolConfig") and not has_tool_result and not has_synthesis:
            return {
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "toolUse": {
                                    "toolUseId": "controlled-tool-1",
                                    "name": self.tool_name,
                                    "input": self._resolve_tool_input(kwargs),
                                }
                            }
                        ],
                    }
                },
                "stopReason": "tool_use",
                "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
                "ResponseMetadata": {"RequestId": "controlled-1", "HTTPStatusCode": 200},
            }
        return {
            "output": {"message": {"role": "assistant", "content": [{"text": self.final_text}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 8, "outputTokens": 4, "totalTokens": 12},
            "ResponseMetadata": {"RequestId": "controlled-2", "HTTPStatusCode": 200},
        }

    def _resolve_tool_input(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        if self.tool_input_mapper is None:
            return self.tool_input
        value = self.tool_input_mapper(kwargs)
        return value if isinstance(value, dict) else {"value": value}


def attach_controlled_runtime(system: Any, runtime: ControlledBedrockRuntime | None = None) -> ControlledBedrockRuntime:
    """Attach a deterministic Converse runtime to an AgenticSystem instance."""

    selected = runtime or ControlledBedrockRuntime()
    system._runtime.runtime = selected
    return selected
