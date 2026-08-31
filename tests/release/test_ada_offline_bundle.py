from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
FRAMEWORKS = ("native", "langgraph", "openai-agents", "strands")


def _builder():
    path = ROOT / "scripts" / "build_ada_offline_bundle.py"
    spec = importlib.util.spec_from_file_location("ada_bundle_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _semantic_evidence(
    provider: str,
    *,
    commit_sha: str,
    wheel_sha256: str,
    episodes_per_framework: int,
) -> dict[str, object]:
    episode = {
        "ok": True,
        "deterministic_validation": {"ok": True},
        "judge": {"ok": True},
    }
    return {
        "schema_version": "agentic_systems.semantic-attestation.v1",
        "commit_sha": commit_sha,
        "wheel_sha256": wheel_sha256,
        "wheel_runtime_verified": True,
        "environment": {
            "providers": {
                provider: {
                    "runtime": {
                        "selected_provider": provider,
                        "fallback_provider": None,
                    }
                }
            }
        },
        "cells": [
            {
                "provider": provider,
                "framework": framework,
                "ok": True,
                "episodes": [dict(episode) for _ in range(episodes_per_framework)],
            }
            for framework in FRAMEWORKS
        ],
    }


def _authentication_evidence(
    *, commit_sha: str, wheel_sha256: str
) -> dict[str, object]:
    return {
        "schema_version": "agentic_systems.live-attestation.v1",
        "commit_sha": commit_sha,
        "wheel_sha256": wheel_sha256,
        "environment": {
            "bedrock_authentication_mode": "aws-credential-chain",
            "uses_aws_credential_chain": True,
        },
        "cases": [
            {
                "provider": "bedrock-runtime",
                "framework": framework,
                "ok": True,
                "scenarios": [
                    {"name": "completion", "ok": True, "details": {}},
                    {"name": "tool_calling", "ok": True, "details": {}},
                ],
            }
            for framework in FRAMEWORKS
        ],
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _certified_fixture(module, tmp_path: Path, monkeypatch) -> dict[str, object]:
    """Create a credential-free release contract without relying on local dist/."""

    dist = tmp_path / "dist"
    evidence = dist / "release-evidence"
    wheel = dist / "agentic_systems-2.1.0-py3-none-any.whl"
    sdist = dist / "agentic_systems-2.1.0.tar.gz"
    summary = evidence / "final-certification-summary.json"
    dist.mkdir(parents=True)
    evidence.mkdir()
    wheel.write_bytes(b"synthetic wheel identity for hermetic release tests\n")
    sdist.write_bytes(b"synthetic sdist identity for hermetic release tests\n")

    monkeypatch.setattr(module, "DIST", dist)
    monkeypatch.setattr(module, "EVIDENCE", evidence)
    monkeypatch.setattr(module, "SUMMARY", summary)
    monkeypatch.setattr(module, "WHEEL", wheel)
    monkeypatch.setattr(module, "SDIST", sdist)

    commit_sha = module._git("rev-parse", "HEAD")
    wheel_sha256 = module.sha256(wheel)
    primary_specs = {
        "python-runtime": ("local-semantic-attestation.json", 3),
        "openai-runtime": ("openai-semantic-attestation.json", 4),
        "ollama-runtime": ("ollama-semantic-attestation.json", 4),
        "bedrock-runtime": ("bedrock-semantic-attestation.json", 4),
        "vllm-runtime": ("vllm-semantic-attestation.json", 4),
    }
    primary: dict[str, object] = {}
    for provider, (filename, episodes_per_framework) in primary_specs.items():
        artifact = evidence / filename
        _write_json(
            artifact,
            _semantic_evidence(
                provider,
                commit_sha=commit_sha,
                wheel_sha256=wheel_sha256,
                episodes_per_framework=episodes_per_framework,
            ),
        )
        primary[provider] = {
            "artifact": filename,
            "frameworks": list(FRAMEWORKS),
            "passed": 4,
            "failed": 0,
            "episodes_passed": episodes_per_framework * len(FRAMEWORKS),
            "episodes_failed": 0,
            "sha256": module.sha256(artifact),
        }

    authentication = evidence / "bedrock-iam-attestation.json"
    _write_json(
        authentication,
        _authentication_evidence(
            commit_sha=commit_sha,
            wheel_sha256=wheel_sha256,
        ),
    )
    vllm_review = evidence / "vllm-semantic-review-final.md"
    vllm_review.write_text("# Synthetic semantic review\n", encoding="utf-8")

    certification: dict[str, object] = {
        "schema_version": "agentic_systems.release-certification.v1",
        "package_version": "2.1.0",
        "commit_sha": commit_sha,
        "wheel_sha256": wheel_sha256,
        "no_fallback": True,
        "secrets_redacted": True,
        "primary_matrix": primary,
        "additional_authentication_routes": {
            "bedrock-runtime/aws-credential-chain": {
                "artifact": authentication.name,
                "authentication_mode": "aws-credential-chain",
                "frameworks": list(FRAMEWORKS),
                "passed": 4,
                "failed": 0,
                "sha256": module.sha256(authentication),
            }
        },
        "evidence_inventory": {"vllm_semantic_review": {"artifact": vllm_review.name}},
        "totals": {
            "certified_live_executions": 24,
            "certified_live_failed": 0,
            "semantic_episodes_passed": 76,
            "semantic_episodes_failed": 0,
        },
    }
    _write_json(summary, certification)
    return certification


def test_ada_bundle_is_reproducible_certified_and_offline(tmp_path: Path, monkeypatch):
    module = _builder()
    _certified_fixture(module, tmp_path, monkeypatch)
    first = module.build_bundle(tmp_path / "first", enforce_materials_clean=False)
    second = module.build_bundle(tmp_path / "second", enforce_materials_clean=False)
    assert first.read_bytes() == second.read_bytes()

    root = "agentic-systems-2.1.0-ada-offline/"
    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read(root + "manifest.json"))
        assert manifest["schema_version"] == "agentic-systems.ada-offline-bundle/v1"
        assert manifest["certification"]["total"] == "24/24"
        assert manifest["certification"]["semantic_episodes"] == "76/76"
        assert manifest["certification"]["no_fallback"] is True
        assert manifest["provenance"]["core_source_equivalent"] is True
        assert manifest["tutorial_notebooks"] == 21
        assert manifest["cli_tutorials"] == 0
        assert root + ".env.example" in names
        env_examples = {name for name in names if Path(name).name == ".env.example"}
        assert env_examples == {root + ".env.example"}
        assert root + "studio/app.py" in names
        assert root + "studio/notebooks/00_conversational_system.ipynb" in names
        assert root + "studio/notebooks/01_launch_studio.ipynb" in names
        assert root + "studio/src/agentic_systems_studio/presentation.py" in names
        assert root + "studio/scripts/validate_conversation_live.py" in names
        assert root + "validation/run_ada_semantic_matrix.py" in names
        assert root + "validation/run_semantic_matrix.py" in names
        assert root + "validation/semantic_e2e_application.py" in names
        assert manifest["semantic_gate"]["configuration_source"] == ".env"
        assert manifest["semantic_gate"]["frameworks"] == [
            "langgraph",
            "native",
            "openai-agents",
            "strands",
        ]
        assert manifest["semantic_gate"]["model_provider_episodes"] == 16
        bundled_evidence = {
            Path(name).name for name in names if name.startswith(root + "evidence/")
        }
        assert bundled_evidence == set(manifest["evidence_files"])
        certification = json.loads(
            archive.read(root + "evidence/final-certification-summary.json")
        )
        primary = certification["primary_matrix"]
        assert primary["vllm-runtime"]["artifact"] in bundled_evidence
        assert primary["python-runtime"]["artifact"] in bundled_evidence
        assert (
            certification["evidence_inventory"]["vllm_semantic_review"]["artifact"]
            in bundled_evidence
        )
        assert (
            certification["additional_authentication_routes"][
                "bedrock-runtime/aws-credential-chain"
            ]["artifact"]
            in bundled_evidence
        )
        assert not any(Path(name).name == ".env" for name in names)
        assert not any("/cli/" in name.lower() for name in names)

        checksums = archive.read(root + "SHA256SUMS").decode().splitlines()
        for row in checksums:
            expected, relative = row.split("  ", 1)
            observed = hashlib.sha256(archive.read(root + relative)).hexdigest()
            assert observed == expected


