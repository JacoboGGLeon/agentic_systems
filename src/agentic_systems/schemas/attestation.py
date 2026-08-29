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


SEMANTIC_ATTESTATION_SCHEMA_VERSION = "agentic_systems.semantic-attestation.v1"


class SemanticMatrix(ContractModel):
    providers: tuple[str, ...] = Field(min_length=1)
    frameworks: tuple[str, ...] = Field(min_length=1)


class SemanticSummary(ContractModel):
    total: int = Field(ge=1)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    episodes_total: int = Field(ge=1)
    episodes_passed: int = Field(ge=0)
    episodes_failed: int = Field(ge=0)


class SemanticEpisodeEvidence(ContractModel):
    name: str = Field(min_length=1)
    ok: bool
    candidate: dict[str, JsonValue]
    candidate_usage: dict[str, JsonValue] = Field(default_factory=dict)
    deterministic_validation: dict[str, JsonValue]
    environment_episode: dict[str, JsonValue]
    human_result: str = Field(min_length=1)
    judge: dict[str, JsonValue]
    judge_execution: dict[str, JsonValue] | None = None
    judge_usage: dict[str, JsonValue] = Field(default_factory=dict)
    lineage: dict[str, JsonValue]
    semantic_review: dict[str, JsonValue]
    usage: dict[str, JsonValue] = Field(default_factory=dict)


class SemanticMatrixCell(ContractModel):
    provider: str = Field(min_length=1)
    framework: str = Field(min_length=1)
    model: str = Field(min_length=1)
    ok: bool
    control_kind: str = Field(min_length=1)
    eval_report: dict[str, JsonValue]
    episodes: tuple[SemanticEpisodeEvidence, ...] = Field(min_length=1)


class SemanticAttestation(ContractModel):
    schema_version: str = SEMANTIC_ATTESTATION_SCHEMA_VERSION
    created_at: AwareDatetime
    commit_sha: str
    wheel_sha256: str
    wheel_filename: str = Field(min_length=1)
    package_version: str = Field(min_length=1)
    runtime_package_file: str = Field(min_length=1)
    wheel_runtime_verified: bool
    environment: dict[str, JsonValue] = Field(default_factory=dict)
    gate_assets: dict[str, JsonValue] = Field(default_factory=dict)
    matrix: SemanticMatrix
    summary: SemanticSummary
    cells: tuple[SemanticMatrixCell, ...] = Field(min_length=1)

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


def validate_semantic_attestation(
    attestation: SemanticAttestation,
    *,
    expected_commit_sha: str,
    expected_wheel_sha256: str,
    expected_pairs: set[tuple[str, str]],
    now: datetime | None = None,
    max_age: timedelta = timedelta(hours=24),
) -> None:
    """Reject incomplete or internally contradictory semantic evidence."""

    errors: list[str] = []
    if attestation.commit_sha != expected_commit_sha.strip().lower():
        errors.append("commit SHA does not match the release candidate")
    if attestation.wheel_sha256 != expected_wheel_sha256.strip().lower():
        errors.append("wheel SHA-256 does not match the release candidate")
    age = (now or datetime.now(timezone.utc)) - attestation.created_at
    if not timedelta(0) <= age <= max_age:
        errors.append("attestation is outside the accepted age window")
    if not attestation.wheel_runtime_verified:
        errors.append("runtime was not verified as the installed candidate wheel")

    declared_providers = list(attestation.matrix.providers)
    declared_frameworks = list(attestation.matrix.frameworks)
    if len(set(declared_providers)) != len(declared_providers):
        errors.append("semantic matrix contains duplicate providers")
    if len(set(declared_frameworks)) != len(declared_frameworks):
        errors.append("semantic matrix contains duplicate frameworks")
    declared_pairs = {
        (provider, framework)
        for provider in declared_providers
        for framework in declared_frameworks
    }
    observed = [(cell.provider, cell.framework) for cell in attestation.cells]
    observed_pairs = set(observed)
    if len(observed_pairs) != len(observed):
        errors.append("attestation contains duplicate provider/framework cells")
    if declared_pairs != expected_pairs:
        errors.append("declared semantic matrix differs from the required matrix")
    missing = sorted(expected_pairs - observed_pairs)
    unexpected = sorted(observed_pairs - expected_pairs)
    if missing:
        errors.append(f"attestation is missing cells: {missing}")
    if unexpected:
        errors.append(f"attestation contains unexpected cells: {unexpected}")

    episodes = [episode for cell in attestation.cells for episode in cell.episodes]
    passed_cells = len([cell for cell in attestation.cells if cell.ok])
    passed_episodes = len([episode for episode in episodes if episode.ok])
    expected_summary = {
        "total": len(attestation.cells),
        "passed": passed_cells,
        "failed": len(attestation.cells) - passed_cells,
        "episodes_total": len(episodes),
        "episodes_passed": passed_episodes,
        "episodes_failed": len(episodes) - passed_episodes,
    }
    if attestation.summary.model_dump() != expected_summary:
        errors.append("semantic summary contradicts cell or episode evidence")

    for cell in attestation.cells:
        pair = (cell.provider, cell.framework)
        if not cell.ok:
            errors.append(f"semantic cell {pair} failed")
        expected_control = (
            "deterministic-control"
            if cell.provider == "python-runtime"
            else "live-language-model"
        )
        if cell.control_kind != expected_control:
            errors.append(f"semantic cell {pair} has incorrect control kind")
        if cell.eval_report.get("ok") is not True:
            errors.append(f"semantic cell {pair} has a failed eval report")
        names = [episode.name for episode in cell.episodes]
        if len(set(names)) != len(names):
            errors.append(f"semantic cell {pair} contains duplicate episodes")
        for episode in cell.episodes:
            errors.extend(_semantic_episode_errors(cell, episode))
    if errors:
        raise ValueError("; ".join(errors))


