"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Payload(Closed):
    text: str


@toolkit.tool
def text_counts(text: str) -> dict:
    input = Payload(text=text).model_dump(mode="python")
    words = input["text"].lower().split()
    return {
        "words": len(words),
        "unique": len(set(words)),
        "mentions": words.count("evidence"),
    }


capability = toolkit.skill(name="text_counts", tools=(text_counts,))


class WorkState(pydantic.BaseModel):
    input: dict
    words: Any | None = None
    unique: Any | None = None
    mentions: Any | None = None


class Output(pydantic.BaseModel):
    words: Any
    unique: Any
    mentions: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def text_counts_step(state):
    return text_counts.run(state.input)
graph.add_node(
    "text_counts",
    text_counts_step,
)
graph.add_edge(toolkit.START, "text_counts")
graph.add_edge("text_counts", toolkit.END)
app = toolkit.Agent("text_counts", graph=graph, skills=(capability,))
sample = {"text": "evidence supports evidence"}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {"words": 3, "unique": 2, "mentions": 2}, (
        result.to_dict()
    )
    return result
