import copy

import pytest

from scripts.claim_acceptance_checks import assess_claims

EVIDENCE = [{"id": "a", "ok": True}, {"id": "b", "ok": False}]
CASE = {"answer": "First succeeded. Second failed.", "expected": "pass"}
ANNOTATIONS = [
    {
        "text": "First succeeded.",
        "status": "supported",
        "required_ids": ["a"],
        "allowed_ids": ["a"],
    },
    {
        "text": "Second failed.",
        "status": "supported",
        "required_ids": ["b"],
        "allowed_ids": ["b"],
    },
]


def report(combined=False):
    records = [
        {
            "fragment": item["text"],
            "model_status": item["status"],
            "observed_records": [copy.deepcopy(event)],
        }
        for item, event in zip(ANNOTATIONS, EVIDENCE)
    ]
    if combined:
        records = [
            {
                "fragment": CASE["answer"],
                "model_status": "supported",
                "observed_records": copy.deepcopy(EVIDENCE),
            }
        ]
    return {
        "execution_ok": True,
        "verdict": {"grounding": "pass", "clarity": True, "records": records},
    }


@pytest.mark.parametrize("combined", [False, True])
def test_complete_evidence_passes_across_valid_partition_choices(combined):
    assert assess_claims(CASE, EVIDENCE, report(combined), ANNOTATIONS) == {
        "passed": True,
        "problems": [],
    }


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (
            lambda r: r["verdict"]["records"][0]["observed_records"].clear(),
            "missing_citation",
        ),
        (
            lambda r: r["verdict"]["records"][0]["observed_records"].append(
                EVIDENCE[1]
            ),
            "irrelevant_citation",
        ),
        (
            lambda r: r["verdict"]["records"][0]["observed_records"].append(
                EVIDENCE[0]
            ),
            "duplicate_citation",
        ),
        (
            lambda r: r["verdict"]["records"][0]["observed_records"][0].update(
                ok=False
            ),
            "evidence_content_mismatch",
        ),
        (
            lambda r: r["verdict"]["records"][0].update(model_status="nonfactual"),
            "status_mismatch",
        ),
        (
            lambda r: r["verdict"]["records"].pop(),
            "invalid_verdict_structure_or_coverage",
        ),
        (lambda r: r["verdict"].update(clarity=False), "clarity_mismatch"),
        (lambda r: r.update(execution_ok=False), "execution_failed"),
    ],
)
def test_matching_aggregate_does_not_hide_local_defects(mutation, reason):
    candidate = report()
    mutation(candidate)
    result = assess_claims(CASE, EVIDENCE, candidate, ANNOTATIONS)
    assert not result["passed"]
    assert any(reason in problem for problem in result["problems"])


def test_combined_fragment_still_requires_each_claim_citation():
    candidate = report(combined=True)
    candidate["verdict"]["records"][0]["observed_records"] = [EVIDENCE[1]]
    result = assess_claims(CASE, EVIDENCE, candidate, ANNOTATIONS)
    assert result == {"passed": False, "problems": ["fragment_0:missing_citation"]}


def test_wrong_annotation_is_not_misreported_as_candidate_failure():
    annotations = copy.deepcopy(ANNOTATIONS)
    annotations[0]["text"] = "Invented."
    with pytest.raises(ValueError):
        assess_claims(CASE, EVIDENCE, report(), annotations)
