"""Progressive construction: runtime, actor SDKs, graph Agent and a shared root deadline."""

import pydantic
import agentic_systems as toolkit


# 1. Runtime selection and the actor scheduler are configured together.
execution = toolkit.runtime(
    provider="python-runtime",
    timeout_s=10,
    max_retries=0,
    max_turns=2,
    max_tool_calls=1,
)


# 2. Each Python actor receives one deterministic capability.
@toolkit.tool
def add_fee(amount_cents: int) -> dict:
    return {"amount_cents": amount_cents + 500}


@toolkit.tool
def apply_discount(amount_cents: int) -> dict:
    return {"amount_cents": amount_cents * 90 // 100}


@toolkit.tool
def assess(amount_cents: int, budget_cents: int) -> dict:
    return {"decision": "approved" if amount_cents <= budget_cents else "review"}


fee_agent = toolkit.Agent(
    "fee_agent", runtime=execution, framework=toolkit.framework("native"),
    skills=(toolkit.skill(name="fee", tools=(add_fee,)),),
)
discount_agent = toolkit.Agent(
    "discount_agent", runtime=execution, framework=toolkit.framework("openai-agents"),
    skills=(toolkit.skill(name="discount", tools=(apply_discount,)),),
)
review_agent = toolkit.Agent(
    "review_agent", runtime=execution, framework=toolkit.framework("strands"),
    skills=(toolkit.skill(name="assessment", tools=(assess,)),),
)


# 3. Context is injected directly in graph nodes and Tools.
class QuoteState(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    amount_cents: int = pydantic.Field(gt=0)
    currency: str | None = None
    budget_cents: int | None = None
    decision: str | None = None


def read_policy(state, *, context: toolkit.Context):
    return {
        "currency": context.data["currency"],
        "budget_cents": context.data["budget_cents"],
    }


# 4. A graph Agent coordinates other Agents; it has no actor runtime of its own.
quote_graph = toolkit.Graph(QuoteState)
quote_graph.add_node("policy", read_policy)
def fee_step(state):
    return fee_agent.run({"amount_cents": state.amount_cents})
quote_graph.add_node(
    "fee", fee_step,
)
def discount_step(state):
    return discount_agent.run({"amount_cents": state.amount_cents})
quote_graph.add_node(
    "discount", discount_step,
)
quote_graph.add_edge(toolkit.START, "policy")
quote_graph.add_edge("policy", "fee")
quote_graph.add_edge("fee", "discount")
quote_graph.add_edge("discount", toolkit.END)
quote_agent = toolkit.Agent("quote_agent", graph=quote_graph)


# 5. A System combines the graph Agent with the Strands actor Agent.
system_graph = toolkit.Graph(QuoteState)
system_graph.add_node("quote", quote_agent)
def review_step(state):
    return review_agent.run({"amount_cents": state.amount_cents, "budget_cents": state.budget_cents})
system_graph.add_node(
    "review",
    review_step,
)
system_graph.add_edge(toolkit.START, "quote")
system_graph.add_edge("quote", "review")
system_graph.add_edge("review", toolkit.END)
financial_system = toolkit.System(
    "quote_system", graph=system_graph,
    context=toolkit.Context(
        {"currency": "MXN", "budget_cents": 9000},
        sources=("fictional-quote-policy-v1",),
    ),
)
financial_harness = financial_system.compile()


def run():
    # 6. The root deadline is shared by the whole invocation, including nested Agents.
    result = financial_harness.run(
        {"amount_cents": 10000},
        timeout_s=30,
    )
    assert result.ok and result.data == {
        "amount_cents": 9450, "currency": "MXN",
        "budget_cents": 9000, "decision": "review",
    }, result.to_dict()
    assert result.check_invariants().ok
    assert result.usage.get("inference_requests", 0) == 0
    return result


if __name__ == "__main__":
    result = run()
    print(result.data)
    print("Observed graph activations:", result.meta['nodes_observed'])
    print(result.human_results())
