"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Claim(Closed):
    id: str
    source: str
    causal: bool
    causal_evidence: list[str]


class Payload(Closed):
    claims: list[Claim]
    sources: list[str]


@toolkit.tool
def review_claims(claims: list[Claim], sources: list[str]) -> dict:
    input = Payload(claims=claims, sources=sources).model_dump(mode="python")
    findings = []
    for claim in input["claims"]:
        if claim["source"] not in input["sources"]:
            findings.append({"claim": claim["id"], "issue": "missing source"})
        if claim.get("causal") and (not claim.get("causal_evidence")):
            findings.append({"claim": claim["id"], "issue": "unsupported causality"})
    return {"accepted": not findings, "findings": findings}


capability = toolkit.skill(name="review_claims", tools=(review_claims,))


class WorkState(pydantic.BaseModel):
    input: dict
    accepted: Any | None = None
    findings: Any | None = None


class Output(pydantic.BaseModel):
    accepted: Any
    findings: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def review_claims_step(state):
    return review_claims.run(state.input)
graph.add_node(
    "review_claims",
    review_claims_step,
)
graph.add_edge(toolkit.START, "review_claims")
graph.add_edge("review_claims", toolkit.END)
app = toolkit.Agent("review_claims", graph=graph, skills=(capability,))
sample = {
    "claims": [
        {"id": "C1", "source": "missing", "causal": True, "causal_evidence": []}
    ],
    "sources": ["report"],
}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {
        "accepted": False,
        "findings": [
            {"claim": "C1", "issue": "missing source"},
            {"claim": "C1", "issue": "unsupported causality"},
        ],
    }, result.to_dict()
    return result
