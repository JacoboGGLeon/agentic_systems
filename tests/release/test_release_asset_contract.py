from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _builder():
    path = ROOT / "scripts" / "build_release_assets.py"
    spec = importlib.util.spec_from_file_location("release_asset_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_release_workflow_mirrors_every_public_delivery() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    for filename in (
        "agentic_systems-${RELEASE_VERSION}-py3-none-any.whl",
        "agentic_systems-${RELEASE_VERSION}.tar.gz",
        "agentic-systems-${RELEASE_VERSION}-ada-offline.zip",
        "agentic-systems-studio-${RELEASE_VERSION}.zip",
        "agentic-systems-skill-${RELEASE_VERSION}.zip",
        "agentic-systems-${RELEASE_VERSION}-strands-protocol-challenge.zip",
        "final-certification-summary.json",
        "SHA256SUMS-${RELEASE_VERSION}.txt",
    ):
        assert filename in workflow
    for checksum_input in (
        "wheel_sha256",
        "sdist_sha256",
        "ada_sha256",
        "studio_sha256",
        "skill_sha256",
        "certification_sha256",
        "challenge_sha256",
    ):
        assert f"inputs.{checksum_input}" in workflow
    assert "candidate/*.json" in workflow


def test_quality_audits_the_clean_built_runtime_not_the_dev_host() -> None:
    workflow = (ROOT / ".github" / "workflows" / "quality.yml").read_text(
        encoding="utf-8"
    )

    build_index = workflow.index("python -m build --no-isolation")
    audit_index = workflow.index("Clean runtime dependency vulnerability audit")
    assert audit_index > build_index
    assert ".tmp/runtime-audit/bin/python -m pip install dist/*.whl" in workflow
    assert (
        ".tmp/runtime-audit/bin/python -m pip_audit --local --skip-editable" in workflow
    )
    assert "run: python -m pip_audit --local --skip-editable" not in workflow


def test_plain_certification_artifact_is_secret_audited(tmp_path: Path) -> None:
    module = _builder()
    summary = tmp_path / "final-certification-summary.json"
    summary.write_text('{"token":"sk-' + "x" * 24 + '"}', encoding="utf-8")

    report = module.audit_archive(summary, [])

    assert report["members"] == 1
    assert report["secret_paths"] == [summary.name]
    assert report["ok"] is False


def test_final_asset_build_can_require_live_certification(
    monkeypatch, tmp_path: Path
) -> None:
    module = _builder()
    dist = tmp_path / "dist"
    dist.mkdir()
    studio = tmp_path / "studio.zip"
    studio.write_bytes(b"synthetic studio archive")
    missing = tmp_path / "final-certification-summary.json"
    monkeypatch.setattr(module, "DIST", dist)
    monkeypatch.setattr(module, "STUDIO_SOURCE", studio)
    monkeypatch.setattr(
        module, "CERTIFICATION_ASSET", dist / "final-certification-summary.json"
    )
    monkeypatch.setattr(module, "CERTIFICATION_SUMMARY", missing)

    with pytest.raises(FileNotFoundError, match="Final release assembly requires"):
        module.build_release_assets(require_certification=True)


def test_certification_source_and_public_asset_have_distinct_locations() -> None:
    module = _builder()

    assert module.CERTIFICATION_SUMMARY.parent.name == "release-evidence"
    assert module.CERTIFICATION_ASSET.parent == module.DIST
    assert module.CERTIFICATION_ASSET.name == module.CERTIFICATION_SUMMARY.name
