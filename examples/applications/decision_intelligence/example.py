"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Option(Closed):
    name: str
    quality: int
    cost: int


class Payload(Closed):
    options: list[Option]


@toolkit.tool
def rank_options(options: list[Option]) -> dict:
    input = Payload(options=options).model_dump(mode="python")
    scores = {row["name"]: row["quality"] - row["cost"] for row in input["options"]}
    return {"scores": scores, "selected": max(scores, key=scores.get)}


capability = toolkit.skill(name="rank_options", tools=(rank_options,))


class WorkState(pydantic.BaseModel):
    input: dict
    scores: Any | None = None
    selected: Any | None = None


class Output(pydantic.BaseModel):
    scores: Any
    selected: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def rank_options_step(state):
    return rank_options.run(state.input)
graph.add_node(
    "rank_options",
    rank_options_step,
)
graph.add_edge(toolkit.START, "rank_options")
graph.add_edge("rank_options", toolkit.END)
app = toolkit.Agent("rank_options", graph=graph, skills=(capability,))
sample = {
    "options": [
        {"name": "A", "quality": 9, "cost": 7},
        {"name": "B", "quality": 8, "cost": 3},
    ]
}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {"scores": {"A": 2, "B": 5}, "selected": "B"}, (
        result.to_dict()
    )
    return result
