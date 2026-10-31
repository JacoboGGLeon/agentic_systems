"""Saved evidence must remain strict, inspectable and honest about failures."""

import json

import pydantic
import pytest

import agentic_systems as toolkit


@pytest.mark.parametrize("options,error", [
    ({"status": "invented"}, ValueError),
    ({"status": "paused"}, ValueError),
    ({"ok": 1}, TypeError),
    ({"data": []}, TypeError),
    ({"children": [object()]}, TypeError),
    ({"tool_events": [object()]}, TypeError),
    ({"data": {1: "invalid JSON key"}}, TypeError),
])
def test_invalid_saved_result_does_not_enter_the_evidence_contract(options, error):
    with pytest.raises(error):
        toolkit.RunResult(**options)


def test_lineage_truncation_preserves_failure_visibility_and_valid_json():
    children = tuple(toolkit.RunResult(data={"value": i}, meta={"name": f"step-{i}", "kind": "node"}) for i in range(13))
    failed = toolkit.RunResult(ok=False, errors=({"code": "business-failure"},), meta={"name": "late-failure"})
    result = toolkit.RunResult(ok=False, children=(*children, failed), meta={"name": "audit"})
    lineage = result.lineage()
    assert "failures outside this view" in lineage.render()
    assert lineage.explain()["ok"] is False
    assert lineage.to_dict()["execution_id"] == result.execution_id
    assert json.loads(lineage.to_prompt_context())["failed_steps"] > 0
    for size in (0, 1):
        with pytest.raises(ValueError):
            lineage.to_prompt_context(max_chars=size)
    assert result.trace("full") == result.to_dict()
    assert result.trace("compact", max_steps=2)["ok"] is False
    with pytest.raises(ValueError):
        result.trace("invented")
    with pytest.raises(ValueError):
        result.trace(max_steps=0)
    with pytest.raises(ValueError):
        result.lineage(max_tool_rows=-1)
    assert "omitted" in result.human_results(max_steps=1)
    assert len(result.human_results(max_chars=256)) <= 256


def test_saved_invariants_detect_duplicated_misparented_and_false_success_evidence():
    failed = toolkit.RunResult(ok=False, execution_id="duplicate", parent_execution_id="wrong")
    inconsistent = toolkit.RunResult(
        children=(failed, failed), usage={"input_tokens": -1},
        tool_events=({"id": "tool", "name": "bad", "ok": True, "error": {"message": "failed"}},),
    )
    validation = inconsistent.check_invariants()
    codes = {issue["code"] for issue in validation.issues}
    assert {"duplicate_execution_id", "parent_mismatch", "success_with_failed_evidence", "inconsistent_tool_event", "negative_usage"} <= codes
    assert not validation.to_dict()["ok"]


def test_human_views_restore_episode_inputs_and_show_recorded_attempts():
    episode = toolkit.RunResult(
        data={"outputs": [{"value": 3}], "history": [{"record": {"value": 2}}], "summary": {"processed": 1}},
        meta={"kind": "environment", "name": "day"},
    )
    assert '"records_observed"' in episode.human_results()
    attempt = toolkit.RunResult(meta={"kind": "node", "name": "retry", "scheduler_execution": {
        "attempt_history": [{"number": 1, "status": "failed"}, {"number": 2, "status": "completed"}]}})
    assert "Attempt 1: failed" in attempt.human_results()


def test_nonfinite_pydantic_data_and_paused_views_are_explicit():
    class Data(pydantic.BaseModel):
        value: float

    with pytest.raises(TypeError):
        toolkit.Context({"nested": Data(value=float("inf"))})
    paused = toolkit.RunResult(status="paused", interrupts=({"id": "approval"},), continuation={"program": "local"})
    assert json.loads(paused.lineage().to_prompt_context())["status"] == "paused"
