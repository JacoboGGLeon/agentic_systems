from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError

from agentic_systems.providers.bedrock.identity import _IdentityMixin
from agentic_systems.providers.bedrock.langgraph import _LangGraphMixin
from agentic_systems.providers.bedrock.models import (
    BedrockRunResult,
    RuntimeToolCallRecord,
)


def _client_error(code: str, message: str = "denied") -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": message}},
        "BedrockOperation",
    )


class IdentityRuntime(_IdentityMixin):
    model_id = "model-a"
    region_name = "us-test-1"

    def __init__(self, bedrock, identity=None):
        self.bedrock = bedrock
        self.sts = SimpleNamespace(
            get_caller_identity=lambda: (
                identity
                or {
                    "Account": "123456789012",
                    "Arn": "arn:aws:sts::123456789012:assumed-role/team/session-name",
                    "UserId": "ABCDEFGHIJKLMNOP:session-name",
                }
            )
        )

    @staticmethod
    def _make_jsonable(value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {
                key: IdentityRuntime._make_jsonable(item) for key, item in value.items()
            }
        if isinstance(value, list):
            return [IdentityRuntime._make_jsonable(item) for item in value]
        return value

    @staticmethod
    def _summarize_model_metadata(value):
        return {"summary": value.get("modelDetails", value)}


def test_identity_masking_and_redaction_contracts():
    runtime = IdentityRuntime(SimpleNamespace())
    plain = runtime.whoami()
    assert plain["account"] == "123456789012"
    assert plain["region"] == "us-test-1"

    masked = runtime.whoami(mask=True)
    assert masked["account"] == "123456******"
    assert masked["redacted"] is True
    assert "123456789012" not in masked["arn"]
    assert "..." in masked["user_id"]

    assert runtime._mask_middle(None) is None
    assert runtime._mask_middle("short") == "*****"
    assert runtime._mask_middle("abcdefghijkl") == "abcdef...ijkl"
    short = runtime.redact_aws_identity(
        {"account": "123", "user_id": "u", "arn": "arn:short"}
    )
    assert short["account"] == "***"
    assert short["arn"] == "arn:short"
    assert runtime.redact_aws_identity({}) == {"redacted": True}


def test_model_availability_exact_lookup_and_iam_denial():
    exact = SimpleNamespace(
        get_foundation_model=lambda **kwargs: {
            "modelDetails": {"modelId": kwargs["modelIdentifier"]},
            "updatedAt": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
    )
    runtime = IdentityRuntime(exact)
    full = runtime.model_availability()
    assert full["ok"] is True
    assert full["availability"]["updatedAt"].startswith("2026-01-01")
    compact = runtime.model_availability("model-b", full_metadata=False)
    assert compact["availability"] == {"summary": {"modelId": "model-b"}}

    def denied(**kwargs):
        raise _client_error("AccessDeniedException")

    unknown = IdentityRuntime(SimpleNamespace(get_foundation_model=denied))
    result = unknown.model_availability()
    assert result["ok"] is None
    assert result["availability"] == "unknown_due_to_iam"


def test_model_availability_fallbacks_and_client_capabilities():
    def missing(**kwargs):
        raise _client_error("ResourceNotFoundException", "missing")

    listed = SimpleNamespace(
        get_foundation_model=missing,
        list_foundation_models=lambda: {
            "modelSummaries": [
                {"modelId": "other"},
                {"foundationModelId": "model-a", "modelName": "A"},
                {"modelArn": "arn:model"},
            ]
        },
    )
    result = IdentityRuntime(listed).model_availability(full_metadata=False)
    assert result["ok"] is True
    assert result["matched"] == [
        {"summary": {"foundationModelId": "model-a", "modelName": "A"}}
    ]
    assert (
        result["previous_get_foundation_model_error"]["error_code"]
        == "ResourceNotFoundException"
    )

    only_list = SimpleNamespace(list_foundation_models=lambda: {"modelSummaries": []})
    result = IdentityRuntime(only_list).model_availability()
    assert result["ok"] is False
    assert (
        result["previous_get_foundation_model_error"]["error_code"]
        == "MethodNotAvailable"
    )

    def list_denied():
        raise _client_error("ThrottlingException", "slow down")

    failed = IdentityRuntime(SimpleNamespace(list_foundation_models=list_denied))
    result = failed.model_availability()
    assert result["availability"] == "unknown_due_to_error"
    assert result["error_code"] == "ThrottlingException"

    none = IdentityRuntime(SimpleNamespace()).model_availability()
    assert none["check"] == "none"
    assert none["availability"] == "unknown_due_to_client_capability"


def _record(identifier: str, name: str, ok: bool, data):
    return RuntimeToolCallRecord(
        tool_use_id=identifier,
        tool_name=name,
        tool_input={"value": identifier},
        tool_output={"kind": "object", "data": data},
        ok=ok,
    )


def test_bedrock_run_result_traces_recovery_usage_and_modes():
    result = BedrockRunResult(
        final_text="done",
        messages=[{"role": "user"}, {"role": "assistant"}],
        tool_calls=[
            _record("c1", "lookup", False, {"error_type": "ValidationError"}),
            _record("c2", "lookup", True, {"value": 1}),
            _record("c3", "other", False, "raw failure"),
        ],
        raw_responses=[
            {
                "usage": {"inputTokens": 2, "outputTokens": 3, "totalTokens": 5},
                "stop_reason": "tool_use",
            },
            {"usage": None, "stop_reason": "end_turn"},
        ],
    )
    compact = result.compact_trace()
    assert compact["usage_totals"] == {
        "input_tokens": 2,
        "output_tokens": 3,
        "total_tokens": 5,
        "requests": 2,
    }
    assert compact["recovered_tool_error_count"] == 1
    assert compact["unresolved_failed_tool_count"] == 1
    assert compact["run_ok"] is False
    assert compact["tools"][2]["error_type"] is None
    assert compact["stop_reasons"] == ["tool_use", "end_turn"]
    assert result.trace(mode="compact") == compact
    assert result.trace(mode="full") == result.to_dict()
    with pytest.raises(ValueError, match="compact.*full"):
        result.trace(mode="invalid")

    clean = BedrockRunResult(final_text="done", messages=[])
    assert clean.compact_trace()["run_ok"] is True


class GraphRuntime(_LangGraphMixin):
    def __init__(self):
        self.calls = []

    def run_direct(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return BedrockRunResult(final_text=f"answer:{prompt}", messages=[])


def test_langgraph_node_forwards_every_runtime_option_and_prompt_fallback():
    runtime = GraphRuntime()
    node = runtime.as_langgraph_node(
        instructions="system",
        tool_choice="required",
        tool_names=["lookup"],
        max_turns=4,
        max_tool_calls=2,
        max_tokens=80,
        temperature=0.2,
        retry_tool_errors=False,
        max_tool_error_repairs=1,
        synthesize_final_on_max_turns=False,
        required_tools=["lookup"],
        stop_when_required_tools_ok=True,
        input_key="question",
        output_key="answer",
        trace_key="trace",
        trace_mode="full",
    )
    state = node({"question": "hello", "kept": True})
    assert state["answer"] == "answer:hello"
    assert state["kept"] is True
    assert runtime.calls[0][1]["max_tool_calls"] == 2
    assert runtime.calls[0][1]["required_tools"] == ["lookup"]

    fallback = runtime.as_langgraph_node(input_key="missing")
    assert fallback({"user_request": "from-user"})["final_text"] == "answer:from-user"
    assert fallback({"input": "from-input"})["final_text"] == "answer:from-input"
    serialized = fallback({"other": 1})["final_text"]
    assert serialized == 'answer:{"other": 1}'
