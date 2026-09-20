import json

import pytest
import agentic_systems as toolkit
from scripts.semantic_claim_checks import verify_evidence_field


@pytest.mark.parametrize(
    "field,claimed,expected,reason",
    [
        ("length", 3, True, "exact_match"),
        ("length", 323, False, "evidence_value_mismatch"),
        ("length", "3", False, "evidence_value_mismatch"),
        ("length", True, False, "evidence_value_mismatch"),
        ("recipient", "specialist", True, "exact_match"),
        ("next_recipient", "another", False, "missing_evidence_field"),
    ],
)
def test_factual_claim_gate_uses_public_tool_and_agent(
    field, claimed, expected, reason
):
    agent = toolkit.agent(
        name="fact_checker",
        runtime=toolkit.runtime(provider="python-runtime"),
        tools=[verify_evidence_field],
    )
    result = agent.run(
        {
            "tool": "verify_evidence_field",
            "input": {
                "evidence_json": json.dumps({"length": 3, "recipient": "specialist"}),
                "field": field,
                "claimed_json": json.dumps(claimed),
            },
        }
    )
    assert result.ok
    output = result.normalized()["tools"][0]["output"]
    assert output["supported"] is expected
    assert output["reason"] == reason
    assert result.lineage().steps
