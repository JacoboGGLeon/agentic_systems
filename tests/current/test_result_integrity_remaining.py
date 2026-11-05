"""Saved evidence validates malformed inputs and retains diagnostic boundaries."""
import pytest
from pydantic import BaseModel
from agentic_systems import RunResult
from agentic_systems._results import _Event, _json


@pytest.mark.parametrize("kwargs,kind,message", [
    ({"status": "unknown"}, ValueError, "Unknown execution status"),
    ({"status": "paused"}, ValueError, "A paused result requires interrupts and a continuation, without errors"),
    ({"ok": 1}, TypeError, "RunResult requires boolean ok and dictionary data"),
    ({"data": []}, TypeError, "RunResult requires boolean ok and dictionary data"),
    ({"children": [1]}, TypeError, "children must contain RunResult values"),
    ({"tool_events": [1]}, TypeError, "tool_events must contain event records"),
])
def test_saved_result_rejection_is_actionable(kwargs, kind, message):
    with pytest.raises(kind) as caught:
        RunResult(**kwargs)
    assert str(caught.value) == message


@pytest.mark.parametrize("changes", [{"ok": False}, {"errors": [{"code": "failed"}]}, {"interrupts": []}, {"continuation": None}])
def test_paused_result_requires_every_resume_condition(changes):
    values = {"status": "paused", "interrupts": [{"question": "approve"}], "continuation": {"id": "resume"}}
    with pytest.raises(ValueError) as caught:
        RunResult(**{**values, **changes})
    assert str(caught.value) == "A paused result requires interrupts and a continuation, without errors"


def test_duplicate_tool_ids_detected_without_tool_failures():
    events = (_Event("same", "first"), _Event("same", "second"))
    assert RunResult(tool_events=events).check_invariants().to_dict() == {
        "ok": False, "issues": [{"code": "inconsistent_tool_event", "path": "same"}]}


@pytest.mark.parametrize("nested", [{"values": [float("inf")]}, {"values": {"nested": float("nan")}}])
def test_pydantic_nested_nonfinite_values_rejected(nested):
    class Payload(BaseModel):
        values: object
    with pytest.raises(TypeError, match="^Expected finite JSON data$"):
        _json(Payload(**nested))


def test_nested_pydantic_model_nonfinite_values_rejected():
    class Child(BaseModel):
        value: float
    class Parent(BaseModel):
        child: Child
    with pytest.raises(TypeError, match="^Expected finite JSON data$"):
        _json(Parent(child=Child(value=float("inf"))))


def test_trace_unknown_mode_has_actionable_diagnostic():
    with pytest.raises(ValueError) as caught:
        RunResult().trace("unknown")
    assert str(caught.value) == "mode must be compact or full"


@pytest.mark.parametrize("value", [True, -1, 1.0, None])
def test_lineage_row_limit_is_nonnegative_integer(value):
    with pytest.raises(ValueError) as caught:
        RunResult().lineage(max_tool_rows=value)
    assert str(caught.value) == "max_tool_rows must be nonnegative"


def test_lineage_zero_rows_and_default_three_rows():
    run = RunResult(tool_events=(_Event("event", "rows", output={"rows": [1, 2, 3, 4]}),))
    assert run.lineage().steps[-1]["evidence"]["output"] == {"rows": [1, 2, 3]}
    assert run.lineage(max_tool_rows=0).steps[-1]["evidence"]["output"] == {"rows": []}
