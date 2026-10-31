"""Current API adaptation; see README for its measured scope."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    answer: Any | None = None


graph_1 = toolkit.Graph(State, output_schema=State)
def read_step(data):
    return data
graph_1.add_node("read", read_step)
graph_1.add_edge(toolkit.START, "read")
graph_1.add_edge("read", toolkit.END)
app = toolkit.Agent("saved_answer", graph=graph_1)
evaluation = toolkit.Eval(
    "literal_gate",
    app,
    cases=tuple(
        (
            {"input": {"answer": answer}, "expected": {"data": {"answer": "VALID"}}}
            for answer in ("VALID", "VALID.", "invalid", "")
        )
    ),
)


def run():
    runs = [
        toolkit.Eval("literal_gate", app, cases=(case,)).run()
        for case in evaluation.cases
    ]
    decisions = [result.ok for result in runs]
    assert decisions == [True, False, False, False]
    return {
        "decisions": decisions,
        "scope": "literal saved-answer gate; no entailment claim",
        "evaluations": [r.to_dict() for r in runs],
    }
