from __future__ import annotations

import pytest
import agentic_systems as toolkit
from agentic_systems.contracts import ValidationResult
from agentic_systems.evals import EvalReport


class Candidate:
    def run(self, input, **kwargs):
        return toolkit.RunResult(text=str(input), ok=True)


class Judge:
    def __init__(self, passed=True):
        self.passed = passed

    def run(self, input, **kwargs):
        scores = {name: 1.0 for name in toolkit.JudgeRubric().criteria}
        findings = []
        if not self.passed:
            scores["request_fulfillment"] = 0.0
            findings = [
                {
                    "criterion": "request_fulfillment",
                    "evidence": "The response repeats the request instead of fulfilling it.",
                }
            ]
        return toolkit.RunResult(
            ok=True,
            data={
                "criteria": scores,
                "score": sum(scores.values()) / len(scores),
                "findings": findings,
            },
        )


def reject(result, case):
    validation = ValidationResult()
    validation.add(
        "format_mismatch",
        "The original response violates the declared format.",
        path="text",
    )
    return validation


@pytest.mark.parametrize("method", ["evaluate", "evaluate_agent", "run"])
def test_assertion_failure_blocks_approving_judge_and_roundtrips(method):
    report = getattr(toolkit.eval(), method)(
        Candidate(), [{"input": "323  "}], assertions=[reject], judge=Judge()
    )
    case = report.cases[0]
    assert not report.ok
    assert case.deterministic_validation["ok"] is False
    assert case.judge.ok is False
    assert case.judge.raw_criteria["request_fulfillment"] == 1.0
    assert case.deterministic_validation["issues"][0]["code"] == "format_mismatch"
    assert EvalReport.model_validate_json(report.model_dump_json()).ok is False


def test_passing_structural_checks_do_not_override_semantic_failure():
    report = toolkit.eval().evaluate(
        Candidate(), [{"input": "Repeat this request"}], judge=Judge(False)
    )
    case = report.cases[0]
    assert case.deterministic_validation["ok"] is True
    assert case.judge.criteria["request_fulfillment"] == 0.0
    assert not case.ok


def test_invalid_assertion_is_rejected_before_execution():
    with pytest.raises(TypeError, match="callable"):
        toolkit.eval().evaluate(Candidate(), [], assertions=[None])


@pytest.mark.parametrize(
    "assertion",
    [lambda result, case: True, lambda result, case: ValidationResult(ok=False)],
)
def test_invalid_or_unexplained_assertions_fail_closed(assertion):
    report = toolkit.eval().evaluate(
        Candidate(), [{"input": "x"}], assertions=[assertion]
    )
    assert not report.ok
    assert report.cases[0].validation["issues"]


def test_assertion_exception_does_not_leak_message():
    def broken(result, case):
        raise ValueError("private-token-must-not-escape")

    report = toolkit.eval().evaluate(Candidate(), [{"input": "x"}], assertions=[broken])
    assert not report.ok
    assert "ValueError" in report.model_dump_json()
    assert "private-token-must-not-escape" not in report.model_dump_json()


def test_warning_does_not_fail_and_assertion_sees_case():
    def warning(result, case):
        assert case["name"] == "declared"
        assert result.text == "x"
        checked = ValidationResult()
        checked.add("notice", "Informational warning", severity="warning")
        return checked

    report = toolkit.eval().evaluate(
        Candidate(), [{"name": "declared", "input": "x"}], assertions=[warning]
    )
    assert report.ok
    assert report.cases[0].validation["issues"][0]["severity"] == "warning"
