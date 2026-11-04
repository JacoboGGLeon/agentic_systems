"""Recorded audit evidence is a consumer contract, including bounded views."""
import json
from dataclasses import replace

import pytest
from pydantic import BaseModel

from agentic_systems import RunResult
from agentic_systems._results import _Event, _Lineage, _Validation, _json, _preview


def evidence():
    leaf = RunResult(execution_id="child", parent_execution_id="root", text="payment rejected",
                     ok=False, data={"amount": 10}, errors=({"code": "declined"},),
                     engine="provider", mode="work", meta={"kind": "action", "name": "charge"},
                     tool_events=(_Event("event", "pay", output={"rows": [1, 2, 3, 4]},
                                         ok=False, error={"code": "declined"}),))
    return RunResult(execution_id="root", text="review payment", ok=False,
                     data={"answer": 10}, children=(leaf,), engine="provider", model="fixture",
                     usage={"requests": 2}, validation={"ok": False},
                     errors=({"code": "declined"},),
                     meta={"name": "payments", "input": {"amount": 10}, "next": "review",
                           "graph_node": "route", "scheduler_execution": {"attempt_history": [
                               {"number": 1, "status": "failed", "error": [{"code": "retry"}]},
                               {"number": 2, "status": "completed", "result": {"usage": {"requests": 1}}}]}})


def test_compact_trace_preserves_identity_failure_priority_and_omission_count():
    run = evidence()
    assert run.trace(max_steps=1) == {
        "ok": False, "status": "failed", "execution_id": "root", "engine": "provider",
        "model": "fixture", "data": {"answer": 10}, "errors": [{"code": "declined"}],
        "omitted_steps": 1,
        "steps": [{"execution_id": "root", "parent_execution_id": None, "name": "payments", "ok": False}]}
    successful = RunResult(execution_id="good", children=(run,))
    assert successful.trace(max_steps=1)["steps"][0]["execution_id"] == "root"
    assert run.trace("full", max_steps=0) == run.to_dict()
    assert RunResult(**run.to_dict()).to_dict() == run.to_dict()


def test_lineage_exports_complete_observed_records_and_consumer_metadata():
    run = evidence()
    lineage = run.lineage(name="audit", question="why", goal="reconcile", tags=["finance"],
                          metadata={"reviewer": "human"}, max_tool_rows=2)
    expected = [
        {"step_id": "root", "kind": "execution", "title": "payments", "summary": "review payment",
         "source": "provider", "why": "Recorded execution evidence",
         "evidence": {"ok": False, "data": {"answer": 10}, "errors": [{"code": "declined"}]}},
        {"step_id": "root:attempt:1", "kind": "attempt", "title": "Actor attempt 1", "summary": "failed",
         "source": "provider", "why": "Observed scheduler attempt; retries retain prior evidence",
         "evidence": {"ok": False, "usage": {}, "errors": [{"code": "retry"}]}},
        {"step_id": "root:attempt:2", "kind": "attempt", "title": "Actor attempt 2", "summary": "completed",
         "source": "provider", "why": "Observed scheduler attempt; retries retain prior evidence",
         "evidence": {"ok": True, "usage": {"requests": 1}, "errors": []}},
        {"step_id": "root:decision", "kind": "decision", "title": "Next node", "summary": "review",
         "source": "route", "why": "Recorded graph routing result", "evidence": {"next": "review"}},
        {"step_id": "child", "kind": "execution", "title": "charge", "summary": "payment rejected",
         "source": "provider", "why": "Recorded execution evidence",
         "evidence": {"ok": False, "data": {"amount": 10}, "errors": [{"code": "declined"}]}},
        {"step_id": "event", "kind": "tool", "title": "pay", "summary": "failed", "source": "pay",
         "why": "Recorded Tool event", "evidence": {"ok": False, "output": {"rows": [1, 2]}, "error": {"code": "declined"}}}]
    assert lineage.to_dict() == {
        "schema_version": "agentic_systems.lineage.v2", "execution_id": "root", "status": "failed",
        "name": "audit", "question": "why", "goal": "reconcile", "answer": "review payment",
        "ok": False, "steps": expected, "usage": {"requests": 2}, "validation": {"ok": False},
        "tags": ["finance"], "metadata": {"reviewer": "human"}}
    assert lineage.explain() == {"execution_id": "root", "answer": "review payment", "ok": False,
                                 "status": "failed", "steps": expected}
    assert json.loads(lineage.to_prompt_context(max_chars=10000))["steps"] == expected
    assert lineage.render().splitlines() == ["audit: FAILED", "review payment", *[
        f"- {s['title']}: {s['summary']} [{s['step_id']}]" for s in expected]]


