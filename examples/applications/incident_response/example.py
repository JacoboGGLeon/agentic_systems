"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Event(Closed):
    status: str


class Payload(Closed):
    events: list[Event]


@toolkit.tool
def triage(events: list[Event]) -> dict:
    input = Payload(events=events).model_dump(mode="python")
    failures = sum((event["status"] == "error" for event in input["events"]))
    return {
        "failures": failures,
        "severity": "high" if failures >= 2 else "low",
        "action": "isolate and investigate" if failures >= 2 else "monitor",
    }


capability = toolkit.skill(name="triage", tools=(triage,))


class WorkState(pydantic.BaseModel):
    input: dict
    failures: Any | None = None
    severity: Any | None = None
    action: Any | None = None


class Output(pydantic.BaseModel):
    failures: Any
    severity: Any
    action: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def triage_step(state):
    return triage.run(state.input)
graph.add_node(
    "triage", triage_step
)
graph.add_edge(toolkit.START, "triage")
graph.add_edge("triage", toolkit.END)
app = toolkit.Agent("triage", graph=graph, skills=(capability,))
sample = {"events": [{"status": "error"}, {"status": "ok"}, {"status": "error"}]}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {
        "failures": 2,
        "severity": "high",
        "action": "isolate and investigate",
    }, result.to_dict()
    return result
