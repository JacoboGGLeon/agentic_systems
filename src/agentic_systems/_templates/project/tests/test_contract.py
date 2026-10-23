from copy import deepcopy

import pytest
from agentic_systems import Limits
from order_fulfillment import build_system, load_cases, verify
from order_fulfillment.verification import check_tree


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_order_challenge_contracts_episodes_evals_and_evidence(backend):
    report = verify(backend)
    assert report["passed"] and report["cases_passed"] == 7
    assert report["evaluation"]["data"]["passed"] == 6
    assert len(report["environment"]["children"]) == 6


@pytest.mark.parametrize("backend", ["native", "langgraph"])
@pytest.mark.parametrize("quantity", [True, -1, 0, "2"])
def test_invalid_quantities_never_reach_stock_or_pricing(backend, quantity):
    payload = deepcopy(load_cases()[0]["input"])
    payload["order"]["items"][0]["quantity"] = quantity
    result = build_system(backend).run(payload)
    assert result.ok and result.data["decision"] == "rejected"
    assert "invalid_quantity" in result.data["reasons"]
    assert {e.name for n in result.walk() for e in n.tool_events} == {
        "normalize_order", "validate_order", "reject_order"
    }
    check_tree(result)


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_rejection_precedes_high_value_review_and_shared_limit_applies(backend):
    payload = deepcopy(load_cases()[3]["input"])
    payload["order"]["budget_cents"] = 1
    result = build_system(backend).run(payload)
    assert result.ok and result.data["decision"] == "rejected"
    assert result.data["reasons"] == ["over_budget"]
    limited = build_system(backend).run(payload, limits=Limits(max_actions=2))
    assert not limited.ok and limited.meta["actions_observed"] == 2
    assert "assess_policy" not in {e.name for n in limited.walk() for e in n.tool_events}
