"""Pydantic states retain validation through the common orchestration engine."""

import asyncio
import json
from typing import Annotated
import operator

import pydantic
import pytest
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    value: int
    left: int | None = None
    right: int | None = None


def graph(node):
    builder = toolkit.Graph(State)
    builder.add_node("work", node)
    builder.add_edge(toolkit.START, "work")
    builder.add_edge("work", toolkit.END)
    return builder


@pytest.mark.parametrize("owner", (toolkit.Agent, toolkit.System))
def test_model_input_nodes_updates_and_human_results(owner):
    def increase(state: State):
        assert isinstance(state, State)
        return {"value": state.value + 1}

    unit = owner("counter", graph=graph(increase))
    for raw in ({"value": 2}, State(value=2)):
        result = unit.run(raw)
        assert result.ok and result.data["value"] == 3
        assert result.check_invariants().ok
        text = result.human_results()
        assert all(word in text for word in ("Input:", "Process", "Output:", "COMPLETED"))
        assert result.execution_id in text
        json.dumps(result.to_dict(), allow_nan=False)


def test_bad_input_prevents_side_effects_and_bad_update_fails():
    seen = []
    app = toolkit.Agent("strict", graph=graph(lambda state: seen.append(state) or {"value": 1}))
    result = app.run({"value": "not-an-integer"})
    assert not result.ok and not seen and "ValidationError" in str(result.errors)
    bad = toolkit.Agent("bad-output", graph=graph(lambda state: {"value": "wrong"})).run({"value": 1})
    assert not bad.ok and bad.children and bad.check_invariants().ok


def test_validators_survive_compilation_and_decisions_receive_models():
    class Positive(pydantic.BaseModel):
        value: int

        @pydantic.field_validator("value")
        @classmethod
        def positive(cls, value):
            if value < 0:
                raise ValueError("must be positive")
            return value

    builder = toolkit.Graph(Positive)
    builder.add_node("work", lambda state: {"value": state.value + 1})
    builder.add_node("end", lambda state: {})
    builder.add_edge(toolkit.START, "work")
    builder.add_conditional_edges("work", lambda state: "end" if state.value > 0 else toolkit.END)
    builder.add_edge("end", toolkit.END)
    unit = toolkit.System("checked", graph=builder)
    assert unit.run({"value": 0}).data == {"value": 1}
    assert not unit.run({"value": -1}).ok


def test_nested_units_tools_context_environment_eval_and_pause():
    class Domain(pydantic.BaseModel):
        amount: int

    @toolkit.tool
    def add(value: int, *, context: toolkit.Context) -> dict:
        return {"value": value + context.data["amount"]}

    capability = toolkit.skill(name="addition", tools=(add,))
    memory = toolkit.Memory(capacity=2)
    agent = toolkit.Agent("operator", graph=graph(add), skills=(capability,), context=toolkit.Context(Domain(amount=2)), memory=memory)
    system = toolkit.System("team", graph=graph(agent))
    assert system.run(State(value=1)).data["value"] == 3
    environment = toolkit.Environment("episode", graph=graph(system), records=({"value": 1}, {"value": 2}))
    assert environment.run().ok
    evaluation = toolkit.Eval("check", unit=system, cases=({"input": {"value": 1}, "expected": {"data": {"value": 3}}},))
    assert evaluation.run().ok
    assert memory.read()

    def approval(state: State):
        approved = toolkit.pause({"value": state.value})
        return {"value": state.value + int(approved)}

    program = toolkit.Agent("approval", graph=graph(approval)).compile()
    paused = program.run(State(value=3))
    assert paused.status == "paused" and "PAUSED" in paused.human_results()
    resumed = program.resume(paused, True)
    assert resumed.ok and resumed.data["value"] == 4


def test_parallel_reducers_async_and_output_schema():
    class Parallel(pydantic.BaseModel):
        values: Annotated[list[int], operator.add] = pydantic.Field(default_factory=list)

    builder = toolkit.Graph(Parallel)
    builder.add_node("left", lambda state: {"values": [1]})
    builder.add_node("right", lambda state: {"values": [2]})
    builder.add_edge(toolkit.START, "left")
    builder.add_edge(toolkit.START, "right")
    builder.add_edge(["left", "right"], toolkit.END)
    result = asyncio.run(toolkit.System("parallel", graph=builder).arun({}))
    assert result.ok and sorted(result.data["values"]) == [1, 2]

    class Output(pydantic.BaseModel):
        value: int

    filtered = toolkit.Graph(State, output_schema=Output)
    filtered.add_node("work", lambda state: {"value": state.value + 1, "left": 50})
    filtered.add_edge(toolkit.START, "work")
    filtered.add_edge("work", toolkit.END)
    assert toolkit.Agent("output", graph=filtered).run({"value": 1}).data == {"value": 2}


