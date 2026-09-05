from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    module = importlib.import_module("build_release_manifest")
    names = [
        "agentic_systems-2.4.6-py3-none-any.whl",
        "agentic_systems-2.4.6.tar.gz",
        "agentic-systems-2.4.6-ada-offline.zip",
        "agentic-systems-2.4.6-strands-protocol-challenge.zip",
        "agentic-systems-studio-2.4.6.zip",
        "agentic-systems-skill-2.4.6.zip",
    ]
    for name in names:
        (tmp_path / name).write_bytes(name.encode())
    summary = {
        "schema_version": "agentic_systems.release-certification.v1",
        "package_version": "2.4.6",
        "assembly_commit_sha": "a" * 40,
        "wheel_sha256": module.sha256(tmp_path / names[0]),
        "sdist_sha256": module.sha256(tmp_path / names[1]),
        "secrets_redacted": True,
        "no_fallback": True,
        "totals": {
            "certified_live_failed": 0,
            "total_semantic_episodes_failed": 0,
            "total_semantic_episodes_reviewed": 108,
        },
    }
    names.append("final-certification-summary.json")

    def seal():
        (tmp_path / names[-1]).write_text(json.dumps(summary), encoding="utf-8")
        (tmp_path / "SHA256SUMS-2.4.6.txt").write_text(
            "".join(f"{module.sha256(tmp_path / name)}  {name}\n" for name in names),
            encoding="utf-8",
        )

    seal()
    return module, tmp_path, summary, names, seal


def test_manifest_binds_every_delivery_and_is_repeatable(candidate):
    module, directory, _, names, _ = candidate
    path = module.build(directory)
    first = path.read_bytes()
    assert module.build(directory).read_bytes() == first
    manifest = module.ReleaseManifest.model_validate_json(first)
    assert {item.filename for item in manifest.artifacts} == set(names) | {
        "SHA256SUMS-2.4.6.txt"
    }


@pytest.mark.parametrize(
    "fault",
    [
        "failed",
        "unreviewed",
        "boolean_count",
        "fallback",
        "secret",
        "schema",
        "identity",
        "missing",
        "bytes",
    ],
)
def test_manifest_rejects_incomplete_or_conflicting_evidence(candidate, fault):
    module, directory, summary, names, seal = candidate
    if fault == "failed":
        summary["totals"]["total_semantic_episodes_failed"] = 1
    elif fault in {"unreviewed", "boolean_count"}:
        summary["totals"]["total_semantic_episodes_reviewed"] = (
            0 if fault == "unreviewed" else True
        )
    elif fault == "fallback":
        summary["no_fallback"] = "true"
    elif fault == "secret":
        summary["secrets_redacted"] = False
    elif fault == "schema":
        summary["schema_version"] = "unknown"
    elif fault == "identity":
        summary["wheel_sha256"] = "b" * 64
    elif fault == "missing":
        names.remove("agentic-systems-skill-2.4.6.zip")
    seal()
    if fault == "bytes":
        (directory / names[0]).write_bytes(b"changed after sealing")
    with pytest.raises(ValueError):
        module.build(directory)
    assert not (directory / "release-manifest.json").exists()


@pytest.mark.parametrize(
    "filename", ["extra.whl", "extra.tar.gz", "release-manifest.json"]
)
def test_manifest_cannot_disguise_distribution_or_include_itself(candidate, filename):
    module, _, _, _, _ = candidate
    with pytest.raises(ValueError):
        module.ReleaseArtifactIdentity(filename=filename, kind="asset", sha256="a" * 64)
