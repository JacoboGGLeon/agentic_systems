"""Converse wire regressions through the real three SDK loops, with no HTTP."""

from copy import deepcopy
import json

import pydantic
import pytest

import agentic_systems as toolkit
from agentic_systems._engine.providers.bedrock.schema import bedrock_strict_tools
from agentic_systems._engine.providers.bedrock.converse import _ConverseMixin
from examples.applications.data_quality.example import Payload, Row, sample


MODEL = "qwen.qwen3-32b-v1:0"


def tool_spec(schema=None):
    return {"toolSpec": {
        "name": "profile_rows", "description": "Inspect original rows",
        "inputSchema": {"json": schema if schema is not None else Row.model_json_schema()},
    }}


def test_wire_enforcement_preserves_required_nullable_schema_and_caller_objects():
    original = [tool_spec(), {"cachePoint": {"type": "default"}}]
    before = deepcopy(original)
    projected = bedrock_strict_tools(original, MODEL)
    assert original == before and projected is not original
    spec = projected[0]["toolSpec"]
    assert spec["strict"] is True
    assert spec["inputSchema"] == original[0]["toolSpec"]["inputSchema"]
    schema = spec["inputSchema"]["json"]
    assert set(schema["required"]) == {"id", "amount"}
    assert {"type": "null"} in schema["properties"]["amount"]["anyOf"]
    assert projected[1] == original[1]


@pytest.mark.parametrize("schema", [
    {"type": "object", "properties": {"amount": {"type": "integer"}}},
    {"type": "object", "additionalProperties": True},
    {"type": "integer", "minimum": 1},
    {"oneOf": [{"type": "integer"}, {"type": "null"}]},
    {"type": "object", "additionalProperties": False, "properties": {"data": {}}},
    {"$ref": "https://example.invalid/schema"},
    {"$defs": {"Loop": {"$ref": "#/$defs/Loop"}}, "$ref": "#/$defs/Loop"},
    {"type": "object", "additionalProperties": False,
     "properties": {f"optional_{i}": {"type": "integer"} for i in range(13)}},
])
def test_unsupported_schema_is_never_weakened_to_enable_strict(schema):
    original = [tool_spec(schema)]
    assert bedrock_strict_tools(original, MODEL) == original


def test_other_models_and_explicit_sdk_choices_are_preserved():
    original = [tool_spec()]
    assert bedrock_strict_tools(original, "unverified-model") == original
    for strict in (True, False):
        explicit = deepcopy(original)
        explicit[0]["toolSpec"]["strict"] = strict
        assert bedrock_strict_tools(explicit, MODEL) == explicit


def test_strict_optional_property_budget_is_request_wide():
    schema = {"type": "object", "additionalProperties": False,
              "properties": {f"optional_{i}": {"type": "integer"} for i in range(7)}}
    original = [tool_spec(schema), tool_spec(schema)]
    original[1]["toolSpec"]["name"] = "another_tool"
    result = bedrock_strict_tools(original, MODEL)
    assert result[0]["toolSpec"]["strict"] is True
    assert "strict" not in result[1]["toolSpec"]
    assert result[1] == original[1]


def test_nullable_default_does_not_become_a_required_or_imputed_value():
    class OptionalRow(pydantic.BaseModel):
        model_config = pydantic.ConfigDict(extra="forbid", strict=True)
        id: int
        amount: int | None = None

    original = [tool_spec(OptionalRow.model_json_schema())]
    result = bedrock_strict_tools(original, MODEL)
    schema = result[0]["toolSpec"]["inputSchema"]["json"]
    assert result[0]["toolSpec"]["strict"] is True
    assert schema == original[0]["toolSpec"]["inputSchema"]["json"]
    assert schema["required"] == ["id"]  # Never rewrite optional into required.
    assert schema["properties"]["amount"]["default"] is None


def test_service_rejection_is_not_retried_with_weaker_decoding():
    from types import SimpleNamespace
    from botocore.exceptions import ClientError

    calls = []

    def reject(**kwargs):
        calls.append(kwargs)
        raise ClientError(
            {"Error": {"Code": "ValidationException", "Message": "strict schema rejected"}},
            "Converse",
        )

    runtime = SimpleNamespace(
        runtime=SimpleNamespace(converse=reject), model_id=MODEL,
        max_tokens_default=512, temperature_default=0,
    )
    with pytest.raises(ClientError, match="strict schema rejected"):
        _ConverseMixin.converse(
            runtime, messages=[{"role": "user", "content": [{"text": "Inspect"}]}],
            tools=[tool_spec()],
        )
    assert len(calls) == 1
    assert calls[0]["toolConfig"]["tools"][0]["toolSpec"]["strict"] is True


