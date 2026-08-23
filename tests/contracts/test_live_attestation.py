from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import ValidationError
import pytest

from agentic_systems.schemas import (
    LiveAttestation,
    LIVE_SCENARIO_NAMES,
    LiveMatrixCase,
    LiveScenarioEvidence,
    validate_live_attestation,
)


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
COMMIT = "a" * 40
WHEEL = "b" * 64


def _case(framework: str, *, ok: bool = True) -> LiveMatrixCase:
    return LiveMatrixCase(
        provider="vllm-runtime",
        framework=framework,
        model="qwen",
        ok=ok,
        scenarios=tuple(
            LiveScenarioEvidence(
                name=name,
                ok=ok,
                invariant_issues=() if ok else ("failed",),
                details={"tokens": 4},
            )
            for name in LIVE_SCENARIO_NAMES
        ),
        usage={"total_tokens": 4},
        errors=() if ok else ({"code": "provider"},),
    )


def _attestation(cases: tuple[LiveMatrixCase, ...]) -> LiveAttestation:
    return LiveAttestation(
        created_at=NOW,
        commit_sha=COMMIT.upper(),
        wheel_sha256=WHEEL.upper(),
        wheel_filename="agentic_systems-2.0.1-py3-none-any.whl",
        python_version="3.12.5",
        environment={"cuda": "12.4", "gpu": "T4", "vllm": "0.9"},
        cases=cases,
    )


def test_live_attestation_accepts_exact_fresh_release_evidence() -> None:
    frameworks = ("native", "langgraph", "openai-agents", "strands")
    evidence = _attestation(tuple(_case(item) for item in frameworks))
    validate_live_attestation(
        evidence,
        expected_commit_sha=COMMIT,
        expected_wheel_sha256=WHEEL,
        expected_pairs={("vllm-runtime", item) for item in frameworks},
        now=NOW + timedelta(hours=1),
    )
    assert evidence.commit_sha == COMMIT
    assert evidence.wheel_sha256 == WHEEL
    assert LiveAttestation.model_validate_json(evidence.model_dump_json()) == evidence


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("commit_sha", "not-a-sha", "commit_sha"),
        ("wheel_sha256", "short", "wheel_sha256"),
    ],
)
def test_live_attestation_rejects_invalid_hashes(
    field: str, value: str, message: str
) -> None:
    payload = _attestation((_case("native"),)).model_dump()
    payload[field] = value
    with pytest.raises(ValidationError, match=message):
        LiveAttestation.model_validate(payload)


def test_live_attestation_reports_every_release_mismatch() -> None:
    evidence = _attestation(
        (
            _case("native", ok=False),
            _case("native"),
            _case("unexpected"),
        )
    )
    with pytest.raises(ValueError) as captured:
        validate_live_attestation(
            evidence,
            expected_commit_sha="c" * 40,
            expected_wheel_sha256="d" * 64,
            expected_pairs={
                ("vllm-runtime", "native"),
                ("vllm-runtime", "langgraph"),
            },
            now=NOW + timedelta(hours=25),
        )
    message = str(captured.value)
    assert "commit SHA" in message
    assert "wheel SHA-256" in message
    assert "age window" in message
    assert "duplicate" in message
    assert "missing cases" in message
    assert "unexpected cases" in message
    assert "failed cases" in message


def test_live_attestation_rejects_future_evidence() -> None:
    evidence = _attestation((_case("native"),))
    with pytest.raises(ValueError, match="age window"):
        validate_live_attestation(
            evidence,
            expected_commit_sha=COMMIT,
            expected_wheel_sha256=WHEEL,
            expected_pairs={("vllm-runtime", "native")},
            now=NOW - timedelta(seconds=1),
        )


def test_live_attestation_rejects_incomplete_scenarios_and_vllm_identity() -> None:
    incomplete = _case("native").model_copy(
        update={
            "model": "",
            "scenarios": (LiveScenarioEvidence(name="agent", ok=True),),
        }
    )
    evidence = _attestation((incomplete,)).model_copy(
        update={"environment": {"cuda": None, "gpu": "", "vllm": None}}
    )
    with pytest.raises(ValueError) as captured:
        validate_live_attestation(
            evidence,
            expected_commit_sha=COMMIT,
            expected_wheel_sha256=WHEEL,
            expected_pairs={("vllm-runtime", "native")},
            now=NOW,
            required_environment_keys=("cuda", "gpu", "vllm"),
            require_model=True,
        )
    message = str(captured.value)
    assert "missing scenarios" in message
    assert "live environment is incomplete" in message
    assert "does not identify the model" in message
