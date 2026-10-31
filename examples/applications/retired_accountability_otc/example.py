"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Claim(Closed):
    id: str
    owner: str
    evidence: list[str]


class Payload(Closed):
    claims: list[Claim]


@toolkit.tool
def evidence_accountability(claims: list[Claim]) -> dict:
    input = Payload(claims=claims).model_dump(mode="python")
    claims = input["claims"]
    return {
        "unowned": [claim["id"] for claim in claims if not claim["owner"]],
        "unsupported": [claim["id"] for claim in claims if not claim["evidence"]],
        "data": "public synthetic fixture",
    }


capability = toolkit.skill(
    name="evidence_accountability", tools=(evidence_accountability,)
)


class WorkState(pydantic.BaseModel):
    input: dict
    unowned: Any | None = None
    unsupported: Any | None = None
    data: Any | None = None


class Output(pydantic.BaseModel):
    unowned: Any
    unsupported: Any
    data: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def evidence_accountability_step(state):
    return evidence_accountability.run(state.input)
graph.add_node(
    "evidence_accountability",
    evidence_accountability_step,
)
graph.add_edge(toolkit.START, "evidence_accountability")
graph.add_edge("evidence_accountability", toolkit.END)
app = toolkit.Agent("evidence_accountability", graph=graph, skills=(capability,))
sample = {
    "claims": [
        {"id": "C1", "owner": "team-A", "evidence": ["E1"]},
        {"id": "C2", "owner": "", "evidence": []},
    ]
}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {
        "unowned": ["C2"],
        "unsupported": ["C2"],
        "data": "public synthetic fixture",
    }, result.to_dict()
    return result
