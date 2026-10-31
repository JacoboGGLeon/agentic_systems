import pydantic
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    balance: int | None = None
    amount: int | None = None


class Output(pydantic.BaseModel):
    balance: int


graph = toolkit.Graph(State, output_schema=Output)
def sum_step(state):
    return {"balance": state.balance + state.amount}
graph.add_node("sum", sum_step)
graph.add_edge(toolkit.START, "sum")
graph.add_edge("sum", toolkit.END)
episode = toolkit.Environment(
    "ledger",
    graph=graph,
    records=tuple(({"amount": 1} for _ in range(30))),
    state={"balance": 0},
    observe=lambda row, state: {**row, **state},
    update=lambda state, row, result: result.data,
)


def run():
    first = episode.run(timeout_s=None)
    second = episode.run(timeout_s=None)
    assert (
        first.ok
        and second.ok
        and (
            first.data["summary"]["state"]
            == second.data["summary"]["state"]
            == {"balance": 30}
        )
    )
    assert first.execution_id != second.execution_id
    return first
