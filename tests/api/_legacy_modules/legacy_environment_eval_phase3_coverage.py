
from __future__ import annotations

from types import SimpleNamespace

import pytest

from agentic_systems.environments import (
    AgenticEnvironment,
    EnvironmentTransition,
    _call_with_supported_args,
    _map_agent_result,
    _read_graph_input,
    _transition_output,
    _transition_route,
    build_agent_step_graph,
    build_dynamic_agent_router_graph,
    build_planned_agent_graph,
    environment_lineage,
)
import agentic_systems.evals as evals_module
from agentic_systems.evals import EvalCaseResult, EvalReport, Evaluator, run_eval
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
            data={"tool": self.name, "value": input, "ok": self.ok, "summary": f"summary {input}"},
            ok=self.ok,
            tool_events=[],
            mode=mode,
        )


class SyncGraph:
    def invoke(self, state):
        row = state["row"]
        return {**state, "route": row.get("route", "sync"), "summary": row.get("summary", "ok"), "result": {"text": "result text"}}


class CompilableGraph:
    def compile(self):
        return SyncGraph()


def test_agent_graph_wrappers_router_plan_and_mapping_branches():
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
        _map_agent_result(RunResult(text="x"), {}, lambda result, state: "bad", None, None)

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
    planned_state = planned.invoke({"row": {"agent": "worker", "input": "task", "step_id": "s1", "reason": "demo", "expected_tools": ["t"]}})
    assert planned_state["selected_agent"] == "worker"
    assert planned_state["plan"]["expected_tools"] == ["t"]
    with pytest.raises(TypeError):
        planned.invoke({"row": "bad"})
    with pytest.raises(KeyError):
        planned.invoke({"row": {"agent": "unknown", "input": "x"}})
    with pytest.raises(KeyError):
        planned.invoke({"row": {"agent": "worker"}})


def test_environment_episode_summary_normalized_lineage_and_helpers():
    def transition(row, action, info):
        return {"route": row.get("route"), "summary": row.get("summary"), "memory_seen": info["memory"]}

    def reward(state, row):
        return 1.0 if row.get("ok") else 0.0

    def update(memory, graph_state, row, action, env):
        return {"count": memory.get("count", 0) + 1, "last": row["id"]}

    env = AgenticEnvironment(
        records=[{"id": 1, "ok": True, "route": "tool", "summary": "good"}, {"id": 2, "ok": False, "route": "agent", "summary": "bad"}],
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
    assert environment_lineage(env, name="custom", tags=["x"], metadata={"m": 1}).metadata["m"] == 1

    history_env = AgenticEnvironment(records=[{"id": 1}], graph=CompilableGraph(), render_mode="history")
    history_env.reset()
    history_env.step()
    assert isinstance(history_env.render(), list)

    assert _transition_route(EnvironmentTransition("e", 0, {"tool": "row_tool"}, None, {"selected_agent": "agent"}, 1, True, False, {})) == "agent"
    assert _transition_route(EnvironmentTransition("e", 0, {"route": "row_route"}, None, {}, 1, True, False, {})) == "row_route"
    assert _transition_route(EnvironmentTransition("e", 0, {}, None, {}, 1, True, False, {})) == "unknown"
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
    bad_env = AgenticEnvironment(records=[{"id": 1}], transition_fn=lambda row, action, info: "bad")
    bad_env.reset()
    with pytest.raises(TypeError):
        bad_env.step()


def test_eval_report_lineage_summaries_and_evaluator_alias(monkeypatch):
    case = EvalCaseResult(
        name="case1",
        ok=False,
        input={"q": "x"},
        expected={"data_contains": {"tool": "calc", "value": 42}},
        result={"ok": False, "answer": {"text": "bad", "final": {"summary": "final summary"}, "data": {"tool": "calc", "value": 1}}, "tools": [{"name": "calc", "ok": True, "summary": "used"}]},
        validation={"ok": False},
    )
    assert case.to_dict()["name"] == "case1"
    report = EvalReport(ok=False, total=1, passed=0, failed=1, pass_rate=0.0, cases=[case])
    assert report.normalized()["errors"][0]["message"] == "case1"
    with pytest.raises(AssertionError):
        report.raise_if_failed()
    lineage = report.lineage(question="q", goal="g", tags=["tag"], metadata={"m": 1})
    assert lineage.ok is False
    assert lineage.tags == ["eval", "tag"]
    assert lineage.metadata["m"] == 1

    must_call_case = EvalCaseResult(name="case2", ok=True, input="x", expected={"must_call": ["tool"]}, result={"data": {"result": 7, "ok": True}}, validation={"ok": True})
    tools_only_case = EvalCaseResult(name="case3", ok=True, input="x", expected={}, result={"tools": [{"name": "tool_a"}]}, validation={"ok": True})
    empty_case = EvalCaseResult(name="case4", ok=True, input="x", expected={}, result={}, validation={"ok": True})
    unknown_expected_case = EvalCaseResult(name="case5", ok=True, input="x", expected={"other": "value"}, result={"answer": {"data": "not-dict", "final": {"result": 9}}}, validation={"ok": True})
    EvalReport(ok=True, total=4, passed=4, failed=0, pass_rate=1.0, cases=[must_call_case, tools_only_case, empty_case, unknown_expected_case]).lineage()

    class SyncOnlyAgent:
        def run_sync(self, input_value, mode="eval", config=None):
            return RunResult(text="ok", data={"answer": "ok"}, ok=True)

    cases = [{"name": "ok", "input": "x", "expected": {"text_contains": "ok"}}]
    evaluator = Evaluator()
    report_from_alias = evaluator.run(SyncOnlyAgent(), cases)
    assert report_from_alias.ok is True
    assert evaluator.evaluate_agent(SyncOnlyAgent(), cases).ok is True
    assert run_eval(SyncOnlyAgent(), cases, environment_kwargs={"name": "custom_eval"}).passed == 1

    monkeypatch.setattr(evals_module, "_case_actual_evidence", lambda case: {"final": "not-dict", "data": "not-dict", "tools": []})
    assert evals_module._case_actual_summary(empty_case) == "sin salida estructurada"
