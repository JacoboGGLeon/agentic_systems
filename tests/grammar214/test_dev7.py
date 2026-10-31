"""One Graph grammar, typed Tools, isolated Eval memory and readable evidence."""

import json
import pydantic
import pytest
import agentic_systems as t
from langgraph.graph import StateGraph


class State(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    value: int
    seen: int | None = None


def graph(fn):
    builder = t.Graph(State)
    builder.add_node("work", fn)
    builder.add_edge(t.START, "work")
    builder.add_edge("work", t.END)
    return builder


def test_graph_is_original_langgraph_with_no_duplicate_public_names():
    assert t.Graph is StateGraph
    assert not hasattr(t, "StateGraph") and not hasattr(t, "check")
    assert (
        len(
            set(t.__all__) - {"Graph", "START", "END", "Command", "Send", "__version__"}
        )
        == 15
    )


@pytest.mark.parametrize("framework", ["native", "openai-agents", "strands"])
def test_typed_tools_bind_models_in_direct_graph_and_actor_paths(framework):
    class Quantity(pydantic.BaseModel):
        model_config = pydantic.ConfigDict(strict=True, extra="forbid")
        value: int = pydantic.Field(gt=0)

    called = []

    @t.tool(input_schema=Quantity, output_schema=Quantity)
    def increment_typed(request: Quantity) -> Quantity:
        called.append(request.value)
        return Quantity(value=request.value + 1)

    output = increment_typed.run({"value": 4})
    assert output.ok and output.data == {"value": 5}
    unit = t.Agent("graph", graph(increment_typed))
    output = unit.run({"value": 4})
    assert output.ok and output.data["value"] == 5, output.to_dict()
    actor = t.Agent(
        "actor",
        runtime=t.runtime(provider="python-runtime"),
        framework=t.framework(framework),
        skills=(t.skill(name="typed", tools=(increment_typed,)),),
    )
    output = actor.run({"value": 4})
    assert output.ok and output.data == {"value": 5}, output.to_dict()
    assert any(n.meta.get("framework_adapter") == framework for n in output.walk())
    for payload in ({}, {"value": "4"}, {"value": 0}, {"value": 4, "extra": True}):
        assert not increment_typed.run(payload).ok
    assert called == [4, 4, 4]


def test_mismatched_single_parameter_schema_fails_before_body_execution():
    class Quantity(pydantic.BaseModel):
        value: int

    with pytest.raises(TypeError, match="receives that Pydantic model"):

        @t.tool(input_schema=Quantity)
        def mismatch(value: int) -> dict:
            raise AssertionError("must not execute")


def test_eval_isolates_each_case_including_memory_in_node_closures_and_checks():
    memory = t.Memory()
    memory.remember(t.RunResult(data={"seed": True}))
    baseline = memory.read()
    seen = []

    def observe(state):
        previous = len(memory.read())
        seen.append(previous)
        memory.remember(t.RunResult(data={"temporary": state.value}))
        return {"seen": previous}

    unit = t.System("candidate", graph(observe), memory=memory)

    def check(actual, case):
        return {"ok": actual.data["seen"] == 1 and len(memory.read()) == 3}

    evaluation = t.Eval(
        "isolated",
        unit,
        (
            {"input": {"value": 1}, "expected": {"ok": True}},
            {"input": {"value": 2}, "expected": {"ok": True}},
        ),
        checks=(check,),
    )
    program = evaluation.compile()
    assert memory.read() == baseline and seen == []
    result = program.run()
    assert result.ok and result.meta["memory_isolation"] == "per_case", result.to_dict()
    assert seen == [1, 1] and memory.read() == baseline
    assert result.check_invariants().ok


def test_eval_preserves_memory_progress_within_an_environment_but_not_between_cases():
    memory = t.Memory()
    memory.remember(t.RunResult(data={"seed": True}))
    baseline = memory.read()

    def observe(state):
        return {"seen": len(memory.read())}

    unit = t.System("candidate", graph(observe), memory=memory)
    environment = t.Environment("episodes", graph(unit), ({"value": 1}, {"value": 2}))

    def check(actual, case):
        return {"ok": [row["seen"] for row in actual.data["outputs"]] == [1, 2]}

    result = t.Eval(
        "isolated",
        environment,
        (
            {"input": {}, "expected": {"ok": True}},
            {"input": {}, "expected": {"ok": True}},
        ),
        checks=(check,),
    ).run()
    assert result.ok and result.check_invariants().ok, result.to_dict()
    assert memory.read() == baseline


def test_failing_eval_restores_memory_scope():
    memory = t.Memory()
    unit = t.System(
        "candidate", graph(lambda state: {"value": state.value + 1}), memory=memory
    )
    result = t.Eval(
        "failed",
        unit,
        ({"input": {"value": 1}, "expected": {"ok": True}},),
        checks=(lambda result, case: {"ok": False},),
    ).run()
    assert not result.ok and not memory.read()
    unit.run({"value": 1})
    assert len(memory.read()) == 1


def test_nested_input_is_recorded_and_human_view_uses_real_statuses():
    @t.tool
    def increment(value: int) -> dict:
        return {"value": value + 1}

    agent = t.Agent("incrementer", graph(increment))

    def child(state):
        return agent.run({"value": state.value})

    builder = graph(child)

    def choose(state):
        return "approved"

    builder.add_node("approved", lambda state: {"seen": state.value})
    builder.edges.remove(("work", t.END))
    builder.add_conditional_edges("work", choose, ["approved"])
    builder.add_edge("approved", t.END)
    result = t.System("application", builder).run({"value": 4})
    nested = next(n for n in result.walk() if n.meta.get("name") == "incrementer")
    assert nested.meta["input"] == {"value": 4}
    text = result.human_results(max_steps=20)
    assert "Agent incrementer: completed" in text
    assert "Tool increment: completed" in text and text.count("Tool increment:") == 1
    assert 'Decision work -> "approved"' in text
    assert '"status"' not in text and 'name":"tool' not in text
    assert result.execution_id in text
    assert "Input: not recorded" not in nested.human_results()
    assert result.check_invariants().ok
    json.dumps(result.to_dict(), allow_nan=False)


def test_environment_reward_is_an_explicit_state_metric_not_a_public_parameter():
    with pytest.raises(TypeError):
        t.Environment(
            "not-implemented",
            graph(lambda state: {}),
            ({"value": 1},),
            reward=lambda result: 1,
        )
    from examples.checked_composition.example import run

    report = run()
    assert report["episode"].data["summary"]["state"]["total_reward"] == 2
    assert report["evaluation"].data["passed"] == 2
    assert len(report["memory"]) == 3


def test_openai_typed_tool_preserves_raw_input_validation_before_effects():
    import asyncio
    from agentic_systems._engine.integrations.adapters.openai_agents import (
        _sdk_contract_tool,
    )
    from agentic_systems._engine.integrations.adapters.tools import _TOOL_RESULT_MARKER

    class Quantity(pydantic.BaseModel):
        model_config = pydantic.ConfigDict(strict=True, extra="forbid")
        value: int = pydantic.Field(gt=0)

    called = []

    @t.tool(input_schema=Quantity, output_schema=Quantity)
    def increment(request: Quantity) -> Quantity:
        called.append(request.value)
        return Quantity(value=request.value + 1)

    native = _sdk_contract_tool(increment._to_engine(), "increment")
    assert set(native.params_json_schema["properties"]) == {"value"}
    for raw in (
        '{"value":"4"}',
        '{"value":0}',
        "{}",
        '{"value":4,"extra":true}',
        "not json",
    ):
        output = asyncio.run(native.on_invoke_tool(None, raw))
        if isinstance(output, str):
            output = json.loads(output)
        assert output[_TOOL_RESULT_MARKER]["ok"] is False
    assert called == []
    output = asyncio.run(native.on_invoke_tool(None, '{"value":4}'))
    assert output == {"value": 5} and called == [4]
