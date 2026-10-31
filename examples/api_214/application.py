"""A small, offline invoice: Tool → Agent → System → Environment, with Eval."""

import pydantic
import agentic_systems as toolkit


class Invoice(pydantic.BaseModel):
    subtotal: int
    total: int | None = None
    currency: str | None = None
    status: str | None = None


@toolkit.tool
def quote(subtotal: int, *, context: toolkit.Context) -> dict:
    """Calculate integer money using the domain's tax policy."""
    return {
        "total": subtotal * (100 + context.data["tax_percent"]) // 100,
        "currency": context.data["currency"],
    }


domain = toolkit.Context(
    {"tax_percent": 16, "currency": "MXN"}, sources=("tax-policy-v1",)
)
capability = toolkit.skill(
    name="invoicing", tools=(quote,), instructions="Amounts are integer MXN."
)
memory = toolkit.Memory(capacity=3)
agent_graph = toolkit.Graph(Invoice)
agent_graph.add_node("quote", quote)
agent_graph.add_edge(toolkit.START, "quote")
agent_graph.add_edge("quote", toolkit.END)
agent = toolkit.Agent(
    "accountant", graph=agent_graph, skills=(capability,), context=domain, memory=memory
)
system_graph = toolkit.Graph(Invoice)
system_graph.add_node("accountant", agent)
def approve_step(state):
    return {"status": "approved"}
system_graph.add_node("approve", approve_step)
def review_step(state):
    return {"status": "review"}
system_graph.add_node("review", review_step)
system_graph.add_edge(toolkit.START, "accountant")
system_graph.add_conditional_edges(
    "accountant",
    lambda state: "review" if state.total > 1000 else "approve",
    ["approve", "review"],
)
system_graph.add_edge("approve", toolkit.END)
system_graph.add_edge("review", toolkit.END)
system = toolkit.System("billing", graph=system_graph, context=domain)
environment_graph = toolkit.Graph(Invoice)
environment_graph.add_node("billing", system)
environment_graph.add_edge(toolkit.START, "billing")
environment_graph.add_edge("billing", toolkit.END)
environment = toolkit.Environment(
    "batch",
    graph=environment_graph,
    records=({"subtotal": 100}, {"subtotal": 200}),
    state={"sum": 0},
    update=lambda state, record, result: {"sum": state["sum"] + result.data["total"]},
)
evaluation = toolkit.Eval(
    "invoice-contract",
    system,
    cases=({"input": {"subtotal": 100}, "expected": {"ok": True}},),
    checks=(
        lambda result, case: {
            "ok": result.data["total"] == 116 and result.data["currency"] == "MXN"
        },
    ),
)


def demonstrate():
    single = agent.run({"subtotal": 100})
    team = system.compile().run({"subtotal": 100})
    batch = environment.run()
    checked = evaluation.run()
    assert single.ok and single.data["total"] == 116
    assert team.ok and team.data["status"] == "approved"
    assert batch.ok and batch.data["summary"]["state"] == {"sum": 348}
    assert checked.ok
    results = [single, team, batch, checked]
    assert all((result.check_invariants().ok for result in results))
    return {
        "input": [{"subtotal": 100}, {"subtotal": 200}],
        "process": [
            "quote with Tool + Context",
            "Agent graph",
            "System decision",
            "Environment iteration",
            "Eval checks",
        ],
        "output": {
            "agent": single.data,
            "system": team.data,
            "environment": batch.data["summary"],
            "eval_ok": checked.ok,
        },
        "memory": memory.read(),
        "human_lineage": batch.lineage().render(),
        "agent_lineage": batch.lineage().to_prompt_context(),
        "run_results": [result.to_dict() for result in results],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(demonstrate()["output"], ensure_ascii=False, indent=2))