def test_human_results_is_bounded_redacted_and_preserves_failure():
    result = toolkit.RunResult(ok=False, errors=({"code": "bad", "message": "failed"},), data={"api_key": "DO_NOT_SHOW", "long": "x" * 10000}, meta={"input": {"password": "DO_NOT_SHOW"}})
    rendered = result.human_results(max_chars=256)
    assert len(rendered) <= 256 and "FAILED" in rendered and "DO_NOT_SHOW" not in rendered
    with pytest.raises(ValueError):
        result.human_results(max_steps=0)
    with pytest.raises(ValueError):
        result.human_results(max_chars=10)


def test_reexports_are_original_langgraph_objects():
    from langgraph.graph import StateGraph, START, END
    from langgraph.types import Command, Send

    assert (toolkit.Graph, toolkit.START, toolkit.END, toolkit.Command, toolkit.Send) == (StateGraph, START, END, Command, Send)


def test_dynamic_send_and_worker_input_model():
    class Batch(pydantic.BaseModel):
        values: list[int]
        totals: Annotated[list[int], operator.add] = pydantic.Field(default_factory=list)

    class Item(pydantic.BaseModel):
        value: int

    def worker(state: Item):
        return {"totals": [state.value * 2]}

    builder = toolkit.Graph(Batch)
    builder.add_node("worker", worker)
    builder.add_conditional_edges(toolkit.START, lambda state: [toolkit.Send("worker", Item(value=n)) for n in state.values])
    builder.add_edge("worker", toolkit.END)
    result = toolkit.System("map", graph=builder).run({"values": [2, 3]})
    assert result.ok and sorted(result.data["totals"]) == [4, 6], result.errors


def test_async_node_model_update_and_nonfinite_rejection():
    async def increase(state: State):
        return State(value=state.value + 1)

    result = asyncio.run(toolkit.Agent("async", graph=graph(increase)).arun({"value": 1}))
    assert result.ok and result.data["value"] == 2

    class Numeric(pydantic.BaseModel):
        value: float

    with pytest.raises(TypeError):
        toolkit.Context(Numeric(value=float("nan")))


def test_explicit_null_is_not_replaced_by_an_unset_default_between_units():
    class OptionalState(pydantic.BaseModel):
        value: int
        amount: int | None = None

    seen = []
    def inspect(state: OptionalState):
        seen.append(state.model_fields_set)
        return {"value": state.value}

    inner = toolkit.Graph(OptionalState)
    inner.add_node("inspect", inspect)
    inner.add_edge(toolkit.START, "inspect")
    inner.add_edge("inspect", toolkit.END)
    agent = toolkit.Agent("inner", graph=inner)
    outer = toolkit.Graph(OptionalState)
    outer.add_node("inner", agent)
    outer.add_edge(toolkit.START, "inner")
    outer.add_edge("inner", toolkit.END)
    system = toolkit.System("outer", graph=outer)
    assert system.run({"value": 1}).ok
    assert system.run({"value": 1, "amount": None}).ok
    assert "amount" not in seen[0] and "amount" in seen[1]


def test_studio_recognizes_pydantic_first_import_for_static_safety():
    from agentic_systems_studio.presentation import validate_generated_agentic_systems_code

    with pytest.raises(ValueError):
        validate_generated_agentic_systems_code("import pydantic\nimport agentic_systems as toolkit\neval('1+1')", allow_code=True)


def test_tool_can_validate_and_return_a_pydantic_output_model():
    class Receipt(pydantic.BaseModel):
        total: int = pydantic.Field(ge=0)
        currency: str = "MXN"

    @toolkit.tool(output_schema=Receipt)
    def price(quantity: int, unit_price: int) -> Receipt:
        return Receipt(total=quantity * unit_price)

    result = price.run({"quantity": 2, "unit_price": 10})
    assert result.ok and result.data == {"total": 20, "currency": "MXN"}
    assert result.check_invariants().ok
    assert not price.run({"quantity": -1, "unit_price": 10}).ok
