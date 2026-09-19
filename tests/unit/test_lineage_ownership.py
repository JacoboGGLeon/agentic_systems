from agentic_systems.results import RunResult, ToolEvent


def test_parent_tools_survive_with_children():
    own = ToolEvent(id="delegate-1", name="delegate", input={}, output={}, ok=True)
    event = ToolEvent(id="calc-1", name="calculate", input={}, output={}, ok=True)
    child = RunResult(tool_events=[event])
    parent = RunResult(children=[child], tool_events=[own, event])
    assert [s.source for s in parent.lineage().steps if s.kind == "tool"] == [
        "delegate",
        "calculate",
    ]


def test_nested_projections_preserve_distinct_calls():
    first = ToolEvent(id="call-1", name="calculate", input={}, output={}, ok=True)
    second = ToolEvent(id="call-2", name="calculate", input={}, output={}, ok=True)
    leaf = RunResult(tool_events=[first, second])
    middle = RunResult(children=[leaf], tool_events=[first, second])
    root = RunResult(children=[middle], tool_events=[first, second])
    assert len([s for s in root.lineage().steps if s.kind == "tool"]) == 2
