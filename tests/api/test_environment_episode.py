import sys
import types

import pandas as pd
import pytest

from agentic_systems import AgenticEnvironment, AgenticSystem, EnvironmentTransition
from agentic_systems.environments import build_single_agent_step_graph
from agentic_systems.environments import _compile_graph, _records_to_dicts


class EchoGraph:
    def __init__(self):
        self.states = []

    def invoke(self, state):
        self.states.append(state)
        row = state["row"]
        prior = state.get("memory", {}).get("processed", [])
        return {
            **state,
            "agent_text": f"processed {row['case_id']}",
            "business_ok": bool(row.get("expected_ok", True)),
            "memory": {"processed": [*prior, row["case_id"]]},
        }


class CompilableGraph:
    def __init__(self):
        self.compiled = EchoGraph()

    def compile(self):
        return self.compiled


def reward_fn(graph_state, row, action, env):
    return 1.0 if graph_state["business_ok"] else -1.0


def test_agentic_environment_dataframe_episode_memory_reward_and_render():
    frame = pd.DataFrame([
        {"case_id": "case_001", "expected_ok": True},
        {"case_id": "case_002", "expected_ok": False},
    ])
    env = AgenticEnvironment(records=frame, graph=EchoGraph(), reward_fn=reward_fn, render_mode="ansi")

    observation, info = env.reset(seed=7)
    assert observation == {"case_id": "case_001", "expected_ok": True}
    assert info["episode_id"] == "episode-7"
    assert env.episode_id == "episode-7"

    observation, reward, terminated, truncated, info = env.step(action={"attempt": 1})
    assert observation == {"case_id": "case_002", "expected_ok": False}
    assert reward == 1.0
    assert terminated is False and truncated is False
    assert env.memory == {"processed": ["case_001"]}
    assert info["transition"]["graph_state"]["agent_text"] == "processed case_001"
    assert env.current_step == 1
    assert len(env.history) == 1

    observation, reward, terminated, truncated, info = env.step()
    assert observation is None
    assert reward == -1.0
    assert terminated is True and truncated is False
    assert env.memory == {"processed": ["case_001", "case_002"]}
    assert "done=True" in env.render()

    with pytest.raises(RuntimeError, match="Episode is done"):
        env.step()


def test_agentic_environment_options_truncation_mappers_and_history_render():
    rows = [{"case_id": "a"}, {"case_id": "b"}, {"case_id": "c"}]

    def observe(row, env):
        return {"id": row["case_id"], "step": env.current_step}

    def state_factory(row, action, env):
        return {"row": row, "action": action, "memory": {"last": row["case_id"]}}

    def update_memory(current, graph_state, row, action, env):
        return {"last": row["case_id"], "action": action}

    env = AgenticEnvironment(
        records=rows,
        graph=CompilableGraph(),
        max_steps=1,
        observation_mapper=observe,
        state_factory=state_factory,
        memory_updater=update_memory,
        render_mode="history",
    )
    observation, info = env.reset(options={"episode_id": "demo", "start_index": 1, "memory": {"seed": True}})
    assert observation == {"id": "b", "step": 0}
    observation, reward, terminated, truncated, info = env.step(action="approve")
    assert observation is None
    assert terminated is False and truncated is True
    assert env.memory == {"last": "b", "action": "approve"}
    assert env.render()[0]["step_index"] == 0


def test_agentic_environment_error_paths_and_records_conversion():
    assert _records_to_dicts({"one": 1}) == [{"one": 1}]
    assert _records_to_dicts(({"x": 1},)) == [{"x": 1}]
    with pytest.raises(TypeError, match="records must"):
        _records_to_dicts("bad")

    env = AgenticEnvironment(records=[{"case_id": "x"}], graph=EchoGraph())
    with pytest.raises(RuntimeError, match="reset"):
        env.step()
    with pytest.raises(ValueError, match="start_index"):
        env.reset(options={"start_index": 3})
    env.reset(seed=1)
    env.close()
    with pytest.raises(RuntimeError, match="closed"):
        env.step()
    with pytest.raises(RuntimeError, match="closed"):
        env.reset()

    class BadState:
        def __call__(self, row, action, env):
            return "not dict"

    env = AgenticEnvironment(records=[{"case_id": "x"}], graph=EchoGraph(), state_factory=BadState())
    env.reset(seed=1)
    with pytest.raises(TypeError, match="state_factory"):
        env.step()

    class NoInvoke:
        pass

    env = AgenticEnvironment(records=[{"case_id": "x"}], graph=NoInvoke())
    env.reset(seed=1)
    with pytest.raises(TypeError, match="invoke"):
        env.step()

    class ScalarGraph:
        def invoke(self, state):
            return "scalar"

    env = AgenticEnvironment(records=[{"case_id": "x"}], graph=ScalarGraph(), keep_history=False)
    env.reset(seed=1)
    _, _, terminated, truncated, info = env.step()
    assert info["graph_state"] == {"output": "scalar"}
    assert terminated is True and truncated is False
    assert env.history == ()
    assert _compile_graph(ScalarGraph()).invoke({}) == "scalar"
    assert _compile_graph(NoInvoke()).__class__ is NoInvoke

    default_render_env = AgenticEnvironment(records=[{"case_id": "x"}], graph=EchoGraph())
    default_render_env.reset(seed=2)
    assert default_render_env.render()["total_records"] == 1


def test_system_environment_factory_and_langgraph_builder_with_fake_langgraph(monkeypatch):
    created = {}

    class FakeStateGraph:
        def __init__(self, state):
            created["state"] = state
            self.nodes = []
            self.edges = []

        def add_node(self, name, node):
            self.nodes.append((name, node))

        def add_edge(self, start, end):
            self.edges.append((start, end))

        def compile(self):
            created["nodes"] = self.nodes
            created["edges"] = self.edges
            return EchoGraph()

    langgraph_mod = types.ModuleType("langgraph")
    graph_mod = types.ModuleType("langgraph.graph")
    graph_mod.START = "__start__"
    graph_mod.END = "__end__"
    graph_mod.StateGraph = FakeStateGraph
    monkeypatch.setitem(sys.modules, "langgraph", langgraph_mod)
    monkeypatch.setitem(sys.modules, "langgraph.graph", graph_mod)

    system = AgenticSystem(model="demo", region="us-east-1", strict=False)

    class StaticAgent:
        def as_node(self, **kwargs):
            created["node_kwargs"] = kwargs
            return lambda state: {"agent_text": "ok"}

    graph = build_single_agent_step_graph(StaticAgent(), input="row", output="answer", trace="trace", node_name="step")
    env = system.environment([{"case_id": "case"}], graph=graph, name="episode_env")
    observation, info = env.reset(seed=9)
    assert observation["case_id"] == "case"
    _, _, terminated, _, info = env.step()
    assert terminated is True
    assert created["edges"] == [("__start__", "step"), ("step", "__end__")]
    assert created["node_kwargs"]["input"] == "row"
    assert info["name"] == "episode_env"


def test_environment_transition_to_dict():
    transition = EnvironmentTransition(
        episode_id="e",
        step_index=0,
        row={"id": 1},
        action=None,
        graph_state={"ok": True},
        reward=1.0,
        terminated=True,
        truncated=False,
        memory={"m": 1},
    )
    assert transition.to_dict()["memory"] == {"m": 1}
