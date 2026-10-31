"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Row(Closed):
    revenue: str
    cost: str


class Payload(Closed):
    rows: list[Row]


@toolkit.tool
def profit(rows: list[Row]) -> dict:
    input = Payload(rows=rows).model_dump(mode="python")
    from decimal import Decimal

    revenue = sum((Decimal(row["revenue"]) for row in input["rows"]))
    cost = sum((Decimal(row["cost"]) for row in input["rows"]))
    return {"revenue": str(revenue), "cost": str(cost), "profit": str(revenue - cost)}


capability = toolkit.skill(name="profit", tools=(profit,))


class WorkState(pydantic.BaseModel):
    input: dict
    revenue: Any | None = None
    cost: Any | None = None
    profit: Any | None = None


class Output(pydantic.BaseModel):
    revenue: Any
    cost: Any
    profit: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def profit_step(state):
    return profit.run(state.input)
graph.add_node(
    "profit", profit_step
)
graph.add_edge(toolkit.START, "profit")
graph.add_edge("profit", toolkit.END)
app = toolkit.Agent("profit", graph=graph, skills=(capability,))
sample = {
    "rows": [
        {"revenue": "100.10", "cost": "60.05"},
        {"revenue": "20.20", "cost": "10.00"},
    ]
}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {
        "revenue": "120.30",
        "cost": "70.05",
        "profit": "50.25",
    }, result.to_dict()
    return result
