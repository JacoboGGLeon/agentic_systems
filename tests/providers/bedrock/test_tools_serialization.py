from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Literal

import pytest
from pydantic import BaseModel, create_model

from agentic_systems.providers.bedrock.models import RuntimeToolSpec, ToolEnvelope
from agentic_systems.providers.bedrock.tools import _ToolsMixin


class ToolsRuntime(_ToolsMixin):
    def __init__(self):
        self._tools = {}


class Payload(BaseModel):
    value: int


@dataclass
class Record:
    value: int


def test_tool_registration_selection_export_and_print(capsys):
    runtime = ToolsRuntime()

    @runtime.tool
    def direct(value: int = 1) -> dict:
        """Direct tool."""
        return {"value": value}

    @runtime.tool(name="custom", description="Custom description")
    def deferred(text):
        return {"text": text}

    assert direct(value=2) == {"value": 2}
    assert deferred("x") == {"text": "x"}
    assert [spec.name for spec in runtime.tools] == ["direct", "custom"]
    assert (
        runtime.export_tool_specs(["custom"])[0]["description"] == "Custom description"
    )
    runtime.print_tool_specs()
    assert '"name": "direct"' in capsys.readouterr().out
    with pytest.raises(KeyError, match="Unknown tools"):
        runtime._select_tools(["missing"])


def test_input_models_reject_variadics_and_preserve_defaults():
    def supported(required: int, optional: str = "x"):
        return required, optional

    model = ToolsRuntime._build_input_model("supported", inspect.signature(supported))
    assert model(required=1).optional == "x"

    def variadic(*args):
        return args

    with pytest.raises(TypeError, match="cannot use"):
        ToolsRuntime._build_input_model("variadic", inspect.signature(variadic))


def test_bedrock_tools_resolve_deferred_literal_annotations():
    runtime = ToolsRuntime()

    @runtime.tool
    def judge(failed_criteria: list[Literal["clarity", "evidence"]]) -> dict:
        return {"failed_criteria": failed_criteria}

    schema = runtime.export_tool_specs(["judge"])[0]["input_schema"]
    assert schema["properties"]["failed_criteria"]["items"]["enum"] == [
        "clarity",
        "evidence",
    ]


def test_registry_validation_reports_each_static_contract_issue():
    runtime = ToolsRuntime()
    input_model = create_model("BadInput", value=(object, ...))

    def untyped(value):
        return value

    runtime._tools[""] = RuntimeToolSpec(
        name="",
        description=" ",
        func=untyped,
        signature=inspect.signature(untyped),
        input_model=input_model,
        input_schema={"type": "array", "additionalProperties": True},
    )
    report = runtime.validate_tool_registry()
    issues = {item["issue"] for item in report["issues"]}
    assert report["ok"] is False
    assert issues == {
        "tool_name_must_be_non_empty_string",
        "tool_description_is_empty",
        "input_schema_type_must_be_object",
        "input_schema_missing_properties",
        "additionalProperties_should_be_false",
        "parameter_missing_type_annotation",
    }


def test_jsonable_metadata_and_payload_shapes(monkeypatch):
    assert ToolsRuntime._make_jsonable(Payload(value=1)) == {"value": 1}
    assert ToolsRuntime._make_jsonable(Record(2)) == {"value": 2}
    assert ToolsRuntime._make_jsonable({"x": 1}) == {"x": 1}
    assert "object at" in ToolsRuntime._make_jsonable(object())

    summary = ToolsRuntime._summarize_model_metadata(
        {
            "modelDetails": {
                "foundationModelId": "model-a",
                "modelName": "A",
                "providerName": "Provider",
                "inputModalities": ["TEXT"],
                "outputModalities": ["TEXT"],
                "responseStreamingSupported": True,
                "inferenceTypesSupported": ["ON_DEMAND"],
                "modelLifecycle": {"status": "ACTIVE", "ignored": "x"},
            }
        }
    )
    assert summary["modelDetails"]["modelId"] == "model-a"
    assert summary["modelDetails"]["modelLifecycle"] == {"status": "ACTIVE"}
    assert (
        ToolsRuntime._summarize_model_metadata("raw")["modelDetails"]["modelId"] is None
    )
    assert (
        ToolsRuntime._summarize_model_metadata({"modelLifecycle": "bad"})[
            "modelDetails"
        ]["modelLifecycle"]
        == {}
    )

    assert ToolsRuntime._payload_parts("text")[0] == "text"
    assert ToolsRuntime._payload_parts(True)[0] == "boolean"
    assert ToolsRuntime._payload_parts(None)[0] == "null"
    assert ToolsRuntime._payload_parts(2.5)[0] == "number"
    assert ToolsRuntime._payload_parts(object())[0] == "repr"

    monkeypatch.setattr(ToolsRuntime, "_make_jsonable", staticmethod(lambda value: []))
    assert ToolsRuntime._payload_parts(Payload(value=1))[1] == {"value": []}
    assert ToolsRuntime._payload_parts(Record(1))[1] == {"value": []}
    assert ToolsRuntime._payload_parts({"x": 1})[1] == {"value": []}


