"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Payload(Closed):
    operation: str


@toolkit.tool
def scope(operation: str) -> dict:
    input = Payload(operation=operation).model_dump(mode="python")
    supported = {"sum", "count"}
    return {
        "accepted": input["operation"] in supported,
        "supported": sorted(supported),
        "reason": "outside declared capabilities"
        if input["operation"] not in supported
        else "declared operation",
    }


capability = toolkit.skill(name="scope", tools=(scope,))


class WorkState(pydantic.BaseModel):
    input: dict
    accepted: Any | None = None
    supported: Any | None = None
    reason: Any | None = None


class Output(pydantic.BaseModel):
    accepted: Any
    supported: Any
    reason: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def scope_step(state):
    return scope.run(state.input)
graph.add_node("scope", scope_step)
graph.add_edge(toolkit.START, "scope")
graph.add_edge("scope", toolkit.END)
app = toolkit.Agent("scope", graph=graph, skills=(capability,))
sample = {"operation": "transfer_money"}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {
        "accepted": False,
        "supported": ["count", "sum"],
        "reason": "outside declared capabilities",
    }, result.to_dict()
    return result
