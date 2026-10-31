"""Graph composition: typed Tools, two Agents, episodes and isolated evaluation."""

import pydantic
import agentic_systems as toolkit


class Amount(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    amount: int = pydantic.Field(gt=0)


class Fees(Amount):
    fee: int = pydantic.Field(ge=0)


class Quote(Fees):
    total: int = pydantic.Field(gt=0)


class Decision(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    decision: str = pydantic.Field(pattern="^(approve|review)$")


class PaymentState(Amount):
    fee: int | None = None
    total: int | None = None
    decision: str | None = None
    status: str | None = None


class PaymentOutput(Quote):
    decision: str = pydantic.Field(pattern="^(approve|review)$")
    status: str = pydantic.Field(pattern="^(approved|pending_review)$")


class Policy(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    fee_bps: int = pydantic.Field(ge=0)
    ceiling: int = pydantic.Field(gt=0)


@toolkit.tool(input_schema=Amount, output_schema=Fees)
def calculate_fee(payment: Amount, *, context: toolkit.Context) -> Fees:
    return Fees(
        amount=payment.amount, fee=payment.amount * context.data["fee_bps"] // 10000
    )


@toolkit.tool(input_schema=Fees, output_schema=Quote)
def calculate_total(payment: Fees) -> Quote:
    return Quote(
        amount=payment.amount, fee=payment.fee, total=payment.amount + payment.fee
    )


@toolkit.tool(input_schema=Quote, output_schema=Decision)
def decide(quote: Quote, *, context: toolkit.Context) -> Decision:
    return Decision(
        decision="approve" if quote.total <= context.data["ceiling"] else "review"
    )


capabilities = toolkit.skill(
    name="fees",
    tools=(calculate_fee, calculate_total),
    instructions="Calculate fees and totals in integer cents from the declared policy.",
)

# Agent graph: organize the steps of one capability.
fee_graph = toolkit.Graph(PaymentState, input_schema=Amount, output_schema=Quote)
fee_graph.add_node("fee", calculate_fee)
fee_graph.add_node("total", calculate_total)
fee_graph.add_edge(toolkit.START, "fee")
fee_graph.add_edge("fee", "total")
fee_graph.add_edge("total", toolkit.END)
fee_agent = toolkit.Agent("fee_capability", graph=fee_graph, skills=(capabilities,))

reviewer = toolkit.Agent(
    "reviewer",
    runtime=toolkit.runtime(provider="python-runtime"),
    skills=(toolkit.skill(name="review", tools=(decide,)),),
)


def fee_step(state):
    return fee_agent.run({"amount": state.amount})


def review_step(state):
    return reviewer.run(
        {"amount": state.amount, "fee": state.fee, "total": state.total}
    )


def choose(state):
    return state.decision


def approve(state):
    return {"status": "approved"}


def require_review(state):
    return {"status": "pending_review"}


# System graph: coordinate Agents and the application decision.
system_graph = toolkit.Graph(
    PaymentState, input_schema=Amount, output_schema=PaymentOutput
)
system_graph.add_node("fees", fee_step)
system_graph.add_node("review", review_step)
system_graph.add_node("approve", approve)
system_graph.add_node("review_required", require_review)
system_graph.add_edge(toolkit.START, "fees")
system_graph.add_edge("fees", "review")
system_graph.add_conditional_edges(
    "review", choose, {"approve": "approve", "review": "review_required"}
)
system_graph.add_edge("approve", toolkit.END)
system_graph.add_edge("review_required", toolkit.END)

memory = toolkit.Memory()
system = toolkit.System(
    "payments",
    graph=system_graph,
    context=toolkit.Context(
        Policy(fee_bps=100, ceiling=10000), sources=("payment-policy-v1",)
    ),
    memory=memory,
)
harness = system.compile()


# Environment graph: episodes, state and an explicit business reward metric.
def observe_payment(record, state):
    return {"amount": record["amount"]}


def update_day(state, record, result):
    reward = (
        1 if result.ok and result.data["status"] == record["expected_status"] else 0
    )
    return {
        "processed": state["processed"] + 1,
        "reward": reward,
        "total_reward": state["total_reward"] + reward,
    }


episode_graph = toolkit.Graph(
    PaymentState, input_schema=Amount, output_schema=PaymentOutput
)
episode_graph.add_node("payment", system)
episode_graph.add_edge(toolkit.START, "payment")
episode_graph.add_edge("payment", toolkit.END)
environment = toolkit.Environment(
    "daily_payments",
    graph=episode_graph,
    records=(
        {"amount": 5000, "expected_status": "approved"},
        {"amount": 12000, "expected_status": "pending_review"},
    ),
    state={"processed": 0, "reward": 0, "total_reward": 0},
    observe=observe_payment,
    update=update_day,
)


def check_quote(result, case):
    amount = case["input"]["amount"]
    fee = amount // 100
    decision = "approve" if amount + fee <= 10000 else "review"
    status = "approved" if decision == "approve" else "pending_review"
    return {
        "ok": result.data
        == {
            "amount": amount,
            "fee": fee,
            "total": amount + fee,
            "decision": decision,
            "status": status,
        }
    }


# Eval automatically gives each case its own Memory view, without changing this API.
evaluation = toolkit.Eval(
    "payment_acceptance",
    unit=system,
    cases=(
        {"name": "approved", "input": {"amount": 5000}, "expected": {"ok": True}},
        {"name": "review", "input": {"amount": 12000}, "expected": {"ok": True}},
    ),
    checks=(check_quote,),
)


def run():
    result = harness.run({"amount": 5000}, timeout_s=30)
    episode = environment.run(timeout_s=30)
    before_eval = memory.read()
    checked = evaluation.run(timeout_s=30)
    assert result.ok and result.data["fee"] == 50 and result.data["total"] == 5050
    assert episode.ok and [row["status"] for row in episode.data["outputs"]] == [
        "approved",
        "pending_review",
    ]
    assert episode.data["summary"]["state"]["total_reward"] == 2
    assert checked.ok and checked.data["passed"] == 2
    assert memory.read() == before_eval, "Eval must not change production Memory"
    for output in (result, episode, checked):
        assert output.check_invariants().ok, output.to_dict()
        assert output.usage.get("inference_requests", 0) == 0
    return {
        "input": {"amount": 5000},
        "process": "fee Agent Graph -> typed Tools -> reviewer -> decision",
        "output": result.data,
        "result": result,
        "episode": episode,
        "evaluation": checked,
        "memory": memory.read(),
        "human_results": result.human_results(),
        "reward_scope": "Explicit metric in Environment.update; no built-in reward parameter or policy learning",
        "agent_lineage": result.lineage().to_prompt_context(),
    }


if __name__ == "__main__":
    print(run()["human_results"])
