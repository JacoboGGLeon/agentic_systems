from __future__ import annotations


import pytest

import agentic_systems.evals as evals_module
from agentic_systems.evals import EvalCaseResult, EvalReport, Evaluator, run_eval
from agentic_systems.results import RunResult


class FakeAgent:
    def __init__(self, name="agent", ok=True):
        self.name = name
        self.ok = ok
        self.calls = []

    def run(self, input, mode="default", config=None):
        self.calls.append((input, mode, config))
        return RunResult(
            text=f"{self.name}:{input}",
            data={"tool": self.name, "value": input, "ok": self.ok, "summary": f"summary {input}"},
            ok=self.ok,
            tool_events=[],
            mode=mode,
        )


class SyncGraph:
    def invoke(self, state):
        row = state["row"]
        return {**state, "route": row.get("route", "sync"), "summary": row.get("summary", "ok"), "result": {"text": "result text"}}


class CompilableGraph:
    def compile(self):
        return SyncGraph()


def test_eval_report_lineage_summaries_and_evaluator_alias(monkeypatch):
    case = EvalCaseResult(
        name="case1",
        ok=False,
        input={"q": "x"},
        expected={"data_contains": {"tool": "calc", "value": 42}},
        result={"ok": False, "answer": {"text": "bad", "final": {"summary": "final summary"}, "data": {"tool": "calc", "value": 1}}, "tools": [{"name": "calc", "ok": True, "summary": "used"}]},
        validation={"ok": False},
    )
    assert case.to_dict()["name"] == "case1"
    report = EvalReport(ok=False, total=1, passed=0, failed=1, pass_rate=0.0, cases=[case])
    assert report.normalized()["errors"][0]["message"] == "case1"
    with pytest.raises(AssertionError):
        report.raise_if_failed()
    lineage = report.lineage(question="q", goal="g", tags=["tag"], metadata={"m": 1})
    assert lineage.ok is False
    assert lineage.tags == ["eval", "tag"]
    assert lineage.metadata["m"] == 1

    must_call_case = EvalCaseResult(name="case2", ok=True, input="x", expected={"must_call": ["tool"]}, result={"data": {"result": 7, "ok": True}}, validation={"ok": True})
    tools_only_case = EvalCaseResult(name="case3", ok=True, input="x", expected={}, result={"tools": [{"name": "tool_a"}]}, validation={"ok": True})
    empty_case = EvalCaseResult(name="case4", ok=True, input="x", expected={}, result={}, validation={"ok": True})
    unknown_expected_case = EvalCaseResult(name="case5", ok=True, input="x", expected={"other": "value"}, result={"answer": {"data": "not-dict", "final": {"result": 9}}}, validation={"ok": True})
    EvalReport(ok=True, total=4, passed=4, failed=0, pass_rate=1.0, cases=[must_call_case, tools_only_case, empty_case, unknown_expected_case]).lineage()

    class SyncOnlyAgent:
        def run_sync(self, input_value, mode="eval", config=None):
            return RunResult(text="ok", data={"answer": "ok"}, ok=True)

    cases = [{"name": "ok", "input": "x", "expected": {"text_contains": "ok"}}]
    evaluator = Evaluator()
    report_from_alias = evaluator.run(SyncOnlyAgent(), cases)
    assert report_from_alias.ok is True
    assert evaluator.evaluate_agent(SyncOnlyAgent(), cases).ok is True
    assert run_eval(SyncOnlyAgent(), cases, environment_kwargs={"name": "custom_eval"}).passed == 1

    monkeypatch.setattr(evals_module, "_case_actual_evidence", lambda case: {"final": "not-dict", "data": "not-dict", "tools": []})
    assert evals_module._case_actual_summary(empty_case) == "sin salida estructurada"
