from tutorials._offline import blocked_attempts
from copy import deepcopy
import json
from pathlib import Path
import agentic_systems as toolkit


def catalog():
    return {
        "currency": "MXN",
        "products": {
            "KEYBOARD": {"unit_price_cents": 35000, "stock": 10},
            "MONITOR": {"unit_price_cents": 250000, "stock": 3},
            "DOCK": {"unit_price_cents": 120000, "stock": 5},
        },
        "shipping_cents": {"MX": 5000, "US": 12000},
        "manual_review_threshold_cents": 200000,
    }


@toolkit.tool
def normalize_order(state: dict) -> dict:
    """Normalize text fields without coercing quantities, budgets or types."""
    data = deepcopy(state)
    order = data.get("order")
    if isinstance(order, dict):
        for key in ("id", "currency", "country"):
            if isinstance(order.get(key), str):
                order[key] = order[key].strip()
        for item in (
            order.get("items", []) if isinstance(order.get("items"), list) else []
        ):
            if isinstance(item, dict) and isinstance(item.get("sku"), str):
                item["sku"] = item["sku"].strip().upper()
    return data


@toolkit.tool
def validate_order(state: dict) -> dict:
    """Return business validation issues without running pricing on invalid orders."""
    data, rules = (deepcopy(state), catalog())
    order, issues = (data.get("order"), [])
    if not isinstance(order, dict):
        order = {}
        issues.append("invalid_order")
    if not isinstance(order.get("id"), str) or not order.get("id"):
        issues.append("invalid_id")
    if order.get("currency") != rules["currency"]:
        issues.append("unsupported_currency")
    if (
        not isinstance(order.get("country"), str)
        or order.get("country") not in rules["shipping_cents"]
    ):
        issues.append("unsupported_country")
    if type(order.get("budget_cents")) is not int or order["budget_cents"] < 0:
        issues.append("invalid_budget")
    items = order.get("items")
    if not isinstance(items, list) or not items:
        issues.append("invalid_items")
    else:
        for item in items:
            if not isinstance(item, dict):
                issues.append("invalid_item")
                continue
            if (
                not isinstance(item.get("sku"), str)
                or item.get("sku") not in rules["products"]
            ):
                issues.append("unknown_sku")
            if type(item.get("quantity")) is not int or item["quantity"] < 1:
                issues.append("invalid_quantity")
    data["order"] = order
    data["validation"] = {"valid": not issues, "issues": list(dict.fromkeys(issues))}
    return data


@toolkit.tool
def price_order(state: dict) -> dict:
    """Price every order line and shipping using one local catalog snapshot."""
    data, rules = (deepcopy(state), catalog())
    order = data["order"]
    subtotal = sum(
        (
            rules["products"][line["sku"]]["unit_price_cents"] * line["quantity"]
            for line in order["items"]
        )
    )
    shipping = rules["shipping_cents"][order["country"]]
    data["pricing"] = {
        "subtotal_cents": subtotal,
        "shipping_cents": shipping,
        "total_cents": subtotal + shipping,
    }
    return data


@toolkit.tool
def check_inventory(state: dict) -> dict:
    """Aggregate duplicate SKU lines before comparing requested quantities to stock."""
    if state.get("simulate_inventory_failure"):
        raise RuntimeError("controlled_inventory_unavailable")
    data, rules, requested = (deepcopy(state), catalog(), {})
    for line in data["order"]["items"]:
        requested[line["sku"]] = requested.get(line["sku"], 0) + line["quantity"]
    shortages = [
        sku
        for sku, quantity in requested.items()
        if quantity > rules["products"][sku]["stock"]
    ]
    data["inventory"] = {
        "available": not shortages,
        "shortages": shortages,
        "requested": requested,
    }
    return data


@toolkit.tool
def assess_policy(state: dict) -> dict:
    """Apply explicit fixture rules; rejection precedes manual review."""
    data, reasons = (deepcopy(state), [])
    if not data["inventory"]["available"]:
        reasons.append("insufficient_stock")
    if data["pricing"]["total_cents"] > data["order"]["budget_cents"]:
        reasons.append("over_budget")
    if reasons:
        decision = "rejected"
    elif data["pricing"]["total_cents"] > catalog()["manual_review_threshold_cents"]:
        decision, reasons = ("review", ["high_value_order"])
    else:
        decision = "approved"
    data["policy"] = {"decision": decision, "reasons": reasons}
    return data


def receipt(state, decision, next_action):
    return {
        "order_id": state["order"].get("id"),
        "decision": decision,
        "total_cents": state.get("pricing", {}).get("total_cents"),
        "currency": state["order"].get("currency"),
        "reasons": state.get("policy", {}).get(
            "reasons", state["validation"]["issues"]
        ),
        "next_action": next_action,
    }


@toolkit.tool
def approve_order(state: dict) -> dict:
    """Return a proposed shipment instruction; perform no external side effect."""
    return receipt(state, "approved", "prepare_shipment")


@toolkit.tool
def review_order(state: dict) -> dict:
    """Return a human-review instruction without contacting anyone."""
    return receipt(state, "review", "request_human_approval")


