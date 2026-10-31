"""Current API adaptation; see README for its measured scope."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    item: Any | None = None


@toolkit.tool
def unavailable(item: str) -> dict:
    raise LookupError("Inventory unavailable for " + item)


graph_1 = toolkit.Graph(State, output_schema=State)
graph_1.add_node("lookup", unavailable)
graph_1.add_edge(toolkit.START, "lookup")
graph_1.add_edge("lookup", toolkit.END)
graph_2 = toolkit.Graph(State)
graph_2.add_node("step_0", toolkit.Agent("inventory", graph=graph_1))
graph_2.add_edge(toolkit.START, "step_0")
graph_2.add_edge("step_0", toolkit.END)
app = toolkit.System("failure", graph=graph_2)


def run():
    result = app.run({"item": "A17"})
    assert (
        not result.ok
        and result.errors
        and any((node.tool_events for node in result.walk()))
    )
    assert result.check_invariants().ok
    return result
