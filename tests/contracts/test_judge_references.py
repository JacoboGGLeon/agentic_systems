import pytest
from scripts.judge_references import check_references


@pytest.mark.parametrize(
    "reference,value,reason",
    [
        ("/missing", "3", "unknown_reference"),
        ("/answer", "323", "cited_value_mismatch"),
        ("/answer", "not-json", "invalid_cited_json"),
        ("https://external.test/run", '"3"', "unknown_reference"),
    ],
)
def test_negative_has_nearby_valid_reference(reference, value, reason):
    packet = {"answer": "3"}
    positive = [
        dict(
            criterion="clarity",
            references=[dict(reference="/answer", value_json='"3"')],
        )
    ]
    assert check_references(packet, positive)["passed"]
    negative = [
        dict(
            criterion="clarity",
            references=[dict(reference=reference, value_json=value)],
        )
    ]
    assert check_references(packet, negative)["issues"][0]["reason"] == reason


def test_reference_catalog_cannot_be_forged():
    packet = dict(answer="actual", evidence_catalog={"/answer": '"forged"'})
    assessments = [
        dict(
            criterion="clarity",
            references=[dict(reference="/answer", value_json='"forged"')],
        )
    ]
    assert not check_references(packet, assessments)["passed"]


def test_existing_reference_is_not_semantic_support():
    assessment = dict(
        criterion="evidence_correctness",
        evidence="An unrelated tool executed.",
        references=[dict(reference="/answer", value_json='"hello"')],
    )
    result = check_references({"answer": "hello"}, [assessment])
    assert result["passed"]
    assert result["semantic_relevance_verified"] is False


def test_missing_or_duplicated_citations_fail():
    assert not check_references({"answer": "x"}, [])["passed"]
    assert not check_references({"answer": "x"}, [dict(criterion="clarity")])["passed"]
    citation = dict(reference="/answer", value_json='"x"')
    result = check_references(
        {"answer": "x"}, [dict(criterion="clarity", references=[citation, citation])]
    )
    assert result["issues"][0]["reason"] == "duplicate_reference"
