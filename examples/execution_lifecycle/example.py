import asyncio
import time
import agentic_systems as toolkit
import pydantic


class State(pydantic.BaseModel):
    value: int


@toolkit.tool
def increment(value: int) -> dict:
    return {"value": value + 1}


@toolkit.tool
def double(value: int) -> dict:
    return {"value": value * 2}


def run():
    graph = toolkit.Graph(State)
    graph.add_node("increase", increment)
    graph.add_node("double", double)
    def delay_step(state):
        return time.sleep(0.02) or {}
    graph.add_node("delay", delay_step)
    graph.add_edge(toolkit.START, "delay")
    graph.add_edge("delay", "increase")
    graph.add_edge("increase", "double")
    graph.add_edge("double", toolkit.END)
    unit = toolkit.Agent("lifecycle", graph=graph)
    prepared = unit.compile()
    direct = unit.run({"value": 3}, timeout_s=None)
    asynchronous = asyncio.run(prepared.arun({"value": 3}))
    limited = unit.run({"value": 3}, timeout_s=0.005)
    assert direct.ok and direct.data == asynchronous.data == {"value": 8}
    assert not limited.ok
    return {
        "input": {"value": 3},
        "process": prepared.inspect(),
        "output": direct.to_dict(),
        "limit_failure": limited.to_dict(),
    }
