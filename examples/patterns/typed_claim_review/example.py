"""Current API adaptation; see README for its measured scope."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    text: Any | None = None
    source: Any | None = None
    has_source: Any | None = None


class Claim(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    text: str
    source: str


@toolkit.tool(input_schema=Claim)
def inspect_claim(text: str, source: str) -> dict:
    return {"text": text, "source": source, "has_source": bool(source)}


class Output1(pydantic.BaseModel):
    text: Any
    source: Any
    has_source: Any


graph_1 = toolkit.Graph(State, output_schema=Output1)
graph_1.add_node("inspect", inspect_claim)
graph_1.add_edge(toolkit.START, "inspect")
graph_1.add_edge("inspect", toolkit.END)
app = toolkit.Agent("typed_review", graph=graph_1)


def run():
    result = app.run({"text": "Revenue rose", "source": "report"})
    invalid = app.run({"text": 12, "source": "report"})
    assert result.ok and (not invalid.ok)
    return {
        "valid": result.to_dict(),
        "invalid": invalid.to_dict(),
        "scope": "types and source presence; not natural-language entailment",
    }
