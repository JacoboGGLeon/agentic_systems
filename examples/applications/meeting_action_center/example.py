"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Payload(Closed):
    notes: list[str]


@toolkit.tool
def extract_actions(notes: list[str]) -> dict:
    input = Payload(notes=notes).model_dump(mode="python")
    actions = []
    for line in input["notes"]:
        owner, task, due = line.split(" | ")
        actions.append({"owner": owner, "task": task, "due": due})
    return {"actions": actions}


capability = toolkit.skill(name="extract_actions", tools=(extract_actions,))


class WorkState(pydantic.BaseModel):
    input: dict
    actions: Any | None = None


class Output(pydantic.BaseModel):
    actions: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def extract_actions_step(state):
    return extract_actions.run(state.input)
graph.add_node(
    "extract_actions",
    extract_actions_step,
)
graph.add_edge(toolkit.START, "extract_actions")
graph.add_edge("extract_actions", toolkit.END)
app = toolkit.Agent("extract_actions", graph=graph, skills=(capability,))
sample = {"notes": ["Ana | Review budget | Friday"]}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {
        "actions": [{"owner": "Ana", "task": "Review budget", "due": "Friday"}]
    }, result.to_dict()
    return result
