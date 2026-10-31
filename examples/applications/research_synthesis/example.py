"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Claim(Closed):
    text: str
    source: str


class Payload(Closed):
    claims: list[Claim]
    sources: list[str]


@toolkit.tool
def extract_sources(claims: list[Claim], sources: list[str]) -> dict:
    input = Payload(claims=claims, sources=sources).model_dump(mode="python")
    claims = input["claims"]
    sources = input["sources"]
    return {
        "supported": [c["text"] for c in claims if c["source"] in sources],
        "unverified": [c["text"] for c in claims if c["source"] not in sources],
    }


capability = toolkit.skill(name="extract_sources", tools=(extract_sources,))


class WorkState(pydantic.BaseModel):
    input: dict
    supported: Any | None = None
    unverified: Any | None = None


class Output(pydantic.BaseModel):
    supported: Any
    unverified: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def extract_sources_step(state):
    return extract_sources.run(state.input)
graph.add_node(
    "extract_sources",
    extract_sources_step,
)
graph.add_edge(toolkit.START, "extract_sources")
graph.add_edge("extract_sources", toolkit.END)
app = toolkit.Agent("extract_sources", graph=graph, skills=(capability,))
sample = {
    "claims": [
        {"text": "Revenue grew 5%", "source": "report"},
        {"text": "It will double", "source": "unknown"},
    ],
    "sources": ["report"],
}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {
        "supported": ["Revenue grew 5%"],
        "unverified": ["It will double"],
    }, result.to_dict()
    return result
