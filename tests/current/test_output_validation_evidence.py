"""Output validation retains structured business data and actionable failure evidence."""
import pytest
from agentic_systems import RunResult
from agentic_systems._contracts import _check_output
from agentic_systems._results import _Event


def test_valid_text_json_becomes_business_data():
    result = _check_output(RunResult(text='{"amount": 4}'), {"output_schema": {"type": "object"}})
    assert result.ok and result.data == {"amount": 4}
    assert result.errors == ()


@pytest.mark.parametrize("text,issues", [
    ("invalid", [{"code": "invalid_structured_output", "message": "Model text is not JSON"}]),
    ("[]", [{"code": "output_schema_mismatch", "message": "Expected a JSON object"}]),
])
def test_invalid_text_retains_original_error_and_exact_validation_evidence(text, issues):
    previous = {"code": "previous", "message": "provider detail"}
    result = _check_output(RunResult(text=text, errors=(previous,)), {"output_schema": {"type": "object"}})
    assert result.ok is False
    assert result.errors == (previous, *issues)
    assert result.validation == {"ok": False, "issues": issues}
    assert result.text == text


def test_schema_error_retains_nested_business_path():
    result = _check_output(RunResult(data={"amount": "wrong"}), {"output_schema": {
        "type": "object", "properties": {"amount": {"type": "integer"}}}})
    issues = [{"code": "output_schema_mismatch", "message": "'wrong' is not of type 'integer'", "path": ["amount"]}]
    assert result.errors == tuple(issues)
    assert result.validation == {"ok": False, "issues": issues}
    assert result.ok is False


def test_forbidden_nested_tool_retains_failure_evidence():
    child = RunResult(tool_events=(_Event("event", "charge"),))
    result = _check_output(RunResult(children=(child,)), {"tool_expectation": {"forbidden": ["charge"]}})
    issues = [{"code": "forbidden_tool", "message": "Observed a forbidden Tool"}]
    assert result.ok is False and result.errors == tuple(issues)
    assert result.validation == {"ok": False, "issues": issues}


@pytest.mark.parametrize("ok", [True, False])
@pytest.mark.parametrize("policy", ["allow", "no_unresolved"])
def test_allowed_error_identity_metadata_requires_success_and_explicit_policy(ok, policy):
    result = _check_output(RunResult(execution_id="root", ok=ok, meta={"business": 4},
        children=(RunResult(execution_id="child"),)), {"failure_policy": policy})
    expected = {"business": 4}
    if ok and policy == "allow":
        expected["allowed_error_ids"] = ["root", "child"]
    assert result.meta == expected
    assert result.ok is ok
