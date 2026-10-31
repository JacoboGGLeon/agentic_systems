"""Seven agents, disjoint parallel updates and business routing; LangGraph only."""

import pydantic
import agentic_systems as toolkit
from . import tools, skills


class State(pydantic.BaseModel):
    order: dict | None = None
    validation: dict | None = None
    pricing: dict | None = None
    inventory: dict | None = None
    policy: dict | None = None
    simulate_inventory_failure: bool | None = None
    order_id: str | None = None
    decision: str | None = None
    total_cents: int | None = None
    currency: str | None = None
    reasons: list | None = None
    next_action: str | None = None


class Price(pydantic.BaseModel):
    pricing: dict


class Stock(pydantic.BaseModel):
    inventory: dict


class Receipt(pydantic.BaseModel):
    order_id: str
    decision: str
    total_cents: int | None
    currency: str
    reasons: list
    next_action: str


def as_state(data):
    return {"state": data}


def after_policy(data):
    return {"approved": "approve", "review": "review", "rejected": "reject"}[
        data.policy["decision"]
    ]


def build_system():
    intake_graph = toolkit.Graph(State)
    def normalize_step(state):
        return tools.normalize_order.run(as_state(state))
    intake_graph.add_node(
        "normalize", normalize_step
    )
    def validate_step(state):
        return tools.validate_order.run(as_state(state))
    intake_graph.add_node(
        "validate", validate_step
    )
    intake_graph.add_edge(toolkit.START, "normalize")
    intake_graph.add_edge("normalize", "validate")
    intake_graph.add_edge("validate", toolkit.END)
    intake = toolkit.Agent("intake", graph=intake_graph, skills=(skills.intake,))
    agents = {"intake": intake}
    for name, operation, schema, capability in (
        ("pricing", tools.price_order, Price, skills.pricing),
        ("inventory", tools.check_inventory, Stock, skills.inventory),
        ("policy", tools.assess_policy, State, skills.policy),
        ("approve", tools.approve_order, Receipt, skills.approval),
        ("review", tools.review_order, Receipt, skills.review),
        ("reject", tools.reject_order, Receipt, skills.rejection),
    ):
        graph = toolkit.Graph(State, output_schema=schema)
        def node_step(state):
            return operation.run(as_state(state))
        graph.add_node(name, node_step)
        graph.add_edge(toolkit.START, name)
        graph.add_edge(name, toolkit.END)
        agents[name] = toolkit.Agent(name, graph=graph, skills=(capability,))
    graph = toolkit.Graph(State, output_schema=Receipt)
    for name, agent in agents.items():
        graph.add_node(name, agent)
    graph.add_edge(toolkit.START, "intake")
    graph.add_conditional_edges(
        "intake",
        lambda state: (
            ["pricing", "inventory"] if state.validation["valid"] else "reject"
        ),
        ["pricing", "inventory", "reject"],
    )
    graph.add_edge(["pricing", "inventory"], "policy")
    graph.add_conditional_edges("policy", after_policy, ["approve", "review", "reject"])
    for name in ("approve", "review", "reject"):
        graph.add_edge(name, toolkit.END)
    return toolkit.System("order_fulfillment", graph=graph)