@pytest.mark.parametrize("size", [1, 12, 13, 16])
def test_render_reports_truncation_and_failures_outside_the_view(size):
    steps = tuple({"step_id": str(i), "title": "step", "summary": "recorded", "evidence": {"ok": i < 12}}
                  for i in range(size))
    line = _Lineage("audit", "q", "g", "answer", True, steps, {}, None, (), {})
    text = line.render()
    assert text.splitlines()[:2] == ["audit: OK", "answer"]
    assert len([s for s in text.splitlines() if s.startswith("- ")]) == min(size, 12)
    if size > 12:
        assert f"{size - 12} more steps; retrieve evidence by execution_id." in text
        assert f"{size - 12} failures outside this view: " + ", ".join(str(i) for i in range(12, min(size, 15))) in text


def test_prompt_budget_preserves_failed_evidence_and_json_envelope():
    steps = ({"step_id": "large", "evidence": {"ok": True}, "data": "x" * 500},
             {"step_id": "failed", "evidence": {"ok": False}})
    line = _Lineage("audit", "q", "g", "answer", False, steps, {}, None, (), {}, execution_id="run-id")
    assert json.loads(line.to_prompt_context(max_chars=200)) == {
        "ok": False, "steps": [steps[1]], "omitted_steps": 1, "failed_steps": 1,
        "execution_id": "run-id", "answer": "answer"}
    for budget in range(1, 250):
        try:
            text = line.to_prompt_context(max_chars=budget)
        except ValueError:
            continue
        assert len(text) <= budget
        assert json.loads(text)["failed_steps"] == 1
    with pytest.raises(ValueError):
        line.to_prompt_context(max_chars=1)


def test_human_report_preserves_failed_tools_decisions_and_attempts():
    assert evidence().human_results() == (
        'payments: FAILED\nExecution: root\nInput: {"amount":10}\nOutput: {"answer":10}\n'
        'Errors: [{"code":"declined"}]\nProcess:\n'
        '- Tool pay: failed -> {"code":"declined"}\n- Attempt 1: failed\n'
        '- Attempt 2: completed\n- Decision payments -> "review"')
    assert RunResult().human_results().endswith("Process:\n- No business operation recorded.")
    assert "Input: not recorded" in RunResult().human_results()
    assert "Awaiting resume; execution is not complete." in RunResult(
        status="paused", interrupts=({"question": "approve"},), continuation={"id": "continue"}).human_results()


@pytest.mark.parametrize("budget", [256, 257, 400, 1000])
def test_human_bounds_and_failure_priority(budget):
    children = tuple(RunResult(execution_id=str(i), ok=i != 15, data={"large": "x" * 600},
                              meta={"kind": "node", "name": "review" if i == 15 else "work"}) for i in range(16))
    text = RunResult(execution_id="root", children=children, data={"large": "x" * 3000}).human_results(
        max_steps=1, max_chars=budget)
    assert len(text) <= budget
    assert "Step review: failed" in text
    assert "15 operations omitted; inspect lineage for full evidence." in text


@pytest.mark.parametrize("field", ["api_key", "Authorization", "password", "access_token", "secret_key", "session_token"])
def test_secrets_never_escape_any_evidence_view(field):
    run = RunResult(data={"rows": [{field: "sensitive-value"}]}, errors=({field: "sensitive-value"},))
    for value in [run.to_dict(), run.trace(), run.human_results(), run.lineage().to_dict(), run.lineage().to_prompt_context()]:
        assert "sensitive-value" not in str(value)
        assert "[REDACTED]" in str(value)


def test_json_normalization_and_preview_boundary():
    class Payload(BaseModel):
        rows: list[float]
    assert _json(Payload(rows=[1.5])) == {"rows": [1.5]}
    with pytest.raises(TypeError, match="Expected finite JSON data"):
        _json(Payload(rows=[float("inf")]))
    assert _preview("ab", max_chars=4) == "ab"
    assert _preview("ab", max_chars=3) == {"preview": '"ab', "omitted": True}
    for value in [{1: "not JSON"}, {"nested": [object()]}, float("nan")]:
        with pytest.raises(TypeError):
            _json(value)


