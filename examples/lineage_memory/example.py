"""Two Agents, two executions: business state stays separate from Context."""

import pydantic
import agentic_systems as toolkit


class Payment(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    payment_id: str = pydantic.Field(min_length=1)
    amount: int = pydantic.Field(gt=0)
    fee: int | None = None
    decision: str | None = None


# Observation only: these snapshots never become graph state or instructions.
received_contexts = []


@toolkit.tool
def calculate_fee(amount: int, *, context: toolkit.Context) -> dict:
    received_contexts.append({"agent": "fees", "context": context.to_dict()})
    return {"fee": amount * context.data["fee_bps"] // 10000}


@toolkit.tool
def decide(payment_id: str, amount: int, fee: int, *, context: toolkit.Context) -> dict:
    received_contexts.append({"agent": "reviewer", "context": context.to_dict()})

    # Current evidence must support the fee before this agent may approve it.
    fee_evidence = [row for row in context.lineage if row["name"] == "fees"]
    if not fee_evidence or not fee_evidence[-1]["ok"]:
        raise ValueError("Missing successful fees lineage")
    expected_fee = amount * context.data["fee_bps"] // 10000
    if fee_evidence[-1]["data"].get("fee") != fee or fee != expected_fee:
        raise ValueError("Fee is inconsistent with lineage or current policy")

    # Previous approval of the same business identifier changes the decision.
    # Use structured recorded evidence, never parse a human-readable explanation.
    for episode in context.episodes:
        if not episode["ok"]:
            continue
        for step in episode["lineage"]["steps"]:
            if step["kind"] != "execution" or step["title"] != "payments":
                continue
            evidence = step["evidence"]
            previous = evidence.get("data", {})
            if (evidence["ok"] and previous.get("payment_id") == payment_id
                    and previous.get("decision") == "approve"):
                return {"decision": "review_duplicate"}

    return {
        "decision": "approve" if amount + fee <= context.data["ceiling"] else "review"
    }


fee_graph = toolkit.Graph(Payment)
fee_graph.add_node("calculate_fee", calculate_fee)
fee_graph.add_edge(toolkit.START, "calculate_fee")
fee_graph.add_edge("calculate_fee", toolkit.END)
fee_agent = toolkit.Agent("fees", fee_graph)

review_graph = toolkit.Graph(Payment)
review_graph.add_node("decide", decide)
review_graph.add_edge(toolkit.START, "decide")
review_graph.add_edge("decide", toolkit.END)
reviewer = toolkit.Agent("reviewer", review_graph)

payment_graph = toolkit.Graph(Payment)
payment_graph.add_node("fees", fee_agent)
payment_graph.add_node("reviewer", reviewer)
payment_graph.add_edge(toolkit.START, "fees")
payment_graph.add_edge("fees", "reviewer")
payment_graph.add_edge("reviewer", toolkit.END)

memory = toolkit.Memory(capacity=2)
system = toolkit.System(
    "payments",
    payment_graph,
    context=toolkit.Context(
        {"currency": "MXN", "fee_bps": 100, "ceiling": 10000},
        sources=("payment-policy-v1",),
    ),
    memory=memory,
)

harness = system.compile()
assert received_contexts == [] and memory.read() == []

first = harness.run({"payment_id": "PAY-001", "amount": 5000})
second = harness.run({"payment_id": "PAY-001", "amount": 5000})
assert first.ok and second.ok
assert first.data == {"payment_id": "PAY-001", "amount": 5000, "fee": 50, "decision": "approve"}
assert second.data == {"payment_id": "PAY-001", "amount": 5000, "fee": 50, "decision": "review_duplicate"}

assert len(received_contexts) == 4
for index, row in enumerate(received_contexts):
    context = row["context"]
    assert context["data"] == {"currency": "MXN", "fee_bps": 100, "ceiling": 10000}
    assert context["sources"] == ["payment-policy-v1"]
    assert len(context["episodes"]) == index // 2
    if row["agent"] == "fees":
        assert context["lineage"] == []
    else:
        assert any(item["name"] == "fees" for item in context["lineage"])
    if index >= 2:
        assert context["episodes"][0]["execution_id"] == first.execution_id
        assert "lineage" in context["episodes"][0]

assert len(memory.read()) == 2
assert set(first.data) == set(second.data) == {"payment_id", "amount", "fee", "decision"}

def run():
    """Return evidence from the explicit declarations and executions above."""
    return {
        "run_results": [first, second],
        "contexts": received_contexts,
        "memory": memory.read(),
        "human_results": [first.human_results(), second.human_results()],
    }


if __name__ == "__main__":
    for result in (first, second):
        print(result.human_results())
