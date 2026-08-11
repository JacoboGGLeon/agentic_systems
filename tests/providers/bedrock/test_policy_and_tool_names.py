from __future__ import annotations

import os
from typing import Any

from agentic_systems.contracts import RunPolicy
from agentic_systems.providers.bedrock_runtime import BedrockRuntime


os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")


class NamespacedToolClient:
    def __init__(self, safe_name: str) -> None:
        self.safe_name = safe_name
        self.calls: list[dict[str, Any]] = []

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        has_tool_result = any(
            "toolResult" in block
            for message in kwargs.get("messages", [])
            for block in message.get("content", [])
            if isinstance(block, dict)
        )
        if not has_tool_result:
            return {
                "output": {
                    "message": {
                        "content": [
                            {
                                "toolUse": {
                                    "toolUseId": "tooluse-1",
                                    "name": self.safe_name,
                                    "input": {"customer_id": "123"},
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
            "output": {"message": {"content": [{"text": "cliente listo"}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
            "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "req-2"},
        }


class TwoToolCallsClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        has_tool_result = any(
            "toolResult" in block
            for message in kwargs.get("messages", [])
            for block in message.get("content", [])
            if isinstance(block, dict)
        )
        if not has_tool_result:
            return {
                "output": {
                    "message": {
                        "content": [
                            {"toolUse": {"toolUseId": "tooluse-1", "name": "sumar", "input": {"a": 1, "b": 2}}},
                            {"toolUse": {"toolUseId": "tooluse-2", "name": "sumar", "input": {"a": 3, "b": 4}}},
                        ]
                    }
                },
                "stopReason": "tool_use",
                "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
                "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "req-1"},
            }
        return {
            "output": {"message": {"content": [{"text": "final"}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
            "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "req-2"},
        }


def test_run_policy_accepts_max_tool_calls() -> None:
    policy = RunPolicy.for_mode("eval").merge({"max_tool_calls": 4})
    assert policy.max_tool_calls == 4


def test_bedrock_runtime_maps_namespaced_tools_to_safe_converse_names() -> None:
    runtime = BedrockRuntime(model_id="unit-test-model", region_name="us-east-1")
    canonical = "customer_risk.get_customer"
    safe = runtime.bedrock_safe_tool_name(canonical)
    runtime.runtime = NamespacedToolClient(safe)

    @runtime.tool(name=canonical)
    def get_customer(customer_id: str) -> dict:
        """Obtiene un cliente."""
        return {"customer_id": customer_id}

    result = runtime.run_direct("Busca cliente 123", max_turns=3)

    first_request = runtime.runtime.calls[0]
    assert first_request["toolConfig"]["tools"][0]["toolSpec"]["name"] == safe
    assert safe != canonical
    assert result.tool_calls[0].tool_name == canonical
    assert result.tool_calls[0].meta["bedrock_tool_name"] == safe
    assert result.tool_calls[0].tool_output["meta"]["canonical_tool_name"] == canonical


def test_bedrock_runtime_enforces_max_tool_calls_without_business_hardcodes() -> None:
    runtime = BedrockRuntime(model_id="unit-test-model", region_name="us-east-1")
    runtime.runtime = TwoToolCallsClient()

    @runtime.tool
    def sumar(a: int, b: int) -> dict:
        """Suma dos enteros."""
        return {"result": a + b}

    result = runtime.run_direct("Ejecuta dos sumas", max_turns=3, max_tool_calls=1)

    assert result.final_text == "final"
    assert [call.ok for call in result.tool_calls] == [True, False]
    assert result.tool_calls[1].tool_output["data"]["error_type"] == "MaxToolCallsExceeded"