@toolkit.tool
def reject_order(state: dict) -> dict:
    """Return a rejection instruction without contacting anyone."""
    return receipt(state, "rejected", "notify_customer")


import agentic_systems as toolkit

skill_intake = toolkit.skill(name="intake", tools=[normalize_order, validate_order])
skill_pricing = toolkit.skill(name="pricing", tools=[price_order])
skill_inventory = toolkit.skill(name="inventory", tools=[check_inventory])
skill_policy = toolkit.skill(name="policy", tools=[assess_policy])
skill_approval = toolkit.skill(name="approval", tools=[approve_order])
skill_review = toolkit.skill(name="review", tools=[review_order])
skill_rejection = toolkit.skill(name="rejection", tools=[reject_order])
import pydantic
import agentic_systems as toolkit


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
    return {"state": data.model_dump(mode="json", exclude_unset=True)}


def after_policy(data):
    return {"approved": "approve", "review": "review", "rejected": "reject"}[
        data.policy["decision"]
    ]


def build_system():
    intake_graph = toolkit.Graph(State)
    def normalize_step(state):
        return normalize_order.run(as_state(state))
    intake_graph.add_node(
        "normalize", normalize_step
    )
    def validate_step(state):
        return validate_order.run(as_state(state))
    intake_graph.add_node(
        "validate", validate_step
    )
    intake_graph.add_edge(toolkit.START, "normalize")
    intake_graph.add_edge("normalize", "validate")
    intake_graph.add_edge("validate", toolkit.END)
    intake = toolkit.Agent("intake", graph=intake_graph, skills=(skill_intake,))
    agents = {"intake": intake}
    for name, operation, schema, capability in (
        ("pricing", price_order, Price, skill_pricing),
        ("inventory", check_inventory, Stock, skill_inventory),
        ("policy", assess_policy, State, skill_policy),
        ("approve", approve_order, Receipt, skill_approval),
        ("review", review_order, Receipt, skill_review),
        ("reject", reject_order, Receipt, skill_rejection),
    ):
        graph = toolkit.Graph(State, output_schema=schema)
        def node_step(state, operation=operation):
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


from copy import deepcopy
import json
from pathlib import Path
import agentic_systems as toolkit


def load_cases():
    return [
        {
            "name": "approve",
            "input": {
                "order": {
                    "id": "PO-001",
                    "currency": "MXN",
                    "country": "MX",
                    "budget_cents": 80000,
                    "items": [{"sku": "KEYBOARD", "quantity": 2}],
                }
            },
            "expected": {
                "ok": True,
                "data": {
                    "order_id": "PO-001",
                    "decision": "approved",
                    "total_cents": 75000,
                    "currency": "MXN",
                    "reasons": [],
                    "next_action": "prepare_shipment",
                },
            },
        },
        {
            "name": "budget",
            "input": {
                "order": {
                    "id": "PO-002",
                    "currency": "MXN",
                    "country": "MX",
                    "budget_cents": 60000,
                    "items": [{"sku": "KEYBOARD", "quantity": 2}],
                }
            },
            "expected": {
                "ok": True,
                "data": {
                    "order_id": "PO-002",
                    "decision": "rejected",
                    "total_cents": 75000,
                    "currency": "MXN",
                    "reasons": ["over_budget"],
                    "next_action": "notify_customer",
                },
            },
        },
        {
            "name": "stock",
            "input": {
                "order": {
                    "id": "PO-003",
                    "currency": "MXN",
                    "country": "MX",
                    "budget_cents": 2000000,
                    "items": [{"sku": "MONITOR", "quantity": 4}],
                }
            },
            "expected": {
                "ok": True,
                "data": {
                    "order_id": "PO-003",
                    "decision": "rejected",
                    "total_cents": 1005000,
                    "currency": "MXN",
                    "reasons": ["insufficient_stock"],
                    "next_action": "notify_customer",
                },
            },
        },
        {
            "name": "review",
            "input": {
                "order": {
                    "id": "PO-004",
                    "currency": "MXN",
                    "country": "MX",
                    "budget_cents": 300000,
                    "items": [{"sku": "MONITOR", "quantity": 1}],
                }
            },
            "expected": {
                "ok": True,
                "data": {
                    "order_id": "PO-004",
                    "decision": "review",
                    "total_cents": 255000,
                    "currency": "MXN",
                    "reasons": ["high_value_order"],
                    "next_action": "request_human_approval",
                },
            },
        },
        {
            "name": "invalid",
            "input": {
                "order": {
                    "id": "PO-005",
                    "currency": "MXN",
                    "country": "MX",
                    "budget_cents": 80000,
                    "items": [{"sku": "KEYBOARD", "quantity": 0}],
                }
            },
            "expected": {
                "ok": True,
                "data": {
                    "order_id": "PO-005",
                    "decision": "rejected",
                    "total_cents": None,
                    "currency": "MXN",
                    "reasons": ["invalid_quantity"],
                    "next_action": "notify_customer",
                },
            },
        },
        {
            "name": "duplicate_lines",
            "input": {
                "order": {
                    "id": "PO-006",
                    "currency": "MXN",
                    "country": "US",
                    "budget_cents": 2000000,
                    "items": [
                        {"sku": "DOCK", "quantity": 3},
                        {"sku": "DOCK", "quantity": 3},
                    ],
                }
            },
            "expected": {
                "ok": True,
                "data": {
                    "order_id": "PO-006",
                    "decision": "rejected",
                    "total_cents": 732000,
                    "currency": "MXN",
                    "reasons": ["insufficient_stock"],
                    "next_action": "notify_customer",
                },
            },
        },
        {
            "name": "inventory_failure",
            "input": {
                "order": {
                    "id": "PO-007",
                    "currency": "MXN",
                    "country": "MX",
                    "budget_cents": 80000,
                    "items": [{"sku": "KEYBOARD", "quantity": 2}],
                },
                "simulate_inventory_failure": True,
            },
            "expected": {"ok": False},
        },
    ]


