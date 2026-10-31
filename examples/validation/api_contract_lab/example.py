"""Current API adaptation; see README for its measured scope."""

import pydantic
from typing import Any
import agentic_systems as toolkit
from inspect import signature


class State(pydantic.BaseModel):
    value: Any


def run():
    graph_1 = toolkit.Graph(State, output_schema=State)
    def identity_step(data):
        return data
    graph_1.add_node("identity", identity_step)
    graph_1.add_edge(toolkit.START, "identity")
    graph_1.add_edge("identity", toolkit.END)
    worker = toolkit.Agent("identity", graph=graph_1)
    direct = worker.run({"value": 3})
    prepared = worker.compile().run({"value": 3})
    assert direct.ok and prepared.ok and (direct.data == prepared.data)
    return {
        "version": toolkit.__version__,
        "exports": list(toolkit.__all__),
        "Agent": str(signature(toolkit.Agent)),
        "System": str(signature(toolkit.System)),
        "output": direct.data,
    }
