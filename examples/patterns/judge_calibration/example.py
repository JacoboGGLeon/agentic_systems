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


class Candidate(pydantic.BaseModel):
    answer: str


graph_1 = toolkit.Graph(Candidate, output_schema=Candidate)
def answer_step(data):
    return data
graph_1.add_node("answer", answer_step)
graph_1.add_edge(toolkit.START, "answer")
graph_1.add_edge("answer", toolkit.END)
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
            "rationale": "Calibration fixture always approves",
        }
graph_2.add_node(
    "score",
    score_step,
)
graph_2.add_edge(toolkit.START, "score")
graph_2.add_edge("score", toolkit.END)
judge = toolkit.Agent("optimistic_fixture", graph=graph_2)
evaluation = toolkit.Eval(
    "calibration",
    app,
    cases=(
        {"input": {"answer": "VALID"}, "expected": {"data": {"answer": "VALID"}}},
        {"input": {"answer": "WRONG"}, "expected": {"data": {"answer": "VALID"}}},
    ),
    judge=judge,
    rubric={"criteria": ["correctness"], "threshold": 0.9},
)


def run():
    result = evaluation.run()
    decisions = [case["ok"] for case in result.data["cases"]]
    assert decisions == [True, False]
    return {
        "calibration": decisions,
        "false_approvals": 0,
        "scope": "fixture protocol; no empirical model judge calibration",
        "evaluation": result.to_dict(),
    }
