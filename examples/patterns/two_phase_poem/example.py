"""Current API adaptation; see README for its measured scope."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    quantity: Any | None = None
    unit_price: Any | None = None
    total: Any | None = None
    poem: Any | None = None


@toolkit.tool
def exact_total(quantity: int, unit_price: int) -> dict:
    return {"total": quantity * unit_price}


class Output1(pydantic.BaseModel):
    total: Any


graph_1 = toolkit.Graph(State, output_schema=Output1)
graph_1.add_node("total", exact_total)
graph_1.add_edge(toolkit.START, "total")
graph_1.add_edge("total", toolkit.END)
arithmetic = toolkit.Agent("evidence", graph=graph_1)


class Output2(pydantic.BaseModel):
    total: Any
    poem: Any


graph_2 = toolkit.Graph(State, output_schema=Output2)
def format_step(data):
    return {
            "total": data.total,
            "poem": f"Evidence counts {data.total}\nThe amount stays exact\nThis verse is a supplied fixture",
        }
graph_2.add_node(
    "format",
    format_step,
)
graph_2.add_edge(toolkit.START, "format")
graph_2.add_edge("format", toolkit.END)
compose = toolkit.Agent("saved_verse", graph=graph_2)
graph_3 = toolkit.Graph(State)
graph_3.add_node("step_0", arithmetic)
graph_3.add_edge(toolkit.START, "step_0")
graph_3.add_node("step_1", compose)
graph_3.add_edge("step_0", "step_1")
graph_3.add_edge("step_1", toolkit.END)
app = toolkit.System("two_phases", graph=graph_3)


def run():
    result = app.run({"quantity": 3, "unit_price": 116})
    assert (
        result.ok
        and result.data["total"] == 348
        and (len(result.data["poem"].splitlines()) == 3)
    )
    assert any(
        (
            event.name == "exact_total"
            for node in result.walk()
            for event in node.tool_events
        )
    )
    return {
        "result": result.to_dict(),
        "scope": "exact evidence then formatting fixture; no language-model generation",
    }
