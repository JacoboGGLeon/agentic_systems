from __future__ import annotations


import pytest

import agentic_systems.lineage as lineage_module
from agentic_systems.lineage import LineageMemory, LineageStep, lineage_memory
from agentic_systems.results import RunResult, ToolEvent


def test_lineage_memory_full_narrative_and_prompt_context_edges():
    with pytest.raises(ValueError):
        LineageStep(step_id=" ", kind="input", title="Title", summary="x")
    with pytest.raises(TypeError):
        LineageMemory.from_run_result(object())

    tool = ToolEvent(
        id="search-1",
        name="search",
        ok=True,
        input={"q": "agentic"},
        output={"rows": [{"id": 1}, {"id": 2}, {"id": 3}], "route": "sqlite", "summary": "search executed"},
    )
    result = RunResult(
        text="",
        final={"message": "final from message"},
        data={"tool": "portable", "route": "fallback", "rows": [{"id": 1}], "summary": "portable summary"},
        ok=False,
        tool_events=[tool],
        validation={"ok": False, "issues": [{"code": "bad"}]},
        errors=[{"message": "needs review"}, {"code": "plain_error"}],
        usage={"total_tokens": 10},
        meta={"input": {"q": "agentic"}},
    )
    memory = LineageMemory.from_run_result(result, name="lineage", tags=["unit"], metadata={"m": 1}, max_tool_rows=2)
    assert memory.answer == "final from message"
    assert memory.metadata["m"] == 1
    assert memory.validation["ok"] is False
    assert any(step.kind == "error" for step in memory.steps)
    assert memory.compact(max_steps=2)["steps"][0]["step_id"] == "input"

    explanation = memory.explain()
    assert explanation["risks_or_gaps"]
    assert explanation["evidence"]
    assert "Lineage Memory" in memory.human_text(render_mode="audit", max_evidence_items=1)
    compact_text = memory.human_text(render_mode="compact")
    assert "Ruta" in compact_text
    debug_text = memory.human_text(render_mode="debug", max_evidence_chars=120)
    assert "Debug lineage payload" in debug_text
    prompt = memory.to_prompt_context(max_chars=80)
    assert prompt.endswith("...")
    savings = memory.estimated_context_savings({"raw": "x" * 500}, max_chars=80)
    assert savings["saved_chars"] > 0
    assert memory.to_dict()["name"] == "lineage"

    alias = LineageMemory.from_result(result, name="alias")
    helper = lineage_memory(result, name="helper")
    assert alias.name == "alias"
    assert helper.name == "helper"


def test_lineage_memory_portable_evidence_without_tool_events_and_fallbacks():
    result = RunResult(
        text="",
        final={"summary": "portable final", "sections": [{"kind": "sql", "content": "select 1"}, {"kind": "table", "rows": [{"x": 1}]}]},
        data={},
        ok=True,
        tool_events=[],
        meta={"input": None},
    )
    memory = LineageMemory.from_run_result(result, question=None)
    assert memory.answer == "portable final"
    assert any(step.step_id == "portable_tool_evidence" for step in memory.steps)
    text = memory.human_text(include_evidence=False)
    assert "Evidencia" not in text

    fallback = RunResult(text="", final={}, data={}, ok=True, tool_events=[])
    fallback_memory = LineageMemory.from_run_result(fallback)
    assert fallback_memory.answer == "{}"
    assert "No executable step" in fallback_memory.explain()["how_it_happened"][0]

    long_memory = LineageMemory(
        name="many",
        answer="answer",
        steps=[
            LineageStep(step_id=f"s{i}", kind="tool", title=f"Tool {i}", summary="x", evidence={"facts": {"ok": True}})
            for i in range(8)
        ],
    )
    rendered = long_memory.human_text(max_how_items=2, max_evidence_items=2)
    assert "paso(s)" in rendered
    assert "evidencia(s)" in rendered





