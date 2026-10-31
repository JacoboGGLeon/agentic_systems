"""Current API adaptation; see README for its measured scope."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    values: Any | None = None
    total: Any | None = None


calls = []


def calculate(data):
    calls.append(data)
    return {"total": sum(data.values)}


class Output1(pydantic.BaseModel):
    total: Any


graph_1 = toolkit.Graph(State, output_schema=Output1)
graph_1.add_node("sum", calculate)
graph_1.add_edge(toolkit.START, "sum")
graph_1.add_edge("sum", toolkit.END)
candidate = toolkit.Agent("candidate", graph=graph_1)


def run():
    saved = candidate.run({"values": [2, 3]})
    before = len(calls)
    frozen = toolkit.RunResult(**saved.to_dict())
    graph_2 = toolkit.Graph(State, output_schema=State)
    def read_step(data):
        return frozen
    graph_2.add_node("read", read_step)
    graph_2.add_edge(toolkit.START, "read")
    graph_2.add_edge("read", toolkit.END)
    observer = toolkit.Agent("saved_execution", graph=graph_2)
    result = toolkit.Eval(
        "observe", observer, cases=({"input": {}, "expected": {"data": {"total": 5}}},)
    ).run()
    assert result.ok and len(calls) == before
    return {
        "original": saved.to_dict(),
        "evaluation": result.to_dict(),
        "candidate_reruns": 0,
        "compact_trace": frozen.trace(),
        "lineage": frozen.lineage().to_dict(),
    }
