"""Six Agent/System forms, expressed only with LangGraph."""

import pydantic
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    value: int
    left: int | None = None
    right: int | None = None


class Output(pydantic.BaseModel):
    value: int


@toolkit.tool
def increment(value: int) -> dict:
    return {"value": value + 1}


@toolkit.tool
def double(value: int) -> dict:
    return {"value": value * 2}


@toolkit.tool
def left(value: int) -> dict:
    return {"left": value + 1}


@toolkit.tool
def right(value: int) -> dict:
    return {"right": value * 2}


arithmetic = toolkit.skill(name="arithmetic", tools=(increment, double, left, right))


def build():
    increase_graph = toolkit.Graph(State)
    increase_graph.add_node("increment", increment)
    increase_graph.add_edge(toolkit.START, "increment")
    increase_graph.add_edge("increment", toolkit.END)
    increaser = toolkit.Agent("increaser", graph=increase_graph, skills=(arithmetic,))
    double_graph = toolkit.Graph(State)
    double_graph.add_node("double", double)
    double_graph.add_edge(toolkit.START, "double")
    double_graph.add_edge("double", toolkit.END)
    doubler = toolkit.Agent("doubler", graph=double_graph, skills=(arithmetic,))
    left_graph = toolkit.Graph(State)
    left_graph.add_node("left", left)
    left_graph.add_edge(toolkit.START, "left")
    left_graph.add_edge("left", toolkit.END)
    left_agent = toolkit.Agent("left", graph=left_graph)
    right_graph = toolkit.Graph(State)
    right_graph.add_node("right", right)
    right_graph.add_edge(toolkit.START, "right")
    right_graph.add_edge("right", toolkit.END)
    right_agent = toolkit.Agent("right", graph=right_graph)
    units = []
    for owner, first, second, a, b in (
        (toolkit.Agent, increment, double, left, right),
        (toolkit.System, increaser, doubler, left_agent, right_agent),
    ):
        sequence = toolkit.Graph(State, output_schema=Output)
        sequence.add_node("increase", first)
        sequence.add_node("double", second)
        sequence.add_edge(toolkit.START, "increase")
        sequence.add_edge("increase", "double")
        sequence.add_edge("double", toolkit.END)
        units.append(owner(owner.__name__ + "_sequence", graph=sequence))
        parallel = toolkit.Graph(State, output_schema=Output)
        parallel.add_node("left", a)
        parallel.add_node("right", b)
        def total_step(state):
            return {"value": state.left + state.right}
        parallel.add_node("total", total_step)
        parallel.add_edge(toolkit.START, "left")
        parallel.add_edge(toolkit.START, "right")
        parallel.add_edge(["left", "right"], "total")
        parallel.add_edge("total", toolkit.END)
        units.append(owner(owner.__name__ + "_parallel", graph=parallel))
        decision = toolkit.Graph(State, output_schema=Output)
        decision.add_node("increase", first)
        decision.add_node("double", second)
        decision.add_edge(toolkit.START, "increase")
        decision.add_conditional_edges(
            "increase",
            lambda state: "double" if state.value >= 0 else toolkit.END,
            ["double", toolkit.END],
        )
        decision.add_edge("double", toolkit.END)
        units.append(owner(owner.__name__ + "_decision", graph=decision))
    return tuple(units)


def run():
    rows = []
    for unit, expected in zip(build(), (8, 10, 8, 8, 10, 8)):
        result = unit.run({"value": 3})
        assert result.ok and result.data == {"value": expected}
        assert unit.compile().run({"value": 3}).data == result.data
        assert result.check_invariants().ok
        if unit.name.endswith("decision"):
            assert unit.run({"value": -3}).data == {"value": -2}
        rows.append({"unit": unit.name, "result": result.to_dict()})
    return {
        "input": {"value": 3},
        "process": "Agent/System with sequence, branches and decisions; LangGraph only",
        "output": rows,
    }
