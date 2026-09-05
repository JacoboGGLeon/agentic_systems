from __future__ import annotations

import pytest
from pydantic import ValidationError
import agentic_systems as toolkit
from agentic_systems.contracts import ValidationResult
from agentic_systems.tools import ToolEvent
from agentic_systems_studio.conversation import ConversationConfig
from agentic_systems_studio.evaluation import (
    ConversationJudgment,
    build_conversation_judge,
    evaluate_turn,
    record_conversation_judgment,
)


def judgment(passed=True):
    return ConversationJudgment(
        assessments=[
            {
                "criterion": name,
                "passed": passed if name == "request_fulfillment" else True,
                "evidence": "The answer echoes the request."
                if not passed
                else "The response fulfills the supplied task.",
            }
            for name in toolkit.JudgeRubric().criteria
        ]
    )


class Judge:
    def __init__(self, passed=True):
        self.passed = passed
        self.last_result = None

    def run(self, request, **kwargs):
        payload = record_conversation_judgment.function(judgment(self.passed))
        self.last_result = toolkit.RunResult(
            ok=True,
            text="Recorded",
            data=payload,
            tool_events=[
                ToolEvent(
                    id="offline-judgment",
                    name="record_conversation_judgment",
                    input={},
                    output=payload,
                    ok=True,
                )
            ],
            engine="python-runtime",
            meta={"framework": "native"},
        )
        return self.last_result


def valid(result, case):
    return ValidationResult()


def test_tool_derives_scores_and_valid_findings():
    payload = record_conversation_judgment.function(judgment(False))
    assert payload["score"] == 0.8
    assert payload["criteria"]["request_fulfillment"] == 0.0
    assert set(payload["findings"][0]) == {"criterion", "evidence"}


@pytest.mark.parametrize("change", ["missing", "duplicate", "extra", "coerce_bool"])
def test_judge_input_is_closed_complete_and_strict(change):
    payload = judgment().model_dump()
    if change == "missing":
        payload["assessments"].pop()
    elif change == "duplicate":
        payload["assessments"].append(payload["assessments"][0])
    elif change == "extra":
        payload["score"] = 1.0
    else:
        payload["assessments"][0]["passed"] = "true"
    with pytest.raises(ValidationError):
        ConversationJudgment.model_validate(payload)


def test_model_rejection_is_not_promoted_by_keyword_pass():
    answer = "Resume la conversación: incluye 323, Tool, Skill y System."
    result = toolkit.RunResult(ok=True, text=answer)
    evaluated = evaluate_turn(result, answer, judge=Judge(False), assertion=valid)
    assert not evaluated.ok
    assert evaluated.deterministic_validation["ok"]
    assert evaluated.judge.certification_recorded
    assert evaluated.judge.consistent
    assert evaluated.judge.criteria["request_fulfillment"] == 0.0
    assert result.text == answer  # Evaluation must never repair the candidate.


def test_assertion_rejection_blocks_positive_model_judgment():
    def invalid(result, case):
        checked = ValidationResult()
        checked.add("invalid_code", "Invalid public Tool contract")
        return checked

    evaluated = evaluate_turn(
        toolkit.RunResult(ok=True, text="Candidate"),
        "Task",
        judge=Judge(),
        assertion=invalid,
    )
    assert not evaluated.ok
    assert not evaluated.judge.ok


def test_passing_turn_and_python_control_are_distinct():
    evaluated = evaluate_turn(
        toolkit.RunResult(ok=True, text="A grounded summary."),
        "Summarize",
        judge=Judge(),
        assertion=valid,
    )
    assert evaluated.ok
    assert (
        build_conversation_judge(ConversationConfig(provider="python-runtime")) is None
    )
    control = evaluate_turn(
        toolkit.RunResult(ok=True, text="Deterministic control"),
        "Task",
        judge=None,
        assertion=valid,
    )
    assert control.ok
    assert control.judge is None
