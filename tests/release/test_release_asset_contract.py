from __future__ import annotations

import importlib.util
import json
import tarfile
import zipfile
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


def test_certification_identity_rejects_a_different_release_artifact(
    monkeypatch, tmp_path: Path
) -> None:
    module = _builder()
    monkeypatch.setattr(module, "VERSION", "2.1.1")
    wheel = tmp_path / "agentic_systems-2.1.1-py3-none-any.whl"
    sdist = tmp_path / "agentic_systems-2.1.1.tar.gz"
    wheel.write_bytes(b"final wheel")
    sdist.write_bytes(b"final sdist")
    summary = tmp_path / "final-certification-summary.json"
    summary.write_text(
        json.dumps(
            {
                "schema_version": "agentic_systems.release-certification.v1",
                "package_version": "2.1.1",
                "wheel_sha256": "0" * 64,
                "sdist_sha256": module.sha256(sdist),
                "no_fallback": True,
                "secrets_redacted": True,
                "totals": {
                    "certified_live_failed": 0,
                    "total_semantic_episodes_failed": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not describe"):
        module.validate_certification_identity(
            summary,
            wheel=wheel,
            sdist=sdist,
        )


def _synthetic_distributions(tmp_path: Path, readme: str) -> tuple[Path, Path]:
    wheel = tmp_path / "agentic_systems-2.1.1-py3-none-any.whl"
    metadata = (
        "Metadata-Version: 2.4\n"
        "Name: agentic-systems\n"
        "Version: 2.1.1\n"
        "Description-Content-Type: text/markdown\n\n" + readme
    )
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("agentic_systems-2.1.1.dist-info/METADATA", metadata)
    sdist = tmp_path / "agentic_systems-2.1.1.tar.gz"
    source = tmp_path / "README.md"
    source.write_text(readme, encoding="utf-8")
    with tarfile.open(sdist, "w:gz") as archive:
        archive.add(source, arcname="agentic_systems-2.1.1/README.md")
    return wheel, sdist


def test_distribution_narrative_must_match_the_canonical_readme(
    tmp_path: Path,
) -> None:
    module = _builder()
    readme = tmp_path / "canonical.md"
    readme.write_text("# Canonical\n\nOne contract.\n", encoding="utf-8")
    wheel, sdist = _synthetic_distributions(tmp_path, "# Canonical\n\nOne contract.\n")

    module.validate_distribution_narrative(
        wheel=wheel,
        sdist=sdist,
        readme=readme,
    )

    readme.write_text("# Changed after the build\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Wheel long description"):
        module.validate_distribution_narrative(
            wheel=wheel,
            sdist=sdist,
            readme=readme,
        )
