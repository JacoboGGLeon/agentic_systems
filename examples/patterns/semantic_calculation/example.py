"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Line(Closed):
    quantity: int
    unit_price: int


class Payload(Closed):
    items: list[Line]


@toolkit.tool
def calculate_invoice(items: list[Line]) -> dict:
    input = Payload(items=items).model_dump(mode="python")
    total = sum((row["quantity"] * row["unit_price"] for row in input["items"]))
    return {"subtotal": total, "tax": total * 16 // 100, "total": total * 116 // 100}


capability = toolkit.skill(name="calculate_invoice", tools=(calculate_invoice,))


class WorkState(pydantic.BaseModel):
    input: dict
    subtotal: Any | None = None
    tax: Any | None = None
    total: Any | None = None


class Output(pydantic.BaseModel):
    subtotal: Any
    tax: Any
    total: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def calculate_invoice_step(state):
    return calculate_invoice.run(state.input)
graph.add_node(
    "calculate_invoice",
    calculate_invoice_step,
)
graph.add_edge(toolkit.START, "calculate_invoice")
graph.add_edge("calculate_invoice", toolkit.END)
app = toolkit.Agent("calculate_invoice", graph=graph, skills=(capability,))
sample = {"items": [{"quantity": 3, "unit_price": 100}]}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {"subtotal": 300, "tax": 48, "total": 348}, (
        result.to_dict()
    )
    return result
