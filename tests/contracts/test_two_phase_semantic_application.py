import pytest
from pydantic import ValidationError

from scripts.two_phase_semantic_application import (
    Verses,
    accepted,
    compact_judge_payload,
    run_case,
)
from scripts.semantic_e2e_application import JudgeCriteria


@pytest.mark.parametrize(
    "framework", ["native", "langgraph", "openai-agents", "strands"]
)
def test_python_controls(framework):
    report = run_case("python-runtime", framework, "python-runtime")
    assert report["passed"], report.get("failure")
    assert report["deterministic_passed"]
    assert report["semantic_inference_verified"] is False
    assert report["answer"] == "Quiet stars\n323\nNumbers sing"
    packet = compact_judge_payload(report)
    assert packet["selection"]["tool_event_id"] == report["selection"]["tool_event_id"]
    assert packet["execution_evidence"][0]["tools"][0]["output"] == {"product": 323}
    assert all(
        "messages" not in stage and "children" not in stage
        for stage in packet["execution_evidence"]
    )
    report["deterministic_passed"] = False
    with pytest.raises(ValueError, match="integrity_failure"):
        compact_judge_payload(report)


def test_judge_cannot_override_integrity_or_one_failed_criterion():
    decision = dict(
        score=1.0,
        criteria={key: 1.0 for key in JudgeCriteria.model_fields},
        rationale="All checked",
    )
    assert accepted(True, True, decision)
    assert accepted(True, True, {**decision, "findings": []})
    with pytest.raises(ValidationError):
        accepted(True, True, {**decision, "unrecognized": "not silently ignored"})
    assert not accepted(False, True, decision)
    assert not accepted(True, False, decision)
    decision["criteria"]["request_fulfillment"] = 0
    assert not accepted(True, True, decision)


@pytest.mark.parametrize(
    "bad", ["Quiet stars  ", "One", "Two 3", "Two\nlines", " Quiet stars"]
)
def test_strict_output_is_not_repaired(bad):
    with pytest.raises(ValidationError):
        Verses(verso_inicial=bad, verso_final="Numbers sing")