def test_tool_output_serialization_and_permissive_parsing():
    envelope = ToolsRuntime.to_envelope(
        {"x": 1}, tool_name="lookup", extra_meta={"source": "test"}
    )
    assert envelope.meta["source"] == "test"
    assert ToolEnvelope.model_validate_json(
        ToolsRuntime.dumps_tool_output([1], tool_name="lookup")
    ).data == {"items": [1]}

    assert ToolsRuntime.parse_tool_output(envelope)["tool_name"] == "lookup"
    canonical = envelope.model_dump(mode="json")
    assert ToolsRuntime.parse_tool_output(canonical) == canonical
    assert ToolsRuntime.parse_tool_output({"x": 1})["data"] == {"x": 1}
    repaired = ToolsRuntime.parse_tool_output(
        {"kind": "list", "tool_name": "lookup", "ok": True, "data": [1], "meta": {}}
    )
    assert repaired["data"] == {"items": [1]}

    assert ToolsRuntime.parse_tool_output('{"x": 1}') == {"x": 1}
    assert ToolsRuntime.parse_tool_output("[1]")["data"] == {"items": [1]}
    assert ToolsRuntime.parse_tool_output("{'x': 1}")["data"] == {"x": 1}
    assert ToolsRuntime.parse_tool_output("raw")["data"] == {"text": "raw"}
    assert ToolsRuntime.parse_tool_output(3)["data"] == {"value": 3}


def test_strict_framework_output_parsing_and_name_mismatch():
    envelope = ToolsRuntime.to_envelope({"x": 1}, tool_name="lookup")
    assert ToolsRuntime.parse_framework_tool_output(envelope)["ok"] is True
    assert (
        ToolsRuntime.parse_framework_tool_output(envelope.model_dump_json())["ok"]
        is True
    )
    assert (
        ToolsRuntime.parse_framework_tool_output(3)["data"]["error_type"]
        == "NonEnvelopeToolOutput"
    )
    assert (
        ToolsRuntime.parse_framework_tool_output("raw")["data"]["error_type"]
        == "NonEnvelopeToolOutput"
    )
    assert (
        ToolsRuntime.parse_framework_tool_output("[]")["data"]["error_type"]
        == "MalformedToolEnvelope"
    )
    assert (
        ToolsRuntime.parse_framework_tool_output(envelope.model_dump(mode="json"))["ok"]
        is True
    )
    mismatch = ToolsRuntime.parse_framework_tool_output(
        envelope,
        expected_tool_name="other",
    )
    assert mismatch["data"]["error_type"] == "ToolNameMismatch"


def test_execute_tool_success_validation_exception_async_and_unknown():
    runtime = ToolsRuntime()

    @runtime.tool
    def add(a: int, b: int = 1):
        return {"value": a + b}

    @runtime.tool
    def explode(value: int):
        raise RuntimeError(f"boom:{value}")

    @runtime.tool
    async def async_tool(value: int):
        return value

    assert runtime.execute_tool("add", {"a": 2}).data == {"value": 3}
    assert (
        runtime.execute_tool("add", {"a": "bad"}).data["error_type"]
        == "ValidationError"
    )
    assert (
        runtime.execute_tool("explode", {"value": 2}).data["error_type"]
        == "RuntimeError"
    )
    assert (
        runtime.execute_tool("async_tool", {"value": 2}).data["error_type"]
        == "RuntimeError"
    )
    assert runtime.execute_tool("missing").data["error_type"] == "UnknownToolError"
