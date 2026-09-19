import json
from pathlib import Path

import pytest

from scripts.unambiguous_lm_gate import (
    prepare_packet,
    oracle_decisions,
    run_gate,
    render_didactic_markdown,
    verify_batch,
)


FIXTURE = Path(__file__).parents[1] / "fixtures" / "unambiguous_lm_gate_v1.json"


def case():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_oracle_covers_each_unambiguous_status_and_strict_json_type():
    packet = prepare_packet(case())
    decisions = oracle_decisions(packet)["decisions"]
    by_id = {item["assertion_id"]: item for item in decisions}
    assert by_id["a01-supported-bool"]["status"] == "supported"
    assert by_id["a02-contradicted-bool"]["status"] == "contradicted"
    assert by_id["a05-supported-number"]["status"] == "supported"
    assert by_id["a06-contradicted-json-type"]["status"] == "contradicted"
    assert by_id["a08-unknown-missing-path"]["status"] == "unknown"
    assert by_id["a10-unknown-record"]["status"] == "unknown"


def test_exact_oracle_batch_passes_and_single_wrong_status_fails():
    packet = prepare_packet(case())
    oracle = oracle_decisions(packet)
    assert verify_batch(packet, oracle)["passed"] is True
    changed = json.loads(json.dumps(oracle))
    changed["decisions"][0]["status"] = "contradicted"
    report = verify_batch(packet, changed)
    assert report["passed"] is False
    assert report["mismatches"][0]["assertion_id"] == "a01-supported-bool"


def test_missing_reordered_or_invented_decisions_do_not_pass():
    packet = prepare_packet(case())
    oracle = oracle_decisions(packet)
    missing = {"decisions": oracle["decisions"][:-1]}
    assert verify_batch(packet, missing)["passed"] is False
    reordered = {"decisions": list(reversed(oracle["decisions"]))}
    assert verify_batch(packet, reordered)["passed"] is False
    invented = json.loads(json.dumps(oracle))
    invented["decisions"][0]["assertion_id"] = "invented"
    assert verify_batch(packet, invented)["passed"] is False


def test_unknown_cannot_cite_evidence():
    packet = prepare_packet(case())
    oracle = oracle_decisions(packet)
    changed = json.loads(json.dumps(oracle))
    changed["decisions"][7]["evidence_ids"] = ["lookup-b"]
    with pytest.raises(ValueError, match="unknown_must_not_cite"):
        verify_batch(packet, changed)


def test_didactic_report_explains_every_stage_and_assertion():
    raw = case()
    packet = prepare_packet(raw)
    report = run_gate(
        raw,
        "python-runtime",
        "native",
        "python-runtime",
        control_decisions=oracle_decisions(packet),
    )
    evaluation = report["evaluation"]
    assert evaluation["summary"]["stages_passed"] == 3
    assert evaluation["summary"]["assertions_passed"] == 10
    assert len(evaluation["stages"]) == 3
    assert len(evaluation["assertions"]) == 10
    rendered = render_didactic_markdown(evaluation)
    assert "Agent and step evaluation" in rendered
    assert "Assertion evaluation" in rendered
    assert "a06-contradicted-json-type" in rendered
    assert "Observed and expected" in rendered or "value or type differ" in rendered


@pytest.mark.parametrize(
    "framework", ["native", "langgraph", "openai-agents", "strands"]
)
def test_three_stage_control_pipeline_is_framework_portable(framework):
    raw = case()
    packet = prepare_packet(raw)
    report = run_gate(
        raw,
        "python-runtime",
        framework,
        "python-runtime",
        control_decisions=oracle_decisions(packet),
    )
    assert report["execution_passed"], report["result"]
    assert report["decision_passed"]
    assert report["passed"]
    assert len(report["result"]["children"]) == 3
