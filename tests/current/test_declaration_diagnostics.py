"""Invalid declarations explain the violated contract before execution."""
from types import SimpleNamespace
import pytest
from agentic_systems._contracts import _validate_contract


@pytest.mark.parametrize("contract,kind,message", [
    ({"tool_expectation": {"all_of": ["missing"]}}, ValueError, "Contract references unavailable Tools"),
    ({"tool_expectation": {"all_of": ["a"], "forbidden": ["a"]}}, ValueError, "Contradictory required/allowed/forbidden Tools"),
    ({"tool_expectation": {"all_of": ["a"], "allowed": ["b"]}}, ValueError, "Contradictory required/allowed/forbidden Tools"),
    ({"tool_expectation": {"any_of": ["a"], "forbidden": ["a"]}}, ValueError, "No any_of Tool can satisfy this contract"),
    ({"tool_expectation": {"any_of": ["a"], "allowed": ["b"]}}, ValueError, "No any_of Tool can satisfy this contract"),
    ({"tool_expectation": {"min_count": 2}}, ValueError, "Contract exceeds the actor Tool budget"),
    ({"tool_expectation": {"all_of": ["a", "b"]}}, ValueError, "Required Tools exceed the actor budget"),
    ({"completion": "unknown"}, ValueError, "Unknown exact completion mode"),
    ({"failure_policy": "unknown"}, ValueError, "Unknown exact failure_policy"),
    ({"expected_output": []}, TypeError, "expected_output must be a dictionary"),
    ({"expected_tool_outputs": []}, TypeError, "expected_tool_outputs must be a dictionary"),
    ({"expected_tool_outputs": {"missing": {}}}, ValueError, "expected_tool_outputs requires available Tool names and dictionary expectations"),
    ({"expected_tool_outputs": {"a": []}}, ValueError, "expected_tool_outputs requires available Tool names and dictionary expectations"),
])
def test_rejected_declaration_explains_exact_constraint(contract, kind, message):
    with pytest.raises(kind) as caught:
        _validate_contract(contract, ("a", "b"), SimpleNamespace(max_tool_calls=1))
    assert str(caught.value) == message


@pytest.mark.parametrize("field", ["all_of", "any_of", "allowed", "forbidden"])
@pytest.mark.parametrize("value", ["a", [1]])
def test_tool_references_require_lists_of_names(field, value):
    with pytest.raises(TypeError) as caught:
        _validate_contract({"tool_expectation": {field: value}}, ("a",))
    assert str(caught.value) == field + " requires a list of Tool names"


@pytest.mark.parametrize("completion", ["default", "when_required_tools_satisfied", "always_finalize"])
@pytest.mark.parametrize("failure_policy", ["allow", "no_unresolved", "fail_fast"])
def test_valid_declaration_retains_all_decisions(completion, failure_policy):
    contract = {"completion": completion, "failure_policy": failure_policy,
        "tool_expectation": {"all_of": ["a"], "any_of": ["a", "b"], "allowed": ["a"], "forbidden": ["b"], "min_count": 1},
        "expected_output": {"amount": 4}, "expected_tool_outputs": {"a": {"amount": 4}},
        "input_schema": {"type": "object"}, "output_schema": {"type": "object"}}
    assert _validate_contract(contract, ("a", "b"), SimpleNamespace(max_tool_calls=1)) == contract
