"""Current API adaptation; see README for its measured scope."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    answer: Any | None = None
    input: Any
    expected: Any | None = None
    result: Any | None = None
    rubric: Any | None = None
    criteria: Any | None = None
    findings: Any | None = None
    rationale: Any | None = None


class Output1(pydantic.BaseModel):
    answer: Any


graph_1 = toolkit.Graph(State, output_schema=Output1)
def exact_step(data):
    return {"answer": data.answer}
graph_1.add_node("exact", exact_step)
graph_1.add_edge(toolkit.START, "exact")
graph_1.add_edge("exact", toolkit.END)
app = toolkit.Agent("candidate", graph=graph_1)


class Output2(pydantic.BaseModel):
    criteria: Any
    findings: Any
    rationale: Any


graph_2 = toolkit.Graph(State, output_schema=Output2)
def score_step(data):
    return {
            "criteria": {"correctness": 1.0},
            "findings": [],
            "rationale": "Intentionally optimistic fixture",
        }
graph_2.add_node(
    "score",
    score_step,
)
graph_2.add_edge(toolkit.START, "score")
graph_2.add_edge("score", toolkit.END)
fixture_judge = toolkit.Agent("judge_fixture", graph=graph_2)
evaluation = toolkit.Eval(
    "negative_control",
    app,
    cases=({"input": {"answer": "WRONG"}, "expected": {"data": {"answer": "VALID"}}},),
    judge=fixture_judge,
    rubric={"criteria": ["correctness"], "threshold": 0.9},
)


def run():
    result = evaluation.run()
    assert not result.ok
    return {
        "evaluation": result.to_dict(),
        "scope": "optimistic judge cannot overrule a failed exact expectation; fixture, not live judge",
    }
