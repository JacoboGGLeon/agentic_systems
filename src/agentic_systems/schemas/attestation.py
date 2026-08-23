"""Verifiable evidence produced by protected live runners."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import AwareDatetime, Field, field_validator

from .base import ContractModel, JsonValue

LiveScenarioName = Literal[
    "inspect",
    "completion",
    "agent",
    "tool_calling",
    "structured_error",
    "run_result_round_trip",
]
LIVE_SCENARIO_NAMES: tuple[LiveScenarioName, ...] = (
    "inspect",
    "completion",
    "agent",
    "tool_calling",
    "structured_error",
    "run_result_round_trip",
)

LIVE_ATTESTATION_SCHEMA_VERSION = "agentic_systems.live-attestation.v1"


class LiveScenarioEvidence(ContractModel):
    name: str
    ok: bool
    invariant_issues: tuple[str, ...] = ()
    details: dict[str, JsonValue] = Field(default_factory=dict)


class LiveMatrixCase(ContractModel):
    provider: str
    framework: str
    model: str = ""
    ok: bool
    scenarios: tuple[LiveScenarioEvidence, ...]
    usage: dict[str, JsonValue] = Field(default_factory=dict)
    errors: tuple[dict[str, JsonValue], ...] = ()


class LiveAttestation(ContractModel):
    schema_version: str = LIVE_ATTESTATION_SCHEMA_VERSION
    created_at: AwareDatetime
    commit_sha: str
    wheel_sha256: str
    wheel_filename: str = Field(min_length=1)
    python_version: str = Field(min_length=1)
    environment: dict[str, JsonValue] = Field(default_factory=dict)
    cases: tuple[LiveMatrixCase, ...] = Field(min_length=1)

    @field_validator("commit_sha")
    @classmethod
    def validate_commit_sha(cls, value: str) -> str:
        clean = value.strip().lower()
        if (
            len(clean) < 7
            or len(clean) > 64
            or any(char not in "0123456789abcdef" for char in clean)
        ):
            raise ValueError("commit_sha must contain 7-64 hexadecimal characters")
        return clean

    @field_validator("wheel_sha256")
    @classmethod
    def validate_wheel_sha256(cls, value: str) -> str:
        clean = value.strip().lower()
        if len(clean) != 64 or any(char not in "0123456789abcdef" for char in clean):
            raise ValueError(
                "wheel_sha256 must contain exactly 64 hexadecimal characters"
            )
        return clean


def validate_live_attestation(
    attestation: LiveAttestation,
    *,
    expected_commit_sha: str,
    expected_wheel_sha256: str,
    expected_pairs: set[tuple[str, str]],
    now: datetime | None = None,
    max_age: timedelta = timedelta(hours=24),
    required_environment_keys: tuple[str, ...] = (),
    require_model: bool = False,
) -> None:
    """Reject stale, mismatched, duplicated, incomplete, or failed evidence."""

    errors = [
        *_identity_errors(attestation, expected_commit_sha, expected_wheel_sha256),
        *_freshness_errors(attestation, now=now, max_age=max_age),
        *_case_errors(
            attestation,
            expected_pairs,
            required_environment_keys=required_environment_keys,
            require_model=require_model,
        ),
    ]
    if errors:
        raise ValueError("; ".join(errors))


def _identity_errors(
    attestation: LiveAttestation,
    expected_commit_sha: str,
    expected_wheel_sha256: str,
) -> list[str]:
    errors: list[str] = []
    if attestation.commit_sha != expected_commit_sha.strip().lower():
        errors.append("commit SHA does not match the release candidate")
    if attestation.wheel_sha256 != expected_wheel_sha256.strip().lower():
        errors.append("wheel SHA-256 does not match the release candidate")
    return errors


def _freshness_errors(
    attestation: LiveAttestation,
    *,
    now: datetime | None,
    max_age: timedelta,
) -> list[str]:
    age = (now or datetime.now(timezone.utc)) - attestation.created_at
    if timedelta(0) <= age <= max_age:
        return []
    return ["attestation is outside the accepted age window"]


def _case_errors(
    attestation: LiveAttestation,
    expected_pairs: set[tuple[str, str]],
    *,
    required_environment_keys: tuple[str, ...],
    require_model: bool,
) -> list[str]:
    observed = [(case.provider, case.framework) for case in attestation.cases]
    observed_set = set(observed)
    errors = _matrix_errors(attestation, expected_pairs, observed, observed_set)
    errors.extend(_environment_errors(attestation, required_environment_keys))
    for case in attestation.cases:
        errors.extend(_scenario_errors(case, require_model=require_model))
    return errors


def _matrix_errors(
    attestation: LiveAttestation,
    expected_pairs: set[tuple[str, str]],
    observed: list[tuple[str, str]],
    observed_set: set[tuple[str, str]],
) -> list[str]:
    errors: list[str] = []
    if len(observed_set) != len(observed):
        errors.append("attestation contains duplicate provider/framework cases")
    missing = sorted(expected_pairs - observed_set)
    unexpected = sorted(observed_set - expected_pairs)
    if missing:
        errors.append(f"attestation is missing cases: {missing}")
    if unexpected:
        errors.append(f"attestation contains unexpected cases: {unexpected}")
    failed = sorted(
        (case.provider, case.framework) for case in attestation.cases if not case.ok
    )
    if failed:
        errors.append(f"attestation contains failed cases: {failed}")
    return errors


def _environment_errors(
    attestation: LiveAttestation, required_environment_keys: tuple[str, ...]
) -> list[str]:
    missing = sorted(
        key for key in required_environment_keys if not attestation.environment.get(key)
    )
    return [f"live environment is incomplete: {missing}"] if missing else []


def _scenario_errors(case: LiveMatrixCase, *, require_model: bool) -> list[str]:
    pair = (case.provider, case.framework)
    scenario_names = [scenario.name for scenario in case.scenarios]
    scenario_set = set(scenario_names)
    errors: list[str] = []
    if len(scenario_names) != len(scenario_set):
        errors.append(f"case {pair} contains duplicate scenarios")
    missing = sorted(set(LIVE_SCENARIO_NAMES) - scenario_set)
    unexpected = sorted(scenario_set - set(LIVE_SCENARIO_NAMES))
    if missing:
        errors.append(f"case {pair} is missing scenarios: {missing}")
    if unexpected:
        errors.append(f"case {pair} contains unexpected scenarios: {unexpected}")
    failed = sorted(scenario.name for scenario in case.scenarios if not scenario.ok)
    if failed:
        errors.append(f"case {pair} contains failed scenarios: {failed}")
    if require_model and not case.model:
        errors.append(f"case {pair} does not identify the model")
    return errors


__all__ = [
    "LiveScenarioName",
    "LIVE_ATTESTATION_SCHEMA_VERSION",
    "LIVE_SCENARIO_NAMES",
    "LiveAttestation",
    "LiveMatrixCase",
    "LiveScenarioEvidence",
    "validate_live_attestation",
]
