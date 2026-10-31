"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Payload(Closed):
    message: str


@toolkit.tool
def classify_ticket(message: str) -> dict:
    input = Payload(message=message).model_dump(mode="python")
    text = input["message"].lower()
    category = (
        "refund"
        if "refund" in text
        else "shipping"
        if "delivery" in text
        else "general"
    )
    return {
        "category": category,
        "owner": {"refund": "billing", "shipping": "logistics", "general": "support"}[
            category
        ],
    }


capability = toolkit.skill(name="classify_ticket", tools=(classify_ticket,))


class WorkState(pydantic.BaseModel):
    input: dict
    category: Any | None = None
    owner: Any | None = None


class Output(pydantic.BaseModel):
    category: Any
    owner: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def classify_ticket_step(state):
    return classify_ticket.run(state.input)
graph.add_node(
    "classify_ticket",
    classify_ticket_step,
)
graph.add_edge(toolkit.START, "classify_ticket")
graph.add_edge("classify_ticket", toolkit.END)
app = toolkit.Agent("classify_ticket", graph=graph, skills=(capability,))
sample = {"message": "Please refund order A17"}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {"category": "refund", "owner": "billing"}, (
        result.to_dict()
    )
    return result
