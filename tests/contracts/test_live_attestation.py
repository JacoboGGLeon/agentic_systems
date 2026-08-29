from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import ValidationError
import pytest

from agentic_systems.schemas import (
    LiveAttestation,
    LIVE_SCENARIO_NAMES,
    LiveMatrixCase,
    LiveScenarioEvidence,
    SemanticAttestation,
    SemanticEpisodeEvidence,
    SemanticMatrix,
    SemanticMatrixCell,
    SemanticSummary,
    validate_live_attestation,
    validate_semantic_attestation,
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
        wheel_filename="agentic_systems-2.1.0-py3-none-any.whl",
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


def _semantic_attestation() -> SemanticAttestation:
    episode = SemanticEpisodeEvidence(
        name="calculation",
        ok=True,
        candidate={
            "ok": True,
            "runtime": {
                "provider": "openai-runtime",
                "framework": "native",
                "model": "gpt-4.1-mini",
            },
            "children": [],
        },
        deterministic_validation={"ok": True, "issues": []},
        environment_episode={
            "name": "semantic-openai-runtime-native-calculation",
            "entity": "AgenticEnvironment",
        },
        human_result="Provider: openai-runtime | Framework: native | Answer: 323",
        judge={
            "ok": True,
            "score": 1.0,
            "threshold": 0.8,
            "deterministic_validation_ok": True,
            "certification_recorded": True,
            "certification_tool": "record_semantic_judgment",
            "provider": "openai-runtime",
            "framework": "native",
            "model": "gpt-4.1-mini",
        },
        judge_execution={
            "ok": True,
            "runtime": {
                "provider": "openai-runtime",
                "framework": "native",
                "model": "gpt-4.1-mini",
            },
        },
        lineage={"steps": [{"kind": "answer"}]},
        semantic_review={"ok": True, "failures": []},
    )
    return SemanticAttestation(
        created_at=NOW,
        commit_sha=COMMIT,
        wheel_sha256=WHEEL,
        wheel_filename="agentic_systems-2.1.0-py3-none-any.whl",
        package_version="2.1.0",
        runtime_package_file="/venv/site-packages/agentic_systems/__init__.py",
        wheel_runtime_verified=True,
        gate_assets={"runner": {"sha256": "a" * 64}},
        matrix=SemanticMatrix(
            providers=("openai-runtime",),
            frameworks=("native",),
        ),
        summary=SemanticSummary(
            total=1,
            passed=1,
            failed=0,
            episodes_total=1,
            episodes_passed=1,
            episodes_failed=0,
        ),
        cells=(
            SemanticMatrixCell(
                provider="openai-runtime",
                framework="native",
                model="gpt-4.1-mini",
                ok=True,
                control_kind="live-language-model",
                eval_report={"ok": True},
                episodes=(episode,),
            ),
        ),
    )


def test_semantic_attestation_accepts_complete_reviewed_evidence() -> None:
    evidence = _semantic_attestation()
    validate_semantic_attestation(
        evidence,
        expected_commit_sha=COMMIT,
        expected_wheel_sha256=WHEEL,
        expected_pairs={("openai-runtime", "native")},
        now=NOW + timedelta(hours=1),
    )
    assert (
        SemanticAttestation.model_validate_json(evidence.model_dump_json()) == evidence
    )


def test_semantic_attestation_rejects_false_positive_and_matrix_omission() -> None:
    evidence = _semantic_attestation()
    episode = (
        evidence.cells[0]
        .episodes[0]
        .model_copy(
            update={
                "ok": False,
                "deterministic_validation": {
                    "ok": False,
                    "issues": [{"code": "wrong"}],
                },
            }
        )
    )
    cell = evidence.cells[0].model_copy(update={"ok": False, "episodes": (episode,)})
    invalid = evidence.model_copy(update={"cells": (cell,)})
    with pytest.raises(ValueError) as captured:
        validate_semantic_attestation(
            invalid,
            expected_commit_sha=COMMIT,
            expected_wheel_sha256=WHEEL,
            expected_pairs={
                ("openai-runtime", "native"),
                ("bedrock-runtime", "native"),
            },
            now=NOW,
        )
    message = str(captured.value)
    assert "required matrix" in message
    assert "summary contradicts" in message
    assert "failed deterministic validation" in message


def test_semantic_attestation_rejects_missing_live_judge_execution() -> None:
    evidence = _semantic_attestation()
    episode = evidence.cells[0].episodes[0].model_copy(update={"judge_execution": None})
    cell = evidence.cells[0].model_copy(update={"episodes": (episode,)})
    invalid = evidence.model_copy(update={"cells": (cell,)})

    with pytest.raises(ValueError, match="lacks live judge execution evidence"):
        validate_semantic_attestation(
            invalid,
            expected_commit_sha=COMMIT,
            expected_wheel_sha256=WHEEL,
            expected_pairs={("openai-runtime", "native")},
            now=NOW,
        )


def test_semantic_attestation_rejects_judge_identity_mismatch() -> None:
    evidence = _semantic_attestation()
    original = evidence.cells[0].episodes[0]
    judge = dict(original.judge)
    judge["provider"] = "bedrock-runtime"
    episode = original.model_copy(update={"judge": judge})
    cell = evidence.cells[0].model_copy(update={"episodes": (episode,)})
    invalid = evidence.model_copy(update={"cells": (cell,)})

    with pytest.raises(ValueError, match="judge provider identity differs"):
        validate_semantic_attestation(
            invalid,
            expected_commit_sha=COMMIT,
            expected_wheel_sha256=WHEEL,
            expected_pairs={("openai-runtime", "native")},
            now=NOW,
        )
