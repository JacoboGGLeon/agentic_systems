import pytest
from pydantic import ValidationError
from scripts.two_phase_semantic_application import ObservedJudgment, RequiredAssessments
from scripts.semantic_e2e_application import JudgeCriteria
from scripts.judge_references import evidence_catalog, check_references


def test_every_rubric_key_is_required_in_the_transmitted_schema():
    schema = ObservedJudgment.model_json_schema()["$defs"]["RequiredAssessments"]
    assert set(schema["required"]) == set(JudgeCriteria.model_fields)
    assert set(schema["properties"]) == set(JudgeCriteria.model_fields)
    assert schema["additionalProperties"] is False


@pytest.mark.parametrize("omitted", list(JudgeCriteria.model_fields))
def test_each_missing_criterion_is_a_schema_failure(omitted):
    complete = {
        name: dict(
            passed=True,
            evidence="A concise explanation.",
            references=[dict(reference="/answer", value_json='"x"')],
        )
        for name in JudgeCriteria.model_fields
    }
    RequiredAssessments.model_validate(complete)
    del complete[omitted]
    with pytest.raises(ValidationError) as caught:
        RequiredAssessments.model_validate(complete)
    assert caught.value.errors()[0]["loc"] == (omitted,)
    assert caught.value.errors()[0]["type"] == "missing"


def test_all_observed_nested_data_is_addressable_with_escaped_keys():
    packet = dict(
        answer="x",
        execution_evidence=[dict(data={"arbitrary/key~": [False, None, "text"]})],
    )
    catalog = evidence_catalog(packet)
    reference = "/execution_evidence/0/data/arbitrary~1key~0/2"
    assert catalog[reference] == '"text"'
    assert check_references(
        packet,
        [
            dict(
                criterion="clarity",
                references=[dict(reference=reference, value_json='"text"')],
            )
        ],
    )["passed"]
    assert "/evaluation_contract" not in catalog
