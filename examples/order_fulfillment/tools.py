"""Local fixtures only. Prices are integer cents; no orders are placed."""

from copy import deepcopy
import json
from pathlib import Path

import agentic_systems as toolkit


def catalog():
    return json.loads((Path(__file__).parent / "fixtures/catalog.json").read_text(encoding="utf-8"))


@toolkit.tool
def normalize_order(state: dict) -> dict:
    """Normalize text fields without coercing quantities, budgets or types."""
    data = deepcopy(state)
    order = data.get("order")
    if isinstance(order, dict):
        for key in ("id", "currency", "country"):
            if isinstance(order.get(key), str):
                order[key] = order[key].strip()
        for item in order.get("items", []) if isinstance(order.get("items"), list) else []:
            if isinstance(item, dict) and isinstance(item.get("sku"), str):
                item["sku"] = item["sku"].strip().upper()
    return data


@toolkit.tool
def validate_order(state: dict) -> dict:
    """Return business validation issues without running pricing on invalid orders."""
    data, rules = deepcopy(state), catalog()
    order, issues = data.get("order"), []
    if not isinstance(order, dict):
        order = {}
        issues.append("invalid_order")
    if not isinstance(order.get("id"), str) or not order.get("id"):
        issues.append("invalid_id")
    if order.get("currency") != rules["currency"]:
        issues.append("unsupported_currency")
    if not isinstance(order.get("country"), str) or order.get("country") not in rules["shipping_cents"]:
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
            if not isinstance(item.get("sku"), str) or item.get("sku") not in rules["products"]:
                issues.append("unknown_sku")
            if type(item.get("quantity")) is not int or item["quantity"] < 1:
                issues.append("invalid_quantity")
    data["order"] = order
    data["validation"] = {"valid": not issues, "issues": list(dict.fromkeys(issues))}
    return data


@toolkit.tool
def price_order(state: dict) -> dict:
    """Price every order line and shipping using one local catalog snapshot."""
    data, rules = deepcopy(state), catalog()
    order = data["order"]
    subtotal = sum(rules["products"][line["sku"]]["unit_price_cents"] * line["quantity"]
                   for line in order["items"])
    shipping = rules["shipping_cents"][order["country"]]
    data["pricing"] = {"subtotal_cents": subtotal, "shipping_cents": shipping,
                       "total_cents": subtotal + shipping}
    return data


@toolkit.tool
def check_inventory(state: dict) -> dict:
    """Aggregate duplicate SKU lines before comparing requested quantities to stock."""
    if state.get("simulate_inventory_failure"):
        raise RuntimeError("controlled_inventory_unavailable")
    data, rules, requested = deepcopy(state), catalog(), {}
    for line in data["order"]["items"]:
        requested[line["sku"]] = requested.get(line["sku"], 0) + line["quantity"]
    shortages = [sku for sku, quantity in requested.items()
                 if quantity > rules["products"][sku]["stock"]]
    data["inventory"] = {"available": not shortages, "shortages": shortages, "requested": requested}
    return data


@toolkit.tool
def assess_policy(state: dict) -> dict:
    """Apply explicit fixture rules; rejection precedes manual review."""
    data, reasons = deepcopy(state), []
    if not data["inventory"]["available"]:
        reasons.append("insufficient_stock")
    if data["pricing"]["total_cents"] > data["order"]["budget_cents"]:
        reasons.append("over_budget")
    if reasons:
        decision = "rejected"
    elif data["pricing"]["total_cents"] > catalog()["manual_review_threshold_cents"]:
        decision, reasons = "review", ["high_value_order"]
    else:
        decision = "approved"
    data["policy"] = {"decision": decision, "reasons": reasons}
    return data


def receipt(state, decision, next_action):
    return {"order_id": state["order"].get("id"), "decision": decision,
            "total_cents": state.get("pricing", {}).get("total_cents"),
            "currency": state["order"].get("currency"),
            "reasons": state.get("policy", {}).get("reasons", state["validation"]["issues"]),
            "next_action": next_action}


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
