import pytest

from scripts.semantic_e2e_application import JudgeCriteria
from scripts.two_phase_semantic_application import certified_verdict, literal_contract


def verdict(claims, reviewed=False, deterministic=True):
    evidence = literal_contract([17, 19])
    decision = dict(
        score=1.0,
        criteria={key: 1.0 for key in JudgeCriteria.model_fields},
        rationale="All good",
    )
    return certified_verdict(
        deterministic,
        True,
        decision,
        evidence=evidence,
        claims=claims,
        explanation_reviewed=reviewed,
    )


CORRECT = dict(expected_value=323, expected_text="323", expected_length=3)


def test_good_facts_do_not_certify_unreviewed_prose():
    result = verdict(CORRECT)
    assert result["factual_checks"]["passed"]
    assert result["status"] == "pending_review"
    assert not result["passed"]
    assert verdict(CORRECT, reviewed=True)["passed"]


@pytest.mark.parametrize(
    "claims",
    [
        {**CORRECT, "expected_length": 323},
        {**CORRECT, "expected_length": "3"},
        {**CORRECT, "expected_text": 323},
        {**CORRECT, "extra": True},
        {"expected_value": 323},
        {},
    ],
)
def test_high_score_and_review_cannot_override_bad_or_missing_facts(claims):
    result = verdict(claims, reviewed=True)
    assert not result["passed"]
    assert result["status"] == "inconclusive"
    assert result["integrity"] == "passed"
    assert result["semantic_quality"] == "unknown"


def test_missing_observations_remain_pending_not_approved():
    assert verdict(None)["status"] == "inconclusive"
    assert not verdict(None)["passed"]


def test_verified_facts_cannot_override_candidate_integrity():
    assert not verdict(CORRECT, reviewed=True, deterministic=False)["passed"]


def test_factual_checks_retain_real_runresults_and_lineage():
    checks = verdict(CORRECT)["factual_checks"]["checks"]
    assert len(checks) == 3
    for check in checks:
        assert check["result"]["runtime"]["provider"] == "python-runtime"
        assert check["result"]["tools"][0]["name"] == "verify_evidence_field"
        assert check["lineage"]["steps"]
