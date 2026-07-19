from __future__ import annotations

import dataclasses
import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from agentic_systems import AgenticSystem, InspectReport, Skill, Tool, runtime
from agentic_systems.inspection import _payload, _schema


class LookupInput(BaseModel):
    key: str


class LookupOutput(BaseModel):
    value: str


def test_static_inspection_covers_entities_relations_profiles_and_risks_without_execution():
    calls = {"tool": 0}

    def lookup(payload: LookupInput) -> dict:
        calls["tool"] += 1
        return {"value": payload.key}

    lookup_tool = Tool(
        lookup,
        name="lookup",
        description="Look up one value.",
        input_schema=LookupInput,
        output_schema=LookupOutput,
    )
    system = AgenticSystem(runtime=runtime(provider="python-runtime"))
    skill = Skill(
        name="research",
        tools=[lookup_tool],
        contracts={"evidence": "required"},
        policy={"max_sources": 2},
    )
    system.skill(skill)

    class LoadedManifest:
        name = "loaded_research"
        tools = ("lookup",)

        def model_dump(self, mode="json"):
            return {"name": self.name, "tools": list(self.tools)}

    system._skills.append(SimpleNamespace(manifest=LoadedManifest()))

    @system.tool(name="lookup", on_conflict="replace", source="replacement")
    def replacement(key: str) -> dict:
        calls["tool"] += 1
        return {"value": key}

    toolkit = system.toolkit("ops")

    @toolkit.tool
    def health() -> dict:
        calls["tool"] += 1
        return {"ok": True}

    system.agent(
        name="worker",
        instructions="Use lookup.",
        tools=["lookup"],
        skills=["research"],
        engine="python-runtime",
        framework="strands",
        contract={"must_call": ["lookup"]},
        policy={"max_turns": 2, "max_tool_calls": 1},
    )

    report = system.inspect()
    payload = report.to_dict()

    assert calls == {"tool": 0}
    assert report["schema_version"] == "agentic_systems.inspect.v1"
    assert report["inspection_kind"] == "static"
    assert report["side_effects"] == {"models_executed": 0, "tools_executed": 0}
    assert json.loads(json.dumps(payload)) == payload
    assert {item["name"] for item in payload["entities"]["tools"]} == {"lookup", "ops.health"}
    assert payload["entities"]["skills"][0]["identity"] == "research"
    assert any(item["identity"] == "loaded_research" for item in payload["entities"]["skills"])
    assert payload["entities"]["agents"][0]["name"] == "worker"
    assert {"source": "agent:worker", "relation": "uses", "target": "tool:lookup"} in payload["relationships"]
    assert {"source": "skill:research", "relation": "packages", "target": "tool:lookup"} in payload["relationships"]
    assert payload["contracts"]["skills"][0]["tools"][0]["input_schema"]["title"] == "LookupInput"
    assert payload["contracts"]["agents"][0]["contract"]["must_call"] == ["lookup"]
    assert next(item for item in payload["providers"] if item["provider"] == "python-runtime")["selected_by"]
    assert next(item for item in payload["frameworks"] if item["framework"] == "strands")["selected_by"]
    assert payload["capabilities"]["providers"]
    assert payload["conflicts"]["resolved"][0]["decision"] == "replace"
    assert payload["conflicts"]["unresolved"] == []
    assert payload["limits"]["agents"][0]["policy"]["max_turns"] == 2
    assert any(item["code"] == "framework_adapter_unavailable" for item in payload["degradation_risks"])
    assert all(item["suggestion"] for item in payload["diagnostics"])
    assert report.human_text() == report.human_text()
    assert report.human_text().startswith("Agentic Systems static inspection\nStatus: OK")
    assert report.raise_if_errors() is report


def test_static_inspection_preserves_legacy_errors_and_actionable_diagnostics():
    system = AgenticSystem(strict=True)

    @system.tool
    def valid_tool() -> dict:
        raise AssertionError("inspection must not execute this tool")

    def missing_return_annotation():
        raise AssertionError("inspection must not execute this function")

    spec = system._runtime._tools["valid_tool"]
    system._runtime._tools["valid_tool"] = dataclasses.replace(
        spec,
        func=missing_return_annotation,
    )
    report = system.inspect()

    assert report["ok"] is False
    assert report["errors"][0]["issue"] == "tool_return_annotation_must_be_dict"
    diagnostic = next(
        item
        for item in report["diagnostics"]
        if item["code"] == "tool_return_annotation_must_be_dict"
    )
    assert "Annotate the Tool" in diagnostic["suggestion"]
    with pytest.raises(ValueError, match="inspect failed"):
        report.raise_if_errors()


def test_static_inspection_auto_provider_runtime_only_tools_and_empty_human_view():
    system = AgenticSystem(runtime=runtime(provider="auto", allow_python_fallback=True))

    @system.tool(name="runtime_only")
    def runtime_only() -> dict:
        return {"ok": True}

    system._public_tools.pop("runtime_only")
    report = system.inspect()

    assert report["entities"]["tools"][0]["registry"] == "runtime-only"
    assert any(
        item["code"] == "provider_resolution_deferred"
        for item in report["degradation_risks"]
    )

    empty = InspectReport(
        ok=True,
        entities={},
        relationships=[],
        providers=[],
        frameworks=[],
        diagnostics=[],
    )
    assert "Providers: none selected" in empty.human_text()
    assert "Frameworks: none selected" in empty.human_text()
    assert empty.to_dict()["ok"] is True

    assert _payload({"x": 1}) == {"x": 1}
    assert _payload(object())["type"] == "builtins.object"
    assert _schema(str)["type"] == "builtins.str"