def test_lineage_helper_rendering_edges():
    class Unserializable:
        def __str__(self):
            return "unserializable"

    assert lineage_module._safe_json({"x": Unserializable()}, max_chars=5).endswith("...")
    assert lineage_module._short("   ") == ""
    assert lineage_module._is_missing(None) is True
    assert lineage_module._is_missing(" n/a ") is True
    assert lineage_module._is_missing("value") is False

    assert lineage_module._natural_summary("route=None; the graph produced a routing plan.").startswith("El orquestador")
    assert lineage_module._natural_summary("the graph produced a routing plan.").startswith("El orquestador")
    assert "tool_a" in lineage_module._natural_summary("tool_a executed via tool call.")
    assert "sqlite" in lineage_module._natural_summary("tool_a executed via sqlite and returned 2 row(s).")
    assert "sqlite" in lineage_module._natural_summary("tool_a executed via sqlite.")
    assert "tool_a" in lineage_module._natural_summary("tool_a executed.")
    assert "OK" in lineage_module._natural_summary("contract validation passed.")
    assert "OK" in lineage_module._natural_summary("graph validation passed.")
    assert "revisar" in lineage_module._natural_summary("contract validation reported issues.").lower()
    assert "plain" == lineage_module._natural_summary("plain")

    assert lineage_module._evidence_facts(LineageStep.model_construct(step_id="a", kind="tool", title="T", summary="s", evidence=[])) == {}
    assert lineage_module._evidence_facts(LineageStep(step_id="b", kind="tool", title="T", summary="s", evidence={"tool": {"ok": True}})) == {"ok": True}
    assert lineage_module._evidence_facts(LineageStep(step_id="c", kind="validation", title="V", summary="s", evidence={"validation": {"ok": False}})) == {"ok": False}
    assert lineage_module._status_label(True) == "OK"
    assert lineage_module._status_label(False) == "REVISAR"
    assert lineage_module._status_label(None) == "registrado"

    decision = LineageStep(step_id="d", kind="decision", title="Graph node: router", summary="route=None; x", evidence={})
    validation = LineageStep(step_id="v", kind="validation", title="Graph validation", summary="Graph validation passed.", evidence={"validation": {"ok": True}})
    error = LineageStep(step_id="e", kind="error", title="Error", summary="bad", evidence={})
    reasons = lineage_module._derive_support_reasons([decision, validation, error], ok=False)
    assert any("grafo" in reason.lower() for reason in reasons)
    assert lineage_module._derive_support_reasons([], ok=False)

    line = lineage_module._evidence_line(LineageStep(step_id="f", kind="tool", title="Tool", summary="sum", evidence={"facts": {"ok": True, "empty": None}}), max_chars=80)
    assert "Tool:" in line and "ok" in line
    assert lineage_module._tool_output_facts("value") == {"value": "value"}
    nested = lineage_module._tool_output_facts({"data": {"rows": [{"a": 1}, {"a": 2}], "n_rows": 9}}, max_rows=1)
    assert nested["row_count"] == 9 and nested["sample_rows"] == [{"a": 1}]

    assert lineage_module._business_tool_evidence_from_payload("bad") == {}
    assert lineage_module._business_tool_evidence_from_payload({"x": 1}) == {}
    table_evidence = lineage_module._business_tool_evidence_from_payload({"name": "t", "table": {"rows": [{"a": 1}]}})
    assert table_evidence["row_count"] == 1
    section_evidence = lineage_module._business_tool_evidence_from_payload({"sections": [{"kind": "sql", "content": "select 1"}, {"kind": "table", "rows": [{"a": 1}, {"a": 2}]}]})
    assert section_evidence["sql"] == "select 1"


def test_lineage_from_run_result_edges():
    rows_tool = ToolEvent(id="rows", name="rows_tool", input={}, output={"rows": [{"a": 1}, {"a": 2}], "route": "db"})
    memory = LineageMemory.from_run_result(RunResult(text="", final={"answer": "from answer"}, tool_events=[rows_tool]))
    assert memory.answer == "from answer"
    assert "2 row" in next(step.summary for step in memory.steps if step.kind == "tool")

    non_dict_validation_result = RunResult(text="ok")
    object.__setattr__(non_dict_validation_result, "validation", "registered")
    memory_with_validation = LineageMemory.from_run_result(non_dict_validation_result)
    assert any(step.kind == "validation" for step in memory_with_validation.steps)

    graph_decision = LineageStep(step_id="g", kind="decision", title="Graph node: router", summary="route=None; the graph produced a routing plan.")
    tool_step = LineageStep(step_id="t", kind="tool", title="Tool: t", summary="t executed.")
    explain = LineageMemory(name="skip_graph", answer="a", steps=[graph_decision, tool_step]).explain()
    assert len(explain["how_it_happened"]) == 1

    empty = LineageMemory(name="empty", answer="a", steps=[])
    assert "No executable step" in empty.human_text(render_mode="audit")
    assert empty.to_prompt_context(max_chars=10).endswith("...")



def test_lineage_memory_fallback_and_serialization_paths(monkeypatch):
    original_dumps = lineage_module.json.dumps

    def raising_dumps(*args, **kwargs):
        raise RuntimeError("json failed")

    monkeypatch.setattr(lineage_module.json, "dumps", raising_dumps)
    assert lineage_module._safe_json({"x": 1}) == "{'x': 1}"
    monkeypatch.setattr(lineage_module.json, "dumps", original_dumps)

    assert lineage_module._natural_summary("") == ""
    assert lineage_module._natural_summary("route=None;").startswith("El orquestador")
    assert "revisar" in lineage_module._natural_summary("graph validation reported issues.").lower()

    nested_validation = LineageStep(
        step_id="nested_validation",
        kind="validation",
        title="Validation",
        summary="registered",
        evidence={"facts": {"validation": {"ok": True}}},
    )
    assert any("OK" in reason for reason in lineage_module._derive_support_reasons([nested_validation], ok=False))

    route_evidence = lineage_module._business_tool_evidence_from_payload({"tool": "router", "route": "manual"})
    assert "route=manual" in route_evidence["summary"]
    query_evidence = lineage_module._business_tool_evidence_from_payload({"tool": "query", "query": {"query_id": "q1"}})
    assert "query_id=q1" in query_evidence["summary"]

    decision_steps = [
        LineageStep(step_id=f"d{i}", kind="decision", title=f"Decision {i}", summary=f"step {i}")
        for i in range(5)
    ]
    memory = LineageMemory(name="goalful", question="q", goal="g", answer="a", steps=decision_steps)
    compact = memory.human_text(render_mode="compact")
    assert "Objetivo:" in compact
    assert "+2 paso" in compact
    assert memory.to_prompt_context(max_chars=10_000).startswith("LineageMemory: goalful")

    class EmptyExplainLineage(LineageMemory):
        def explain(self):
            return {"what_happened": "a", "how_it_happened": [], "support": [], "why_this_answer": [], "risks_or_gaps": [], "evidence": []}

    empty_route = EmptyExplainLineage(name="patched", answer="a", steps=[])
    assert "No se registraron pasos ejecutables" in empty_route.human_text(render_mode="audit")
