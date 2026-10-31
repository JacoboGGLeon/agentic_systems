"""Current API adaptation; see README for its measured scope."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    messages: Any | None = None
    history: Any | None = None


@toolkit.tool
def bound_history(messages: list[str]) -> dict:
    return {"history": [message[:80] for message in messages[-3:]]}


class Output1(pydantic.BaseModel):
    history: Any


graph_1 = toolkit.Graph(State, output_schema=Output1)
graph_1.add_node("bound", bound_history)
graph_1.add_edge(toolkit.START, "bound")
graph_1.add_edge("bound", toolkit.END)
app = toolkit.Agent("memory", graph=graph_1)


def run():
    result = app.run({"messages": ["old", "first", "second", "current"]})
    assert result.ok and result.data == {"history": ["first", "second", "current"]}
    return result
