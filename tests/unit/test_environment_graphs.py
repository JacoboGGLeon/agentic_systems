from __future__ import annotations


import pytest

from agentic_systems.environments import (
    _map_agent_result,
    _read_graph_input,
    build_agent_step_graph,
    build_dynamic_agent_router_graph,
    build_planned_agent_graph,
)
from agentic_systems.results import RunResult


class FakeAgent:
    def __init__(self, name="agent", ok=True):
        self.name = name
        self.ok = ok
        self.calls = []

    def run(self, input, mode="default", config=None):
        self.calls.append((input, mode, config))
        return RunResult(
            text=f"{self.name}:{input}",
            data={
                "tool": self.name,
                "value": input,
                "ok": self.ok,
                "summary": f"summary {input}",
            },
            ok=self.ok,
            tool_events=[],
            mode=mode,
        )


class SyncGraph:
    def invoke(self, state):
        row = state["row"]
        return {
            **state,
            "route": row.get("route", "sync"),
            "summary": row.get("summary", "ok"),
            "result": {"text": "result text"},
        }


class CompilableGraph:
    def compile(self):
        return SyncGraph()


def test_agent_graph_wrappers_route_plan_and_map_state():
    agent = FakeAgent("single")
    graph = build_agent_step_graph(
        agent,
        input=lambda state: state["row"]["prompt"],
        output=lambda result, state: {"custom": result.text},
        trace="trace",
        result_key="result",
        mode="eval",
        config={"max_turns": 1},
    )
    state = graph.invoke({"row": {"prompt": "hello"}})
    assert state["custom"] == "single:hello"
    assert state["result"]["text"] == "single:hello"
    assert state["trace"]["tool_event_count"] == 0

    with pytest.raises(KeyError):
        _read_graph_input({}, "missing")
    with pytest.raises(TypeError):
        _map_agent_result(
            RunResult(text="x"), {}, lambda result, state: "bad", None, None
        )

    with pytest.raises(ValueError):
        build_dynamic_agent_router_graph({}, router=lambda state, agents: "a")
    router_graph = build_dynamic_agent_router_graph(
        {"a": FakeAgent("a"), "b": FakeAgent("b")},
        router=lambda state, agents: state["row"]["agent"],
        input="row",
        selected_key="chosen",
    )
    routed = router_graph.invoke({"row": {"agent": "b", "payload": 1}})
    assert routed["chosen"] == "b"
    with pytest.raises(KeyError):
        router_graph.invoke({"row": {"agent": "missing"}})

    with pytest.raises(ValueError):
        build_planned_agent_graph({})
    planned = build_planned_agent_graph({"worker": FakeAgent("worker")})
    planned_state = planned.invoke(
        {
            "row": {
                "agent": "worker",
                "input": "task",
                "step_id": "s1",
                "reason": "demo",
                "expected_tools": ["t"],
            }
        }
    )
    assert planned_state["selected_agent"] == "worker"
    assert planned_state["plan"]["expected_tools"] == ["t"]
    with pytest.raises(TypeError):
        planned.invoke({"row": "bad"})
    with pytest.raises(KeyError):
        planned.invoke({"row": {"agent": "unknown", "input": "x"}})
    with pytest.raises(KeyError):
        planned.invoke({"row": {"agent": "worker"}})
