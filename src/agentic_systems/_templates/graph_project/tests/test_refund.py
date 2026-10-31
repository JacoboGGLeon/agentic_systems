"""Business contracts for the generated application, without inference."""

import agentic_systems as toolkit
from order_fulfillment.application import CASE, build_system, check_result


def test_refund_has_business_evidence_and_roundtrips():
    result = build_system().run(CASE)
    assert check_result(result), result.to_dict()
    assert result.usage.get("inference_requests", 0) == 0
    restored = toolkit.RunResult(**result.to_dict())
    assert restored.check_invariants().ok
    assert restored.data == result.data


def test_missing_business_input_is_not_repaired_with_a_default():
    invalid = {key: value for key, value in CASE.items() if key != "amount"}
    result = build_system().run(invalid)
    assert not result.ok and result.errors
