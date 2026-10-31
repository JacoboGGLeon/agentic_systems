import pydantic
from typing import Any
from pathlib import Path
import agentic_systems as toolkit


class State(pydantic.BaseModel):
    value: Any


def run():
    capability = toolkit.load_skill(Path(__file__).parent / "assets/arithmetic")
    graph_1 = toolkit.Graph(State, output_schema=State)
    graph_1.add_node("increment", capability.tools[0])
    graph_1.add_edge(toolkit.START, "increment")
    graph_1.add_edge("increment", toolkit.END)
    worker = toolkit.Agent("portable", graph=graph_1, skills=(capability,))
    result = worker.run({"value": 3})
    assert result.ok and result.data == {"value": 4}
    return {
        "input": {"value": 3},
        "process": capability.inspect(),
        "output": result.to_dict(),
    }
