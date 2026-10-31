import pydantic
from typing import Any
import json
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    value: Any


def run():

    class Output1(pydantic.BaseModel):
        value: Any

    graph_1 = toolkit.Graph(State, output_schema=Output1)
    def increment_step(d):
        return {"value": d.value + 1}
    graph_1.add_node("increment", increment_step)
    graph_1.add_edge(toolkit.START, "increment")
    graph_1.add_edge("increment", toolkit.END)
    result = toolkit.Agent("incrementer", graph=graph_1).run({"value": 3})
    payload = json.loads(json.dumps(result.to_dict()))
    restored = toolkit.RunResult(**payload)
    assert restored.to_dict() == payload and restored.check_invariants().ok
    memory = restored.lineage(
        name="increment",
        question="What happened?",
        goal="Explain execution",
        tags=["offline"],
        metadata={"fixture": True},
        max_tool_rows=2,
    )
    assert memory.to_dict()["steps"] and memory.explain()["ok"]
    return {
        "input": {"value": 3},
        "process": restored.trace(),
        "output": payload,
        "lineage": memory.to_dict(),
        "prompt_context": memory.to_prompt_context(max_chars=500),
    }