@pytest.mark.parametrize("framework", ("native", "openai-agents", "strands"))
@pytest.mark.parametrize("omit_amount", (False, True))
def test_nullable_input_through_real_framework_sdk(monkeypatch, framework, omit_amount):
    from agents import set_tracing_disabled
    from botocore.client import BaseClient

    set_tracing_disabled(True)
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "offline-test-bearer")
    monkeypatch.setenv("BEDROCK_STREAMING", "false")
    calls, effects = [], []
    incoming = deepcopy(sample)
    if omit_amount:
        del incoming["rows"][1]["amount"]

    @toolkit.tool
    def inspect_rows(rows: list[Row]) -> dict:
        payload = Payload(rows=rows).model_dump(mode="json")
        effects.append(payload["rows"])
        return {"rows": len(rows), "missing_amounts": sum(row["amount"] is None for row in payload["rows"])}

    def converse(client, operation, arguments):
        assert operation == "Converse"
        assert arguments["modelId"] == MODEL
        operation_model = client.meta.service_model.operation_model(operation)
        encoded = client._serializer.serialize_to_request(arguments, operation_model)
        if "toolConfig" not in arguments:
            # Native final synthesis intentionally carries no Tool definitions.
            assert calls and framework == "native"
            calls.append(deepcopy(arguments))
            return {"output": {"message": {"role": "assistant", "content": [{"text": '{"rows":2,"missing_amounts":1}'}]}},
                    "stopReason": "end_turn", "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2}}
        assert json.loads(encoded["body"])["toolConfig"] == arguments["toolConfig"]
        assert client.meta.config.read_timeout >= 120
        spec = arguments["toolConfig"]["tools"][0]["toolSpec"]
        assert spec["strict"] is True
        row_schema = spec["inputSchema"]["json"]["$defs"]["Row"]
        assert set(row_schema["required"]) == {"id", "amount"}
        assert {"type": "null"} in row_schema["properties"]["amount"]["anyOf"]
        calls.append(deepcopy(arguments))
        if len(calls) == 1:
            content = [{"toolUse": {"toolUseId": "offline-call", "name": spec["name"], "input": incoming}}]
        else:
            content = [{"text": "Invalid required input" if omit_amount else '{"rows":2,"missing_amounts":1}'}]
        return {"output": {"message": {"role": "assistant", "content": content}},
                "stopReason": "tool_use" if len(calls) == 1 else "end_turn",
                "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
                "metrics": {"latencyMs": 1},
                "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "offline-only"}}

    monkeypatch.setattr(BaseClient, "_make_api_call", converse)
    actor = toolkit.Agent(
        "null_replay", runtime=toolkit.runtime(provider="bedrock-runtime", model=MODEL,
            region="us-east-2", api_key="offline-test-bearer", max_turns=2,
            max_tool_calls=1, max_retries=0, max_tokens=512),
        framework=toolkit.framework(framework),
        skills=(toolkit.skill(name="quality", tools=(inspect_rows,)),),
        contract={"tool_expectation": {"all_of": [inspect_rows.name]},
                  "completion": "when_required_tools_satisfied"},
        policy={"repair": False},
    )
    result = actor.run(sample)
    assert 1 <= len(calls) <= 2, json.dumps(result.to_dict())
    assert result.ok is (not omit_amount), json.dumps(result.to_dict())
    assert effects == ([] if omit_amount else [sample["rows"]])
    serialized = json.loads(json.dumps(result.to_dict()))
    assert toolkit.RunResult(**serialized).check_invariants().ok
    original_text = calls[0]["messages"][0]["content"][0]["text"]
    assert json.loads(original_text) == sample
    if omit_amount:
        assert "Field required" in json.dumps(serialized)
        assert "amount" in json.dumps(serialized)
    else:
        events = [event for run in result.walk() for event in run.tool_events]
        assert len(events) == 1 and events[0].input == sample
        output = events[0].output
        expected = {"rows": 2, "missing_amounts": 1}
        assert output == expected or output.get("data") == expected


def test_required_nullable_remains_distinct_from_optional_and_from_zero():
    assert Row(id=1, amount=None).amount is None
    assert Row(id=1, amount=0).amount == 0
    with pytest.raises(pydantic.ValidationError):
        Row(id=1)
    with pytest.raises(pydantic.ValidationError):
        Row(id=1, amount="null")
