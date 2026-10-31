"""Treasury simulation: explicit composition, Python only, no bank operations."""

import pydantic
import agentic_systems as toolkit


class PaymentState(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    reference: str
    amount_cents: int = pydantic.Field(gt=0)
    balance_cents: int = pydantic.Field(ge=0)
    available_cents: int | None = None
    previous_episodes: int | None = None
    decision: str | None = None
    balance_after_cents: int | None = None


class Decision(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    reference: str
    amount_cents: int
    decision: str = pydantic.Field(pattern="^(approved|review|rejected)$")
    balance_after_cents: int = pydantic.Field(ge=0)


@toolkit.tool
def liquidity(balance_cents: int, *, context: toolkit.Context) -> dict:
    return {
        "available_cents": max(0, balance_cents - context.data["reserve_cents"]),
        "previous_episodes": len(context.episodes),
    }


@toolkit.tool
def authorize(
    amount_cents: int, balance_cents: int, *, context: toolkit.Context
) -> dict:
    approved = amount_cents <= context.data["review_above_cents"]
    return {
        "decision": "approved" if approved else "review",
        "balance_after_cents": balance_cents - amount_cents if approved else balance_cents,
    }


domain = toolkit.Context(
    {"currency": "MXN", "reserve_cents": 30000, "review_above_cents": 30000},
    sources=("fictional-treasury-policy-v1",),
)
memory = toolkit.Memory(capacity=20)
execution = toolkit.runtime(provider="python-runtime")
liquidity_skill = toolkit.skill(name="liquidity", tools=(liquidity,))
authorization_skill = toolkit.skill(name="authorization", tools=(authorize,))
analyst = toolkit.Agent("liquidity_analyst", runtime=execution, skills=(liquidity_skill,))
officer = toolkit.Agent("policy_officer", runtime=execution, skills=(authorization_skill,))

graph = toolkit.Graph(PaymentState, output_schema=Decision)
def liquidity_step(state):
    return analyst.run({"balance_cents": state.balance_cents})
graph.add_node(
    "liquidity",
    liquidity_step,
)
def authorize_step(state):
    return officer.run({"amount_cents": state.amount_cents, "balance_cents": state.balance_cents})
graph.add_node(
    "authorize",
    authorize_step,
)
def reject_step(s):
    return {"decision": "rejected", "balance_after_cents": s.balance_cents}
graph.add_node(
    "reject",
    reject_step,
)
graph.add_edge(toolkit.START, "liquidity")
graph.add_conditional_edges(
    "liquidity",
    lambda s: "authorize" if s.amount_cents <= s.available_cents else "reject",
    ["authorize", "reject"],
)
graph.add_edge("authorize", toolkit.END)
graph.add_edge("reject", toolkit.END)

financial_system = toolkit.System(
    "financial_system", graph=graph, context=domain, memory=memory,
)
financial_harness = financial_system.compile()

records = (
    {"reference": "P-001", "amount_cents": 12000},
    {"reference": "P-002", "amount_cents": 40000},
    {"reference": "P-003", "amount_cents": 90000},
)
daily_graph = toolkit.Graph(PaymentState, output_schema=Decision)
daily_graph.add_node("financial_system", financial_harness.run)
daily_graph.add_edge(toolkit.START, "financial_system")
daily_graph.add_edge("financial_system", toolkit.END)
daily_environment = toolkit.Environment(
    "treasury_day", graph=daily_graph, records=records,
    state={"balance_cents": 100000}, max_steps=3,
    observe=lambda row, state: {**row, "balance_cents": state["balance_cents"]},
    update=lambda state, row, result: {"balance_cents": result.data["balance_after_cents"]},
)


def check_day(result, case):
    outputs = result.data["outputs"]
    return {
        "ok": (
            [row["decision"] for row in outputs] == ["approved", "review", "rejected"]
            and [row["balance_after_cents"] for row in outputs] == [88000, 88000, 88000]
            and result.data["summary"]["state"] == {"balance_cents": 88000}
            and result.data["summary"]["processed"] == 3
            and result.check_invariants().ok
        )
    }


evaluation = toolkit.Eval(
    "treasury_acceptance", unit=daily_environment,
    cases=({
        "name": "approved_review_rejected",
        "input": {"records": records, "state": {"balance_cents": 100000}},
        "expected": {"ok": True},
    },),
    checks=(check_day,),
)


def run():
    deadline_s = 30
    single = financial_harness.run(
        {"reference": "SINGLE", "amount_cents": 12000, "balance_cents": 100000},
        timeout_s=deadline_s,
    )
    assert single.ok and single.data == {
        "reference": "SINGLE", "amount_cents": 12000,
        "decision": "approved", "balance_after_cents": 88000,
    }, single.to_dict()
    episode = daily_environment.run(timeout_s=deadline_s)
    assert episode.ok and check_day(episode, {})["ok"], episode.to_dict()
    checked = evaluation.run(timeout_s=deadline_s)  # Executes the three records again.
    assert checked.ok and checked.data["passed"] == 1, checked.to_dict()
    for result in (single, episode, checked):
        assert isinstance(result, toolkit.RunResult)
        assert result.check_invariants().ok
        assert result.usage.get("inference_requests", 0) == 0
    return {
        "version": toolkit.__version__,
        "scope": "deterministic treasury simulation; no transfers, no inference",
        "input": {"balance_cents": 100000, "records": records},
        "process": "Environment -> compiled System -> analyst -> conditional edge -> officer/reject -> update -> Eval",
        "single": single.to_dict(),
        "episode": episode.to_dict(),
        "evaluation": checked.to_dict(),
        "memory": memory.read(),
        "human_results": episode.human_results(),
        "lineage": episode.lineage().to_dict(),
        "agent_context": episode.lineage().to_prompt_context(),
        "inference_requests": 0,
    }


if __name__ == "__main__":
    report = run()
    print(report["human_results"])
    print("Decisions:", [row["decision"] for row in report["episode"]["data"]["outputs"]])
    print("Closing balance:", report["episode"]["data"]["summary"]["state"])
    print("Eval:", report["evaluation"]["data"]["passed"], "/", report["evaluation"]["data"]["total"])
