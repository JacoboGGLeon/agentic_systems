"""Agentic Systems 2.1.4; explicit LangGraph and deterministic business rules."""

import pydantic
from typing import Any
import agentic_systems as toolkit


class Closed(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")


class Payload(Closed):
    order_id: str
    amount: int
    currency: str
    account_days: int


@toolkit.tool
def refund_policy(order_id: str, amount: int, currency: str, account_days: int) -> dict:
    input = Payload(
        order_id=order_id, amount=amount, currency=currency, account_days=account_days
    ).model_dump(mode="python")
    approved = (
        input["amount"] <= 500
        and input["currency"] == "MXN"
        and (input["account_days"] >= 7)
    )
    return {
        "order_id": input["order_id"],
        "decision": "approved" if approved else "manual_review",
        "amount": input["amount"],
    }


capability = toolkit.skill(name="refund_policy", tools=(refund_policy,))


class WorkState(pydantic.BaseModel):
    input: dict
    order_id: Any | None = None
    decision: Any | None = None
    amount: Any | None = None


class Output(pydantic.BaseModel):
    order_id: Any
    decision: Any
    amount: Any


graph = toolkit.Graph(WorkState, output_schema=Output)
def refund_policy_step(state):
    return refund_policy.run(state.input)
graph.add_node(
    "refund_policy",
    refund_policy_step,
)
graph.add_edge(toolkit.START, "refund_policy")
graph.add_edge("refund_policy", toolkit.END)
app = toolkit.Agent("refund_policy", graph=graph, skills=(capability,))
sample = {"order_id": "A17", "amount": 280, "currency": "MXN", "account_days": 90}


def run():
    result = app.run({"input": sample})
    assert result.ok and result.data == {
        "order_id": "A17",
        "decision": "approved",
        "amount": 280,
    }, result.to_dict()
    return result