def test_certified_wheel_identity_matches_summary(tmp_path: Path, monkeypatch):
    module = _builder()
    _certified_fixture(module, tmp_path, monkeypatch)
    certification = module._load_certification()
    assert module.sha256(module.WHEEL) == certification["wheel_sha256"]
    assert certification["totals"]["certified_live_executions"] == 24
    assert certification["totals"]["certified_live_failed"] == 0
    assert certification["totals"]["semantic_episodes_passed"] == 76
    assert certification["totals"]["semantic_episodes_failed"] == 0


def test_certification_rejects_semantic_false_positive(tmp_path: Path, monkeypatch):
    module = _builder()
    _certified_fixture(module, tmp_path, monkeypatch)
    certification = module._load_certification()
    source = module.EVIDENCE / "local-semantic-attestation.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["cells"][0]["episodes"][0]["judge"]["ok"] = False
    evidence = tmp_path / source.name
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Semantic evidence is incomplete"):
        module._validate_semantic_evidence(
            evidence,
            provider="python-runtime",
            certification=certification,
            row=certification["primary_matrix"]["python-runtime"],
        )


def test_certification_rejects_iam_fallback(tmp_path: Path, monkeypatch):
    module = _builder()
    _certified_fixture(module, tmp_path, monkeypatch)
    certification = module._load_certification()
    source = module.EVIDENCE / "bedrock-iam-attestation.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["cases"][0]["scenarios"][1]["details"]["fallback_provider"] = (
        "openai-runtime"
    )
    evidence = tmp_path / source.name
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    row = certification["additional_authentication_routes"][
        "bedrock-runtime/aws-credential-chain"
    ]

    with pytest.raises(ValueError, match="Authentication evidence used fallback"):
        module._validate_authentication_evidence(
            evidence,
            certification=certification,
            row=row,
        )
