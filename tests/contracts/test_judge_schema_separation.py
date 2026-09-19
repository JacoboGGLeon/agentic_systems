from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from agentic_systems.providers.openai_runtime import _openai_tools
from scripts.two_phase_semantic_application import (
    LiteralObservation,
    ObservedJudgment,
    compact_judge_payload,
    record_observed_judgment,
    run_case,
)


def test_provider_projection_preserves_closed_nested_schema():
    agent = SimpleNamespace(
        tools=[], available_tools=lambda: [record_observed_judgment]
    )
    schema = _openai_tools(None, agent)[0]["function"]["parameters"]
    assert schema == ObservedJudgment.model_json_schema()
    nested = schema["$defs"]["LiteralObservation"]
    assert nested["additionalProperties"] is False
    assert set(nested["properties"]) == set(LiteralObservation.model_fields)


@pytest.mark.parametrize(
    "extra,value",
    [
        ("length_unit", "unicode_code_points"),
        ("line_count", 3),
        ("middle_line_index", 1),
    ],
)
def test_failed_live_extra_fields_still_rejected(extra, value):
    with pytest.raises(ValidationError) as error:
        LiteralObservation.model_validate(
            dict(
                expected_value=323,
                expected_text="323",
                expected_length=3,
                **{extra: value},
            )
        )
    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_packet_separates_returned_facts_from_format_rules():
    report = run_case("python-runtime", "native", "python-runtime")
    packet = compact_judge_payload(report)
    assert set(packet["evaluation_contract"]) == set(LiteralObservation.model_fields)
    assert not set(packet["evaluation_contract"]) & set(packet["format_requirements"])
    assert packet["format_requirements"] == dict(
        length_unit="unicode_code_points", line_count=3, middle_line_index=1
    )
    assert packet["evaluation_contract"]["expected_length"] == len(
        packet["evaluation_contract"]["expected_text"]
    )
