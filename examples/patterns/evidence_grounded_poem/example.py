"""Current API adaptation; see README for its measured scope."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    poem: Any | None = None


sample = "Three items cost 300\nTax adds 48\nVerified total 348"


class Output1(pydantic.BaseModel):
    poem: Any


graph_1 = toolkit.Graph(State, output_schema=Output1)
def read_step(data):
    return {"poem": data.poem}
graph_1.add_node("read", read_step)
graph_1.add_edge(toolkit.START, "read")
graph_1.add_edge("read", toolkit.END)
app = toolkit.Agent("saved_candidate", graph=graph_1)
evaluation = toolkit.Eval(
    "poem_contract",
    app,
    cases=(
        {"input": {"poem": sample}, "expected": {"ok": True}},
        {"input": {"poem": "The moon computes forever"}, "expected": {"ok": True}},
    ),
    checks=(
        lambda result, case: {
            "ok": len(result.data["poem"].splitlines()) == 3
            and "348" in result.data["poem"],
            "issues": [],
        },
    ),
)


def run():
    result = evaluation.run()
    assert (
        not result.ok
        and result.data["cases"][0]["ok"]
        and (not result.data["cases"][1]["ok"])
    )
    return {
        "evaluation": result.to_dict(),
        "scope": "saved creative candidates; no generation or semantic judge inferred",
    }
