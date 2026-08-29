from __future__ import annotations

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from agentic_systems.schemas import ContractExecutionBudget
from scripts.semantic_e2e_application import semantic_judge_execution_budget


def test_contract_budget_derives_portable_limits_for_one_required_tool() -> None:
    budget = ContractExecutionBudget(required_tool_calls=1)

    assert budget.minimum_turns == 5
    assert budget.effective_max_turns == 5
    assert budget.effective_max_tool_calls == 1


@given(required_tool_calls=st.integers(min_value=0, max_value=100))
def test_contract_budget_scales_with_required_tool_count(
    required_tool_calls: int,
) -> None:
    budget = ContractExecutionBudget(required_tool_calls=required_tool_calls)

    assert budget.minimum_turns == required_tool_calls + 4
    assert budget.effective_max_turns >= budget.minimum_turns
    assert budget.effective_max_tool_calls == required_tool_calls


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_turns", 4),
        ("max_tool_calls", 0),
    ],
)
def test_contract_budget_rejects_impossible_explicit_limits(
    field: str, value: int
) -> None:
    with pytest.raises(ValidationError):
        ContractExecutionBudget(required_tool_calls=1, **{field: value})


def test_contract_budget_round_trips_without_semantic_loss() -> None:
    budget = ContractExecutionBudget(required_tool_calls=2, max_turns=8)

    restored = ContractExecutionBudget.model_validate_json(budget.model_dump_json())

    assert restored == budget
    assert restored.minimum_turns == 6
    assert "minimum_turns" not in restored.model_dump()


def test_semantic_judge_budget_uses_validated_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTIC_SYSTEMS_SEMANTIC_JUDGE_MAX_TURNS", "7")

    budget = semantic_judge_execution_budget(required_tool_calls=1)

    assert budget.effective_max_turns == 7
    assert budget.effective_max_tool_calls == 1


def test_semantic_judge_budget_rejects_too_small_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTIC_SYSTEMS_SEMANTIC_JUDGE_MAX_TURNS", "3")

    with pytest.raises(ValidationError, match="contract-derived minimum"):
        semantic_judge_execution_budget(required_tool_calls=1)
