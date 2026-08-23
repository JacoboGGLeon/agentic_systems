from __future__ import annotations

import importlib

import pytest
from pydantic import ValidationError

from agentic_systems.contracts import (
    AgentContract,
    ContractPolicySpec,
    RunPolicy,
    resolve_policy,
    validate_contract_policy,
)

system_module = importlib.import_module("agentic_systems.system")


def test_contract_policy_resolution_and_validation():
    with pytest.raises(ValidationError):
        RunPolicy(max_turns=0)
    with pytest.raises(ValidationError):
        RunPolicy(max_tool_calls=-1)
    assert RunPolicy(max_tool_calls=0).max_tool_calls == 0
    with pytest.raises(ValidationError):
        RunPolicy(max_repairs=-1)
    with pytest.raises(ValidationError):
        RunPolicy(temperature=3)
    with pytest.raises(ValidationError):
        RunPolicy(tool_choice=" ")
    with pytest.raises(ValidationError):
        AgentContract(tool_expectation=123)
    assert (
        resolve_policy(
            mode="fast", agent_policy={"max_turns": 5}, run_config={"max_turns": 2}
        ).max_turns
        == 2
    )

    spec = ContractPolicySpec(
        name="spec",
        contract={"must_call": ["a"]},
        policy={"max_tool_calls": 1},
        tags=["t"],
        metadata={"m": 1},
    )
    assert ContractPolicySpec.coerce(spec) is spec
    assert ContractPolicySpec.coerce({"name": "dict-spec"}).name == "dict-spec"
    assert spec.agent_kwargs()["contract"].must_call == ["a"]
    assert spec.describe()["name"] == "spec"
    assert spec.to_dict()["name"] == "spec"
    with pytest.raises(ValidationError):
        ContractPolicySpec(name=" ")

    ok = validate_contract_policy(
        AgentContract(
            must_call=["a"],
            tool_expectation={
                "all_of": ["a"],
                "exactly": ["a"],
                "min_count": 1,
                "any_of": ["a"],
            },
        ),
        RunPolicy(max_tool_calls=1),
        available_tools={"a"},
    )
    assert ok.ok is True

    bad = validate_contract_policy(
        AgentContract(
            must_call=["missing"],
            must_not_call=["forbidden"],
            tool_expectation={"all_of": ["missing"], "min_count": 3},
        ),
        RunPolicy(max_tool_calls=1),
        available_tools={"a"},
    )
    codes = {issue.code for issue in bad.issues}
    assert "contract_references_unknown_tool" in codes
    assert "policy_tool_budget_too_small" in codes
