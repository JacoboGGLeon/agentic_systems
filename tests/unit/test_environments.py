from __future__ import annotations


import pytest

from agentic_systems.environments import (
    AgenticEnvironment,
    EnvironmentTransition,
    _call_with_supported_args,
    _transition_output,
    _transition_route,
    environment_lineage,
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


def test_environment_episode_summary_normalized_lineage_and_helpers():
    def transition(row, action, info):
        return {
            "route": row.get("route"),
            "summary": row.get("summary"),
            "memory_seen": info["memory"],
        }

    def reward(state, row):
        return 1.0 if row.get("ok") else 0.0

    def update(memory, graph_state, row, action, env):
        return {"count": memory.get("count", 0) + 1, "last": row["id"]}

    env = AgenticEnvironment(
        records=[
            {"id": 1, "ok": True, "route": "tool", "summary": "good"},
            {"id": 2, "ok": False, "route": "agent", "summary": "bad"},
        ],
        transition_fn=transition,
        initial_memory={"count": 0},
        reward_fn=reward,
        memory_updater=update,
        observation_mapper=lambda row, env: {"case": row["id"], "memory": env.memory},
        render_mode="ansi",
    )
    obs, info = env.reset(seed=7, options={"episode_id": "ep", "memory": {"count": 10}})
    assert obs["case"] == 1
    assert info["episode_id"] == "ep"
    next_obs, reward_value, terminated, truncated, step_info = env.step(action={"a": 1})
    assert reward_value == 1.0
    assert terminated is False
    assert truncated is False
    assert next_obs["case"] == 2
    env.step()
    assert env.render().startswith("agentic_environment episode=ep")
    summary = env.summary()
    assert summary["passed_steps"] == 1
    normalized = env.normalized()
    assert normalized["ok"] is False
    assert normalized["errors"][0]["code"] == "environment_step_failed"
    lineage = env.lineage(question="q", goal="g", max_steps=1)
    assert lineage.name.endswith(".lineage")
    assert len(lineage.steps) == 3
    assert (
        environment_lineage(env, name="custom", tags=["x"], metadata={"m": 1}).metadata[
            "m"
        ]
        == 1
    )

    history_env = AgenticEnvironment(
        records=[{"id": 1}], graph=CompilableGraph(), render_mode="history"
    )
    history_env.reset()
    history_env.step()
    assert isinstance(history_env.render(), list)

    assert (
        _transition_route(
            EnvironmentTransition(
                "e",
                0,
                {"tool": "row_tool"},
                None,
                {"selected_agent": "agent"},
                1,
                True,
                False,
                {},
            )
        )
        == "agent"
    )
    assert (
        _transition_route(
            EnvironmentTransition(
                "e", 0, {"route": "row_route"}, None, {}, 1, True, False, {}
            )
        )
        == "row_route"
    )
    assert (
        _transition_route(
            EnvironmentTransition("e", 0, {}, None, {}, 1, True, False, {})
        )
        == "unknown"
    )
    assert _transition_output({"answer": "yes"}) == "yes"
    assert _transition_output({"agent_result": {"answer": "nested"}}) == "nested"
    assert "ok" in _transition_output({"result": {"ok": True, "tool": "t"}})
    assert _transition_output({"result": object()}) == ""

    assert _call_with_supported_args(lambda *args: len(args), 1, 2, 3) == 3

    closed = AgenticEnvironment(records=[], graph=SyncGraph())
    closed._closed = True
    with pytest.raises(RuntimeError):
        closed.reset()
    with pytest.raises(ValueError):
        env.reset(options={"start_index": 99})
    bad_env = AgenticEnvironment(
        records=[{"id": 1}], transition_fn=lambda row, action, info: "bad"
    )
    bad_env.reset()
    with pytest.raises(TypeError):
        bad_env.step()
