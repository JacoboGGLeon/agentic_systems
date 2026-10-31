"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Payload(Closed):
    source: str


@toolkit.tool
def inspect_source(source: str) -> dict:
    input = Payload(source=source).model_dump(mode="python")
    import ast

    tree = ast.parse(input["source"])
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    return {
        "syntax_ok": True,
        "functions": len(functions),
        "missing_return_annotations": [
            node.name for node in functions if node.returns is None
        ],
    }


capability = toolkit.skill(name="inspect_source", tools=(inspect_source,))


class WorkState(pydantic.BaseModel):
    input: dict
    syntax_ok: Any | None = None
    functions: Any | None = None
    missing_return_annotations: Any | None = None


class Output(pydantic.BaseModel):
    syntax_ok: Any
    functions: Any
    missing_return_annotations: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def inspect_source_step(state):
    return inspect_source.run(state.input)
graph.add_node(
    "inspect_source",
    inspect_source_step,
)
graph.add_edge(toolkit.START, "inspect_source")
graph.add_edge("inspect_source", toolkit.END)
app = toolkit.Agent("inspect_source", graph=graph, skills=(capability,))
sample = {"source": "def total(values):\n    return sum(values)\n"}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {
        "syntax_ok": True,
        "functions": 1,
        "missing_return_annotations": ["total"],
    }, result.to_dict()
    return result