def check_tree(output):
    nodes = list(output.walk())
    assert len({n.execution_id for n in nodes}) == len(nodes)
    for node in nodes:
        for child in node.children:
            assert child.parent_execution_id == node.execution_id
    events = [e for n in nodes for e in n.tool_events]
    assert len({e.id for e in events}) == len(events)
    toolkit.RunResult(**json.loads(json.dumps(output.to_dict(), allow_nan=False)))


def trace(output):
    return [
        {"step": n.meta["name"], "ok": n.ok, "output": n.data}
        for n in output.walk()
        if n.meta.get("kind") == "action"
    ]


def verify():
    blocked_before = blocked_attempts()
    unit = build_system()
    prepared = unit.compile()
    cases = load_cases()
    rows = []
    for case in cases:
        payload = deepcopy(case["input"])
        output = prepared.run(payload)
        assert payload == case["input"]
        check_tree(output)
        assert output.ok == case["expected"]["ok"], output.to_dict()
        if output.ok:
            assert output.data == case["expected"]["data"], output.to_dict()
        events = [e for n in output.walk() for e in n.tool_events]
        names = {e.name for e in events}
        if case["name"] == "invalid":
            assert names == {"normalize_order", "validate_order", "reject_order"}
        elif case["name"] == "inventory_failure":
            assert names == {
                "normalize_order",
                "validate_order",
                "price_order",
                "check_inventory",
            }
            assert any((e.name == "price_order" and e.ok for e in events))
            assert any((e.name == "check_inventory" and (not e.ok) for e in events))
            assert any(
                (
                    "controlled_inventory_unavailable" in str(n.errors)
                    for n in output.walk()
                )
            )
        else:
            terminal = {
                "approved": "approve_order",
                "review": "review_order",
                "rejected": "reject_order",
            }
            assert names == {
                "normalize_order",
                "validate_order",
                "price_order",
                "check_inventory",
                "assess_policy",
                terminal[output.data["decision"]],
            }
        rows.append(
            {
                "name": case["name"],
                "input": case["input"],
                "passed": True,
                "expected": case["expected"],
                "process": trace(output),
                "output": output.data,
                "ok": output.ok,
                "result": output.to_dict(),
            }
        )
    accepted = [case for case in cases if case["expected"]["ok"]]
    episode_graph = toolkit.Graph(State, output_schema=Receipt)
    episode_graph.add_node("orders", unit)
    episode_graph.add_edge(toolkit.START, "orders")
    episode_graph.add_edge("orders", toolkit.END)
    episode = toolkit.Environment(
        "orders", graph=episode_graph, records=tuple((c["input"] for c in accepted))
    ).run(timeout_s=None)
    assert episode.ok and episode.data["outputs"] == [
        c["expected"]["data"] for c in accepted
    ]
    assert episode.data["summary"]["state"] == {"processed": len(accepted)}
    assert len(episode.data["history"]) == len(accepted)
    all_ids = {node.execution_id for node in episode.walk()}
    for transition in episode.data["history"]:
        assert transition["execution_id"] in all_ids
    check_tree(episode)
    judged = toolkit.Eval("order_contract", unit, tuple(accepted)).run(
        timeout_s=None
    )
    assert (
        judged.ok
        and judged.data["passed"] == len(accepted)
        and (judged.data["failed"] == 0)
    )
    check_tree(judged)
    wrong = deepcopy(accepted[0])
    wrong["expected"]["data"]["total_cents"] += 1
    negative = toolkit.Eval("wrong_total", unit, (wrong,)).run()
    assert not negative.ok and negative.data["failed"] == 1
    target_id = negative.data["cases"][0]["execution_id"]
    assert next((node for node in negative.walk() if node.execution_id == target_id)).ok
    check_tree(negative)
    attempts = blocked_attempts() - blocked_before
    assert attempts == 0
    return {
        "orchestration": "langgraph",
        "passed": True,
        "target_version": toolkit.__version__,
        "sdk_version": toolkit.__version__,
        "inference_requests": 0,
        "blocked_network_or_subprocess_attempts": attempts,
        "cases_passed": len(rows),
        "cases": rows,
        "topology": prepared.inspect(),
        "environment": episode.to_dict(),
        "evaluation": judged.to_dict(),
        "negative_control": negative.to_dict(),
    }


def run():
    return verify()
