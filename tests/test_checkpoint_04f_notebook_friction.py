from __future__ import annotations

from pydantic import BaseModel

from agentic_systems import AgenticEnvironment, AgenticSystem, Evaluator, Tool


class SumInput(BaseModel):
    a: int
    b: int


class SumOutput(BaseModel):
    result: int


def test_schema_backed_tool_does_not_require_duplicate_parameter_annotations() -> None:
    def sumar_con_schema(a, b) -> dict:
        return {"result": a + b}

    tool = Tool(name="sumar_con_schema", function=sumar_con_schema, input_schema=SumInput, output_schema=SumOutput)

    check = tool.check()
    assert check.ok is True
    result = tool.run({"a": "17", "b": 25})
    assert result.ok is True
    assert result.data == {"result": 42}


def test_system_exposes_public_tool_names_for_notebook_iteration() -> None:
    system = AgenticSystem(model="demo", region="us-east-1")

    @system.tool
    def sumar(a: int, b: int) -> dict:
        return {"result": a + b}

    assert system.public_tool_names == ("sumar",)
    assert [tool.name for tool in system.public_tools.values()] == ["sumar"]


def test_evaluator_public_facade_delegates_to_agent_eval() -> None:
    class StaticAgent:
        def run(self, value, *, mode="eval", config=None):
            from agentic_systems import RunResult

            return RunResult(text=str(value), data={}, ok=True, engine="test", mode=mode)

    report = Evaluator().evaluate_agent(
        StaticAgent(),
        cases=[{"name": "case", "input": "ok", "expected": {"text_contains": "ok"}}],
    )
    assert report.ok is True
    assert report.total == 1


def test_environment_accepts_simple_transition_fn_and_reward_fn() -> None:
    records = [{"case_id": "a", "expected": True}]

    def transition(row, action, info):
        return {"business_ok": row["expected"], "memory": {"seen": [row["case_id"]]}}

    def reward(state):
        return 1.0 if state["business_ok"] else 0.0

    env = AgenticEnvironment(
        name="simple_episode",
        records=records,
        transition_fn=transition,
        reward_fn=reward,
        episode_id="episode-demo",
    )
    observation, info = env.reset()
    assert info["episode_id"] == "episode-demo"
    assert observation == records[0]
    observation, reward_value, terminated, truncated, info = env.step({})
    assert observation is None
    assert reward_value == 1.0
    assert terminated is True
    assert truncated is False
    assert env.memory == {"seen": ["a"]}


def test_transition_fn_error_paths_are_clear() -> None:
    from agentic_systems.environments import _TransitionFunctionGraph

    env = AgenticEnvironment(records=[{"case_id": "x"}], graph={"placeholder": True})

    try:
        _TransitionFunctionGraph(None, env)
    except TypeError as exc:
        assert "transition_fn must be provided" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("Expected TypeError")

    adapter = _TransitionFunctionGraph(lambda row, action, info: "not dict", env)
    try:
        adapter.invoke({"row": {"case_id": "x"}, "action": None, "memory": {}})
    except TypeError as exc:
        assert "transition_fn must return a dict" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("Expected TypeError")
