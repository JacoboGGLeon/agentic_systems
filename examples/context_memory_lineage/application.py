"""Order triage: domain Context, episodic Memory and two views of one lineage."""

import pydantic
import agentic_systems as toolkit


@toolkit.tool
def normalize(order_id: str, amount: int) -> dict:
    if amount < 0:
        raise ValueError("Amount must be nonnegative")
    return {"order_id": order_id.strip(), "amount": amount}


context_observations = []


@toolkit.tool
def assess(order_id: str, amount: int, *, context: toolkit.Context) -> dict:
    """Apply the declared policy; previous episodes are observations, not authority."""
    context_observations.append(context.to_dict())
    return {
        "order_id": order_id,
        "amount": amount,
        "currency": context.data["currency"],
        "decision": "review"
        if amount > context.data["review_threshold"]
        else "approve",
    }


def choose_next(data):
    return "review" if data.decision == "review" else "approve"


class OrderState(pydantic.BaseModel):
    order_id: str | None = None
    amount: int | None = None
    currency: str | None = None
    decision: str | None = None
    status: str | None = None


def build_system(*, threshold=100):
    domain = toolkit.Context(
        {"currency": "MXN", "review_threshold": threshold}, sources=("sales-policy-v3",)
    )
    graph = toolkit.Graph(OrderState)
    graph.add_node("normalize", normalize)
    graph.add_node("assess", assess)
    def approve_step(state):
        return {"status": "approved"}
    graph.add_node("approve", approve_step)
    def review_step(state):
        return {"status": "pending_review"}
    graph.add_node("review", review_step)
    graph.add_edge(toolkit.START, "normalize")
    graph.add_edge("normalize", "assess")
    graph.add_conditional_edges("assess", choose_next, ["review", "approve"])
    graph.add_edge("approve", toolkit.END)
    graph.add_edge("review", toolkit.END)
    return toolkit.System(
        "orders", graph=graph, context=domain, memory=toolkit.Memory()
    )


def demonstrate():
    context_start = len(context_observations)
    system = build_system()
    compiled = system.compile()
    first = compiled.run({"order_id": " P-1 ", "amount": 75})
    second = compiled.run({"order_id": "P-2", "amount": 125})
    assert first.ok and first.data["status"] == "approved"
    assert second.ok and second.data["status"] == "pending_review"
    first_context, second_context = context_observations[context_start:context_start + 2]
    assert len(first_context["episodes"]) == 0 and len(second_context["episodes"]) == 1
    assert "previous_episodes" not in first.data and "previous_episodes" not in second.data
    changed = build_system(threshold=50).run({"order_id": "P-3", "amount": 75})
    assert changed.ok and changed.data["status"] == "pending_review"
    graph = toolkit.Graph(OrderState)
    graph.add_node("orders", build_system())
    graph.add_edge(toolkit.START, "orders")
    graph.add_edge("orders", toolkit.END)
    episode = toolkit.Environment(
        "daily-orders",
        graph=graph,
        records=({"order_id": "P-4", "amount": 10}, {"order_id": "P-5", "amount": 150}),
        state={"processed": 0},
        update=lambda state, row, result: {"processed": state["processed"] + 1},
    ).run()
    evaluation = toolkit.Eval(
        "sales-policy",
        build_system(),
        ({"input": {"order_id": "E-1", "amount": 20}, "expected": {"ok": True}},),
        checks=(lambda result, case: {"ok": result.data["status"] == "approved"},),
    ).run()
    assert episode.ok and evaluation.ok
    results = [first, second, changed, episode, evaluation]
    assert all((r.check_invariants().ok for r in results))
    return {
        "version": toolkit.__version__,
        "orchestration": "langgraph",
        "input": {"order_id": "P-2", "amount": 125},
        "process": [
            "normalize",
            "assess with Context and selected Memory",
            "decision",
            "approve/review",
        ],
        "outputs": [r.data for r in results[:3]],
        "human_lineage": second.lineage(name="P-2").render(),
        "agent_lineage": second.lineage().to_prompt_context(),
        "memory": system.memory.read(),
        "received_contexts": [first_context, second_context],
        "run_results": [r.to_dict() for r in results],
        "inference_requests": 0,
    }
