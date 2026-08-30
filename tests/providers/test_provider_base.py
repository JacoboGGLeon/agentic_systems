from __future__ import annotations

import dataclasses
import sys
import types
from typing import Literal

import pytest
from pydantic import BaseModel

import agentic_systems.providers as providers
from agentic_systems.providers.base import RuntimeToolSpec, ToolRegistryRuntime


def test_tool_registry_resolves_deferred_literal_annotations():
    runtime = ToolRegistryRuntime(model_id="m")

    @runtime.tool
    def judge(
        failed_criteria: list[Literal["clarity", "evidence_correctness"]],
    ) -> dict:
        return {"failed_criteria": failed_criteria}

    schema = runtime.export_tool_specs(["judge"])[0]["input_schema"]
    assert schema["properties"]["failed_criteria"]["items"]["enum"] == [
        "clarity",
        "evidence_correctness",
    ]
    assert runtime.execute_tool("judge", {"failed_criteria": ["clarity"]}).ok
    assert not runtime.execute_tool("judge", {"failed_criteria": ["unsupported"]}).ok


def test_tool_registry_runtime_payloads_validation_and_lazy_provider(
    monkeypatch, capsys
):
    runtime = ToolRegistryRuntime(
        model_id="m",
        region_name="r",
        max_tokens_default="9",
        temperature_default="0.25",
    )
    assert runtime.max_tokens_default == 9
    assert runtime.temperature_default == 0.25

    @runtime.tool(description="Untyped param")
    def loose(x):
        return x

    async def async_tool(x: int) -> dict:
        return {"x": x}

    runtime.tool(async_tool, name="async_tool", description="Async tool")

    report = runtime.validate_tool_registry()
    assert report["ok"] is False
    assert any(
        issue["issue"] == "parameter_missing_type_annotation"
        for issue in report["issues"]
    )
    assert runtime.export_tool_specs(["loose"])[0]["name"] == "loose"
    runtime.print_tool_specs()
    assert "loose" in capsys.readouterr().out
    with pytest.raises(KeyError):
        runtime.export_tool_specs(["missing"])

    assert runtime.execute_tool("missing", {}).ok is False
    assert runtime.execute_tool("async_tool", {"x": 1}).ok is False
    assert runtime.execute_tool("loose", {"x": object()}).ok is True

    class PayloadModel(BaseModel):
        value: int

    @dataclasses.dataclass
    class PayloadData:
        value: int

    payloads = [
        PayloadModel(value=1),
        PayloadData(value=2),
        {"a": 1},
        [1, 2],
        "text",
        True,
        3,
        None,
        object(),
    ]
    kinds = [
        ToolRegistryRuntime.to_envelope(value, tool_name="payload").kind
        for value in payloads
    ]
    assert kinds == [
        "pydantic",
        "dataclass",
        "object",
        "list",
        "text",
        "boolean",
        "number",
        "null",
        "repr",
    ]

    def bad_varargs(*args):
        return {}

    with pytest.raises(TypeError, match="cannot use"):
        runtime.tool(bad_varargs, name="bad_varargs")

    fake_module = types.ModuleType("agentic_systems.providers.bedrock_runtime")
    fake_module.BedrockRuntime = object
    monkeypatch.setitem(
        sys.modules, "agentic_systems.providers.bedrock_runtime", fake_module
    )
    assert providers.BedrockRuntime is object
    with pytest.raises(AttributeError):
        providers.__getattr__("Nope")


def test_base_provider_validates_registry_schema_errors():
    runtime = ToolRegistryRuntime(model_id="m")

    @runtime.tool(name="ok", description="ok")
    def ok(x: int) -> dict:
        return {"x": x}

    spec = runtime._tools["ok"]
    runtime._tools[""] = RuntimeToolSpec(
        name="",
        description="",
        func=spec.func,
        signature=spec.signature,
        input_model=spec.input_model,
        input_schema={"type": "array"},
        is_async=False,
    )
    runtime._tools["bad_schema"] = RuntimeToolSpec(
        name="bad_schema",
        description="bad",
        func=spec.func,
        signature=spec.signature,
        input_model=spec.input_model,
        input_schema={"type": "object", "additionalProperties": True},
        is_async=False,
    )
    report = runtime.validate_tool_registry(["", "bad_schema"])
    issues = {issue["issue"] for issue in report["issues"]}
    assert "tool_name_must_be_non_empty_string" in issues
    assert "input_schema_type_must_be_object" in issues
    assert "input_schema_missing_properties" in issues
    assert "additionalProperties_should_be_false" in issues

    class Dumpable(BaseModel):
        value: int

    @dataclasses.dataclass
    class NestedData:
        value: int

    envelope = runtime.to_envelope(
        {"model": Dumpable(value=1), "data": NestedData(value=2)}, tool_name="nested"
    )
    assert envelope.data == {"model": {"value": 1}, "data": {"value": 2}}


def test_tool_registry_conflict_policies_are_explicit_and_inspectable():
    runtime = ToolRegistryRuntime(model_id="m")

    def original(value: int) -> dict:
        return {"source": "original", "value": value}

    def incoming(value: int) -> dict:
        return {"source": "incoming", "value": value}

    runtime.tool(original, name="shared")
    runtime.tool(original, name="shared")
    assert runtime.composition()["events"][-1]["decision"] == "reuse"

    with pytest.raises(ValueError, match="Tool.*shared"):
        runtime.tool(incoming, name="shared")

    runtime.tool(incoming, name="shared", on_conflict="keep")
    assert runtime.execute_tool("shared", {"value": 1}).data["source"] == "original"

    runtime.tool(incoming, name="shared", on_conflict="replace")
    assert runtime.execute_tool("shared", {"value": 1}).data["source"] == "incoming"
    assert runtime.composition()["events"][-1] == {
        "kind": "tool",
        "identity": "shared",
        "decision": "replace",
        "selected": "incoming",
    }


def test_tool_registry_rejects_unresolved_type_annotations():
    runtime = ToolRegistryRuntime(model_id="m")

    def unresolved(value) -> dict:
        return {"value": value}

    unresolved.__annotations__["value"] = "MissingToolInput"

    with pytest.raises(TypeError, match="unresolved type annotations"):
        runtime.tool(unresolved)