def test_invariant_diagnostics_preserve_codes_and_paths():
    event = _Event("event", "pay", error={"code": "unexpected"})
    run = RunResult(execution_id="root", children=(RunResult(execution_id="root", ok=False),),
                    tool_events=(event, event), usage={"requests": -1})
    assert run.check_invariants().to_dict() == {"ok": False, "issues": [
        {"code": "success_with_failed_evidence", "path": "root"},
        {"code": "parent_mismatch", "path": "root"},
        {"code": "inconsistent_tool_event", "path": "event"},
        {"code": "inconsistent_tool_event", "path": "event"},
        {"code": "negative_usage", "path": "root"},
        {"code": "duplicate_execution_id", "path": "root"}]}
    assert _Validation(False, ({"code": "problem"},)).to_dict() == {"ok": False, "issues": [{"code": "problem"}]}
    assert replace(run, children=(), tool_events=(), usage={}).check_invariants().ok


@pytest.mark.parametrize("kind,label", [("agent", "Agent"), ("system", "System"), ("environment", "Environment"), ("eval", "Eval"), ("node", "Step")])
def test_human_reports_named_business_children(kind, label):
    child = RunResult(execution_id="child", meta={"kind": kind, "name": "business\noperation"})
    assert f"- {label} business operation: completed" in RunResult(children=(child,)).human_results()
    assert "Failure external: failed" in RunResult(children=(RunResult(ok=False, meta={"name": "external"}),)).human_results()


def test_human_environment_filters_observations_and_eval_exposes_executed_cases():
    records = tuple(RunResult(data={"row": {"amount": n}}, meta={"name": name, "owner_name": owner,
                     "owner_kind": kind}) for n, name, owner, kind in [
                         (1, "observe", "day", "environment"), (2, "observe", "other", "environment"),
                         (3, "observe", "day", "eval"), (4, "update", "day", "environment")])
    run = RunResult(children=records, data={"outputs": [{"amount": 1}], "summary": {"processed": 1}},
                    meta={"kind": "environment", "name": "day"})
    assert run.human_results() == ('day: COMPLETED\nExecution: ' + run.execution_id +
        '\nInput: {"records_observed":[{"amount":1}]}\nOutput: {"outputs":[{"amount":1}],"summary":{"processed":1}}'
        '\nProcess:\n- No business operation recorded.')
    fallback = RunResult(data={"history": [{"record": {"amount": 9}}]}, meta={"kind": "environment"})
    assert 'Input: {"records_observed":[{"amount":9}]}' in fallback.human_results()
    checked = RunResult(data={"cases": [{"input": {"amount": 7}}], "total": 1, "passed": 1, "failed": 0}, meta={"kind": "eval"})
    assert 'Input: {"cases_executed":[{"amount":7}]}' in checked.human_results()
    assert 'Output: {"total":1,"passed":1,"failed":0}' in checked.human_results()


def test_human_unwraps_successful_tool_data_and_hides_internal_routing():
    child = RunResult(meta={"internal": True, "kind": "agent", "name": "hidden", "next": "secret"},
                      tool_events=(_Event("e", "quote", output={"data": {"total": 3}}),))
    text = RunResult(children=(child,)).human_results()
    assert '- Tool quote: completed -> {"total":3}' in text
    assert "Agent hidden" not in text and "Decision hidden" not in text


def test_lineage_defaults_fallbacks_nested_rows_and_paused_status():
    run = RunResult(execution_id="root", data={"amount": 5}, meta={"input": {"amount": 4}, "next": "done"},
                    tool_events=(_Event("event", "quote", output={"rows": [{"nested": [1, 2, 3]}]}),))
    line = run.lineage(max_tool_rows=1)
    assert line.question == '{"amount": 4}' and line.answer == '{"amount": 5}'
    assert line.name == "run" and line.goal == "" and line.tags == () and line.metadata == {}
    assert line.steps[0]["title"] == "default" and line.steps[0]["summary"] == "completed"
    assert line.steps[1]["source"] == "graph"
    assert line.steps[2]["evidence"] == {"ok": True, "output": {"rows": [{"nested": [1]}]}, "error": None}
    failed = RunResult(ok=False).lineage()
    assert failed.steps[0]["summary"] == "failed"
    paused = RunResult(status="paused", interrupts=({"question": "approve"},), continuation={"id": "resume"}).lineage()
    assert paused.render().startswith("run: PAUSED\n")
    assert json.loads(paused.to_prompt_context())["status"] == "paused"
