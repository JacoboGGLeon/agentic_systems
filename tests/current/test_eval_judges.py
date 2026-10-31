"""Deterministic judges exercise the protocol, not model reasoning quality."""

import asyncio
from typing import Any

import pydantic
import pytest

import agentic_systems as toolkit


class State(pydantic.BaseModel):
    value: int


def target():
    def increment(state):
        return {"value": state.value + 1}

    graph = toolkit.Graph(State)
    graph.add_node("increment", increment)
    graph.add_edge(toolkit.START, "increment")
    graph.add_edge("increment", toolkit.END)
    return toolkit.Agent("target", graph)


def fixture_judge(verdict):
    # Loose fixture output lets the Eval protocol reject malformed judgments.
    state = pydantic.create_model("JudgeState", **{key: (Any, None) for key in
                                  {"input", "expected", "result", "rubric", *verdict}})
    output = pydantic.create_model("JudgeOutput", **{key: (Any, ...) for key in verdict})

    def score(request):
        return verdict

    graph = toolkit.Graph(state, output_schema=output)
    graph.add_node("score", score)
    graph.add_edge(toolkit.START, "score")
    graph.add_edge("score", toolkit.END)
    return toolkit.Agent("fixture-judge", graph)


def evaluation(verdict, rubric):
    return toolkit.Eval("judge-protocol", target(),
                        ({"input": {"value": 3}, "expected": {"data": {"value": 4}}},),
                        judge=fixture_judge(verdict), rubric=rubric)


@pytest.mark.parametrize("rubric,error", [
    ({"criteria": []}, ValueError),
    ({"criteria": ["a", "a"]}, ValueError),
    ({"threshold": 2}, ValueError),
    ({"require_failure_findings": "yes"}, TypeError),
    ({"instructions": 3}, TypeError),
    ({"certification_tool": ""}, TypeError),
])
def test_rubric_is_validated_before_execution(rubric, error):
    with pytest.raises(error):
        evaluation({"criteria": {"correct": 1}, "findings": []}, rubric).compile()


@pytest.mark.parametrize("verdict,expected", [
    ({"criteria": {"correct": 1}, "findings": []}, True),
    ({"criteria": {"correct": 0.5}, "findings": [{"criterion": "correct", "evidence": "Incorrect result"}]}, False),
    ({"criteria": {"other": 1}, "findings": []}, False),
    ({"criteria": {"correct": 2}, "findings": []}, False),
    ({"criteria": {"correct": True}, "findings": []}, False),
    ({"criteria": {"correct": 1}, "findings": "invented"}, False),
    ({"criteria": {"correct": 0}, "findings": []}, False),
    ({"criteria": {"correct": 0}, "findings": [{"criterion": "unknown", "evidence": "x"}]}, False),
    ({"criteria": {"correct": 1}, "findings": [], "ok": False}, False),
])
def test_judge_scores_findings_and_self_report_must_agree(verdict, expected):
    result = evaluation(verdict, {"criteria": ["correct"], "threshold": 0.8}).run()
    assert result.ok is expected, result.to_dict()
    assert result.data["passed"] == int(expected)
    assert result.check_invariants().ok
    assert "judge-protocol" in result.human_results()


def test_certification_requires_actual_tool_evidence_and_async_eval_works():
    result = evaluation({"criteria": {"correct": 1}, "findings": []},
                        {"criteria": ["correct"], "certification_tool": "certify"}).run()
    assert not result.ok
    result = asyncio.run(evaluation({"criteria": {"correct": 1}, "findings": []},
                                    {"criteria": ["correct"]}).arun())
    assert result.ok


@pytest.mark.parametrize("options,error", [
    ({"unit": object(), "cases": ({"expected": {"ok": True}},)}, TypeError),
    ({"unit": None, "cases": ()}, ValueError),
    ({"unit": None, "cases": ({"expected": {"ok": True}},), "checks": []}, TypeError),
    ({"unit": None, "cases": ({"expected": {"ok": True}},), "rubric": {}}, ValueError),
    ({"unit": None, "cases": ({"input": {"value": 3}},)}, ValueError),
])
def test_eval_declaration_requires_an_explicit_acceptance_contract(options, error):
    if options["unit"] is None:
        options = {**options, "unit": target()}
    with pytest.raises(error):
        toolkit.Eval("invalid", **options).compile()


def test_check_must_return_a_boolean_verdict():
    def malformed_check(result, case):
        return {"ok": "yes"}

    result = toolkit.Eval("invalid-check", target(), ({"input": {"value": 3}},),
                          checks=(malformed_check,)).run()
    assert not result.ok and "boolean" in str(result.errors)
