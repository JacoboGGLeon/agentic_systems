"""Episode state and episodic Memory are separate concepts."""

import pydantic
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    amount: int | None = None
    previous: int | None = None
    total: int | None = None


class Output(pydantic.BaseModel):
    total: int


def build():
    graph = toolkit.Graph(State, output_schema=Output)
    def sum_step(state):
        return {"total": state.previous + state.amount}
    graph.add_node("sum", sum_step)
    graph.add_edge(toolkit.START, "sum")
    graph.add_edge("sum", toolkit.END)
    return toolkit.Environment(
        "ledger",
        graph=graph,
        records=({"amount": 2}, {"amount": 3}, {"amount": 100}),
        state={"total": 0},
        memory=toolkit.Memory(capacity=3),
        observe=lambda row, state: {
            "amount": row["amount"],
            "previous": state["total"],
        },
        update=lambda state, row, result: result.data,
        stop=lambda state, result: state["total"] >= 5,
    )


def run():
    episode = build()
    result = episode.run()
    replay = episode.run()
    assert result.ok and result.data["outputs"] == [{"total": 2}, {"total": 5}]
    assert result.data["summary"]["state"] == {"total": 5}
    assert (
        replay.data["outputs"] == result.data["outputs"]
        and replay.data["summary"] == result.data["summary"]
    )
    assert replay.execution_id != result.execution_id
    return {
        "input": [{"amount": 2}, {"amount": 3}, {"amount": 100}],
        "process": "state 0 to 2 to 5; stop before 100",
        "output": result.to_dict(),
        "memory": episode.memory.read(),
    }
