import json

import pytest

from agentic_systems import RunResult
from agentic_systems.contracts import ValidationResult
from agentic_systems.tools import ToolEvent


def _event(event_id: str, *, name: str = "lookup", ok: bool, error=None) -> ToolEvent:
    return ToolEvent(
        id=event_id,
        name=name,
        input={"id": 1},
        output={"data": {"value": 1}},
        ok=ok,
        error=error,
    )


def _codes(validation: ValidationResult) -> set[str]:
    return {issue.code for issue in validation.issues}


def test_final_data_and_text_are_compatible_projections() -> None:
    result = RunResult(
        text="Human summary",
        data={"record_id": 7, "evidence": ["tool:lookup"]},
        final={"answer": "Approved"},
    )

    assert result.check_invariants().ok is True
    assert result.final == {"answer": "Approved"}
    assert result.data["record_id"] == 7
    assert result.text == "Human summary"


def test_failed_validation_forces_failure_and_adds_deduplicated_error() -> None:
    validation = ValidationResult(ok=True)
    validation.add(
        "missing_evidence", "Required evidence was not produced.", path="data.evidence"
    )

    result = RunResult(text="answer", validation=validation.to_dict())
    result.apply_validation(validation)

    assert result.ok is False
    assert result.validation["ok"] is False
    validation_errors = [
        error for error in result.errors if error["code"] == "validation_failed"
    ]
    assert validation_errors == [
        {
            "code": "validation_failed",
            "message": "Required evidence was not produced.",
            "path": "data.evidence",
            "validation_code": "missing_evidence",
            "meta": {},
        }
    ]


def test_validation_warning_preserves_success_without_error() -> None:
    validation = ValidationResult(ok=True)
    validation.add("review", "Review recommended.", severity="warning")

    result = RunResult(text="answer").apply_validation(validation)

    assert result.ok is True
    assert result.errors == []
    assert result.validation["issues"][0]["severity"] == "warning"


def test_compatibility_validation_payload_is_preserved_and_controls_success() -> None:
    legacy = {"ok": False, "issues": [{"code": "legacy_failure"}]}
    result = RunResult(text="legacy", validation=legacy)

    assert result.ok is False
    assert result.validation == legacy
    assert result.errors[-1]["message"] == "legacy_failure"
    assert RunResult.model_validate(result.to_dict()).validation == legacy

    unstructured = RunResult(text="legacy", validation={"issues": ["plain failure"]})
    assert unstructured.ok is False
    assert unstructured.errors[-1]["message"] == "plain failure"


def test_mutated_validation_contradictions_are_reported_clearly() -> None:
    result = RunResult(text="answer")
    result.validation = {"ok": False, "issues": []}
    result.ok = True
    assert "success_with_failed_validation" in _codes(result.check_invariants())

    result.validation = {
        "ok": True,
        "issues": [
            {
                "code": "bad",
                "message": "bad",
                "severity": "error",
                "path": None,
                "meta": {},
            }
        ],
    }
    assert "validation_status_mismatch" in _codes(result.check_invariants())


def test_partial_tool_failure_distinguishes_recovered_and_unresolved() -> None:
    recovered = RunResult(
        text="completed after retry",
        tool_events=[
            _event("failed", ok=False, error={"message": "temporary"}),
            _event("recovery", ok=True),
        ],
    )
    recovered_error = next(
        error for error in recovered.errors if error["code"] == "tool_failed"
    )
    assert recovered_error["resolved"] is True
    assert recovered_error["recovered_by_tool_event_id"] == "recovery"
    assert recovered.trace()["recovered_tool_error_count"] == 1
    assert recovered.trace()["unresolved_failed_tool_count"] == 0

    unresolved = RunResult(
        text="partial answer",
        tool_events=[
            _event("unresolved", ok=False, error={"message": "allowed partial failure"})
        ],
    )
    invariant_check = unresolved.check_invariants()
    assert invariant_check.ok is True
    assert "success_with_unresolved_tool_failure" in _codes(invariant_check)
    assert unresolved.raise_if_inconsistent() is unresolved


def test_error_and_tool_event_contradictions_are_detected() -> None:
    result = RunResult(
        text="answer",
        tool_events=[
            _event("duplicate", ok=True, error={"message": "impossible"}),
            _event("duplicate", ok=True),
        ],
    )
    validation = result.check_invariants()

    assert validation.ok is False
    assert {"duplicate_tool_event_id", "successful_tool_event_with_error"} <= _codes(
        validation
    )
    with pytest.raises(ValueError, match="duplicate_tool_event_id"):
        result.raise_if_inconsistent()


def test_usage_must_be_non_negative_and_error_is_actionable() -> None:
    result = RunResult(text="answer", usage={"input_tokens": -1, "cached": False})
    validation = result.check_invariants()

    assert "negative_usage_value" in _codes(validation)
    with pytest.raises(ValueError, match="input_tokens.*cannot be negative"):
        result.raise_if_inconsistent()


def test_missing_answer_and_failure_evidence_are_warnings() -> None:
    empty_success = RunResult()
    empty_failure = RunResult(ok=False)

    assert "success_without_answer" in _codes(empty_success.check_invariants())
    assert "failure_without_error_evidence" in _codes(empty_failure.check_invariants())
    assert empty_success.check_invariants().ok is True
    assert empty_failure.check_invariants().ok is True


def test_serialization_invariant_and_json_round_trip() -> None:
    result = RunResult(
        text="answer",
        data={"value": 3},
        usage={"requests": 1},
        tool_events=[_event("ok", ok=True)],
    )
    payload = result.to_dict()
    restored = RunResult.model_validate(json.loads(json.dumps(payload)))

    assert restored.to_dict() == payload
    assert restored.check_invariants().ok is True

    non_serializable = RunResult(text="answer", data={"value": object()})
    serialization_check = non_serializable.check_invariants()
    assert "not_json_serializable" in _codes(serialization_check)


def test_reasoning_is_removed_before_first_public_projection_and_round_trip() -> None:
    raw = "<thinking>private chain</thinking>\n\nPublic answer"
    result = RunResult(
        text=raw,
        final={"text": raw},
        ok=False,
        errors=[{"code": "run_failed", "message": raw}],
    )

    assert result.text == "Public answer"
    assert result.final["text"] == "Public answer"
    assert result.errors[0]["message"] == "Public answer"
    assert result.meta["reasoning"] == {
        "present": True,
        "format": "<thinking>",
        "removed_from_public_text": True,
    }
    restored = RunResult.model_validate_json(result.model_dump_json())
    assert restored.normalized() == result.normalized()
    assert "private chain" not in result.model_dump_json()

    result.text = raw
    result.final = {"text": raw}
    result.apply_validation({"ok": True, "issues": []})

    assert result.text == "Public answer"
    assert result.final["text"] == "Public answer"
    assert "private chain" not in result.model_dump_json()


def test_lineage_preserves_status_usage_validation_and_evidence() -> None:
    result = RunResult(
        text="answer",
        data={"evidence": {"source": "lookup"}},
        usage={"total_tokens": 4},
        tool_events=[_event("lookup-1", ok=True)],
        validation={"ok": True, "issues": []},
        meta={"input": {"question": "status?"}},
    )
    lineage = result.lineage(name="invariant-test")
    payload = lineage.to_dict()

    assert payload["ok"] is True
    assert payload["usage"] == {"total_tokens": 4}
    assert payload["validation"] == {"ok": True, "issues": []}
    assert any(
        step["kind"] == "tool" and step["evidence"]["ok"] is True
        for step in payload["steps"]
    )
