import pytest

from agentic_systems import (
    AgentContract,
    RunPolicy,
)
from agentic_systems.contracts import ValidationResult


def test_contract_policy_and_validation_error_paths():
    validation = ValidationResult(ok=True)
    validation.add("warn", "warning only", severity="warning")
    assert validation.ok is True
    validation.add("err", "error")
    with pytest.raises(ValueError, match="Validation failed"):
        validation.raise_if_failed()

    assert AgentContract(failure_policy=None).failure_policy == "no_unresolved"
    assert AgentContract(failure_policy=True).failure_policy == "no_unresolved"
    assert AgentContract(failure_policy=False).failure_policy == "allow"
    assert (
        AgentContract(require_no_unresolved_tool_failures=False).failure_policy
        == "allow"
    )
    allow = AgentContract(failure_policy="allow")
    assert allow.require_no_unresolved_tool_failures is False

    with pytest.raises(ValueError, match="Unknown run mode"):
        RunPolicy.for_mode("unknown")
    merged = RunPolicy(max_turns=1).merge(RunPolicy(max_tokens=33))
    assert merged.max_turns == 1 and merged.max_tokens == 33