def _semantic_episode_errors(
    cell: SemanticMatrixCell,
    episode: SemanticEpisodeEvidence,
) -> list[str]:
    label = (cell.provider, cell.framework, episode.name)
    errors: list[str] = []
    if not episode.ok:
        errors.append(f"semantic episode {label} failed")
    if episode.deterministic_validation.get("ok") is not True:
        errors.append(f"semantic episode {label} failed deterministic validation")
    if episode.environment_episode.get(
        "entity"
    ) != "AgenticEnvironment" or not episode.environment_episode.get("name"):
        errors.append(f"semantic episode {label} lacks its Environment identity")
    judge = episode.judge
    if judge.get("ok") is not True:
        errors.append(f"semantic episode {label} failed its judge")
    if judge.get("deterministic_validation_ok") is not True:
        errors.append(
            f"semantic episode {label} judge contradicts deterministic validation"
        )
    if judge.get("certification_recorded") is not True or not judge.get(
        "certification_tool"
    ):
        errors.append(f"semantic episode {label} lacks a certified judge Tool")
    score = judge.get("score")
    threshold = judge.get("threshold")
    if (
        not isinstance(score, (int, float))
        or not isinstance(threshold, (int, float))
        or score < threshold
    ):
        errors.append(f"semantic episode {label} judge score is below threshold")
    if judge.get("provider") != cell.provider:
        errors.append(f"semantic episode {label} judge provider identity differs")
    if judge.get("framework") != cell.framework:
        errors.append(f"semantic episode {label} judge framework identity differs")
    if judge.get("model") != cell.model:
        errors.append(f"semantic episode {label} judge model identity differs")

    judge_execution = episode.judge_execution
    if cell.provider == "python-runtime":
        if judge_execution is not None:
            errors.append(
                f"semantic episode {label} deterministic judge must not claim an LM execution"
            )
    elif not isinstance(judge_execution, dict):
        errors.append(f"semantic episode {label} lacks live judge execution evidence")
    else:
        if judge_execution.get("ok") is not True:
            errors.append(f"semantic episode {label} live judge execution failed")
        judge_runtime = judge_execution.get("runtime")
        if not isinstance(judge_runtime, dict):
            errors.append(f"semantic episode {label} live judge lacks runtime identity")
        else:
            if judge_runtime.get("provider") != cell.provider:
                errors.append(
                    f"semantic episode {label} live judge provider identity differs"
                )
            if judge_runtime.get("framework") != cell.framework:
                errors.append(
                    f"semantic episode {label} live judge framework identity differs"
                )
            if judge_runtime.get("model") != cell.model:
                errors.append(
                    f"semantic episode {label} live judge model identity differs"
                )
    review = episode.semantic_review
    if review.get("ok") is not True or review.get("failures"):
        errors.append(f"semantic episode {label} failed manual semantic review")
    candidate = episode.candidate
    if candidate.get("ok") is not True:
        errors.append(f"semantic episode {label} candidate execution failed")
    runtime = candidate.get("runtime")
    if not isinstance(runtime, dict):
        errors.append(f"semantic episode {label} lacks runtime identity")
    else:
        if runtime.get("provider") != cell.provider:
            errors.append(f"semantic episode {label} provider identity differs")
        if runtime.get("framework") != cell.framework:
            errors.append(f"semantic episode {label} framework identity differs")
        if runtime.get("model") != cell.model:
            errors.append(f"semantic episode {label} model identity differs")
    if _contains_truthy_key(candidate, "fallback_provider"):
        errors.append(f"semantic episode {label} contains a fallback provider")
    if (
        cell.provider not in episode.human_result
        or cell.framework not in episode.human_result
    ):
        errors.append(f"semantic episode {label} human_result omits runtime identity")
    if not episode.lineage:
        errors.append(f"semantic episode {label} lacks lineage evidence")
    return errors


def _contains_truthy_key(value: JsonValue, key: str) -> bool:
    if isinstance(value, dict):
        return bool(value.get(key)) or any(
            _contains_truthy_key(item, key) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_truthy_key(item, key) for item in value)
    return False


__all__ = [
    "LiveScenarioName",
    "LIVE_ATTESTATION_SCHEMA_VERSION",
    "LIVE_SCENARIO_NAMES",
    "LiveAttestation",
    "LiveMatrixCase",
    "LiveScenarioEvidence",
    "SEMANTIC_ATTESTATION_SCHEMA_VERSION",
    "SemanticAttestation",
    "SemanticEpisodeEvidence",
    "SemanticMatrix",
    "SemanticMatrixCell",
    "SemanticSummary",
    "validate_live_attestation",
    "validate_semantic_attestation",
]
