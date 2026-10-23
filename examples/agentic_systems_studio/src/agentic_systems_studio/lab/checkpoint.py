"""Native LangGraph pause/resume projected through a public Agent result."""
from typing import TypedDict
from uuid import uuid4
import agentic_systems as toolkit


def run():
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import interrupt, Command

    class State(TypedDict, total=False):
        amount: int
        approved: bool

    def approval(state):
        decision = interrupt({"question": "Approve this expense?", "amount": state["amount"]})
        if type(decision) is not bool:
            raise ValueError("An explicit boolean approval is required")
        return {"approved": decision}

    graph = StateGraph(State)
    graph.add_node("approval", approval)
    graph.add_edge(START, "approval")
    graph.add_edge("approval", END)
    compiled = graph.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "expense-" + uuid4().hex}}

    def step(request):
        raw = compiled.invoke(Command(resume=request["resume"]) if "resume" in request else request, config=config)
        if raw.get("__interrupt__"):
            return {"paused": True, "request": raw["__interrupt__"][0].value}
        return {"paused": False, "amount": raw["amount"], "approved": raw["approved"]}

    actor = toolkit.Agent("human_approval", toolkit.Action("checkpoint", step))
    paused = actor.run({"amount": 280})
    resumed = actor.run({"resume": True})
    assert paused.ok and paused.data["paused"]
    assert resumed.ok and resumed.data == {"paused": False, "amount": 280, "approved": True}
    return {"feature": "LangGraph interrupt/checkpoint/resume", "input": {"amount": 280},
            "paused": paused.to_dict(), "resumed": resumed.to_dict(), "inference_requests": 0,
            "scope": "Native LangGraph feature wrapped by Action; not an added toolkit constructor"}
