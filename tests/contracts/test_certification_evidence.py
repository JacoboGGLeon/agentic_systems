from copy import deepcopy

import pytest

from agentic_systems import RunResult
from agentic_systems.tools.events import ToolEvent
from scripts.certification_evidence import select_single_tool_result


def source():
    event = ToolEvent(id="call", name="operation", input={"x": 2}, output={"value": 4})
    child = RunResult(
        execution_id="child", parent_execution_id="root", tool_events=[event]
    )
    return RunResult(
        execution_id="root", children=[child], tool_events=[deepcopy(event)]
    )


def select(result):
    return select_single_tool_result(
        result,
        tool_name="operation",
        expected_input={"x": 2},
        observed_output={"value": 4},
    )


def test_ancestor_projection_and_mutation_isolation():
    result = source()
    selected = select(result)
    assert selected.owner_execution_id == "child"
    assert selected.source_execution_id == "root"
    result.children[0].tool_events[0].output["value"] = 999
    selected.payload()["value"] = 123
    assert selected.payload() == {"value": 4}


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda r: setattr(r, "execution_id", None), "missing_execution_identity"),
        (
            lambda r: setattr(r.children[0], "execution_id", "root"),
            "invalid_execution_identity",
        ),
        (
            lambda r: setattr(r.children[0], "parent_execution_id", "wrong"),
            "invalid_parent_reference",
        ),
        (lambda r: setattr(r, "ok", False), "failed_execution"),
        (lambda r: setattr(r.children[0], "ok", False), "failed_execution"),
        (lambda r: setattr(r.tool_events[0], "name", "invented"), "unexpected_tool"),
        (lambda r: setattr(r.tool_events[0], "ok", False), "failed_tool"),
        (
            lambda r: setattr(r.tool_events[0], "error", {"code": "failure"}),
            "failed_tool",
        ),
        (lambda r: r.tool_events[0].input.update(x=True), "input_mismatch"),
        (lambda r: r.tool_events[0].output.update(value=5), "observation_mismatch"),
        (
            lambda r: r.tool_events.append(deepcopy(r.tool_events[0])),
            "duplicate_or_missing_event_identity",
        ),
        (
            lambda r: setattr(r.children[0].tool_events[0], "id", "second-call"),
            "expected_one_real_call",
        ),
        (
            lambda r: setattr(r.children[0].tool_events[0], "duration_ms", 10),
            "conflicting_event_projection",
        ),
    ],
)
def test_corruption_rejected_for_the_right_reason(mutation, reason):
    result = source()
    mutation(result)
    with pytest.raises(ValueError, match=f"^{reason}$"):
        select(result)


def test_missing_and_sibling_reuse_are_not_ancestor_projections():
    result = source()
    result.tool_events = []
    result.children[0].tool_events = []
    with pytest.raises(ValueError, match="expected_one_real_call"):
        select(result)
    result = source()
    sibling = deepcopy(result.children[0])
    sibling.execution_id = "sibling"
    result.children.append(sibling)
    with pytest.raises(ValueError, match="shared_identity_between_siblings"):
        select(result)


def test_direct_execution_is_a_valid_positive():
    result = source().children[0]
    result.parent_execution_id = None
    assert select(result).owner_execution_id == "child"
