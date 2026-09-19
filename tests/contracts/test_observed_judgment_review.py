import copy

import pytest
import agentic_systems as toolkit
from scripts.semantic_e2e_application import JudgeCriteria
from scripts.two_phase_semantic_application import (
    record_observed_judgment,
    literal_contract,
    review_subject,
    apply_explanation_review,
)


def example():
    claims = dict(expected_value=323, expected_text="323", expected_length=3)
    agent = toolkit.agent(
        name="recording_control",
        runtime=toolkit.runtime(provider="python-runtime"),
        tools=[record_observed_judgment],
    )
    result = agent.run(
        {
            "tool": "record_semantic_judgment",
            "input": {
                "observations": claims,
                "assessments": {
                    key: dict(
                        passed=True,
                        evidence="Fixture explanation for " + key,
                        references=[dict(reference="/answer", value_json='"fixture"')],
                    )
                    for key in JudgeCriteria.model_fields
                },
            },
        }
    )
    assert result.ok, result.errors
    payload = result.normalized()["tools"][0]["output"]
    return dict(
        deterministic_passed=True,
        judge_input={
            "answer": "fixture",
            "evaluation_contract": literal_contract([17, 19]),
        },
        judge={
            "result": result.normalized(),
            "lineage": result.lineage().model_dump(mode="json"),
        },
        **payload,
    )


def receipt(report):
    return dict(
        subject_sha256=review_subject(report),
        reviewer="offline-test-fixture",
        approved=True,
        criteria={
            key: "Offline fixture, not a live certification."
            for key in JudgeCriteria.model_fields
        },
    )


def test_real_tool_records_positive_explanations_and_review_is_bound():
    report = example()
    assert len(report["assessments"]) == 5
    review = receipt(report)
    apply_explanation_review(report, review)
    assert report["passed"]
    review["criteria"]["clarity"] = "mutated outside report"
    assert (
        report["explanation_review"]["criteria"]["clarity"]
        != review["criteria"]["clarity"]
    )


@pytest.mark.parametrize(
    "field", ["claims", "decision", "assessments", "judge_input", "judge"]
)
def test_changed_subject_invalidates_review(field):
    report = example()
    review = receipt(report)
    changed = copy.deepcopy(report)
    changed[field] = {"changed": True}
    with pytest.raises(ValueError, match="stale_explanation_review"):
        apply_explanation_review(changed, review)


def test_incomplete_and_negative_reviews_cannot_approve():
    report = example()
    review = receipt(report)
    review["criteria"].pop("clarity")
    with pytest.raises(ValueError, match="complete_criterion_review_required"):
        apply_explanation_review(report, review)
    review = receipt(report)
    review["approved"] = False
    apply_explanation_review(report, review)
    assert not report["passed"]
    assert report["certification_verdict"]["status"] == "inconclusive"
    assert report["certification_verdict"]["semantic_quality"] == "unknown"
