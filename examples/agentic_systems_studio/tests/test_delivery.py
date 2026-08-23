from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import agentic_systems as toolkit

from agentic_systems_studio.__main__ import main
from agentic_systems_studio.catalog import SYSTEM_SPECS


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_bundle_builder():
    path = PROJECT_ROOT / "scripts" / "build_bundle.py"
    spec = importlib.util.spec_from_file_location("studio_bundle_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_notebooks_are_valid_and_use_public_studio_constructors():
    notebooks = sorted((PROJECT_ROOT / "notebooks").glob("*.ipynb"))
    assert len(notebooks) >= 2
    combined = ""
    for path in notebooks:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["nbformat"] == 4
        assert all(
            "outputs" in cell
            for cell in payload["cells"]
            if cell["cell_type"] == "code"
        )
        combined += "\n".join(
            "".join(cell["source"])
            for cell in payload["cells"]
            if cell["cell_type"] == "code"
        )
    assert "build_system(" in combined
    assert "compose_systems(" in combined


def test_cli_reads_same_catalog_creator_and_scaffolder(
    tmp_path: Path, capsys, monkeypatch
):
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    assert SYSTEM_SPECS[0].id in output

    assert main(["describe", "data-quality"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "data-quality"

    target = tmp_path / "cli-app"
    assert (
        main(["init", str(target), "--name", "cli-app", "--system", "prompt-security"])
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["system_id"] == "prompt-security"
    assert (target / "manifest.json").exists()

    class FakeCreator:
        def run(self, request, **_kwargs):
            return toolkit.RunResult(
                text="Blueprint ready.",
                data={"request": request},
                engine="openai-runtime",
                model="test-model",
                mode="create",
            )

    monkeypatch.setattr(
        "agentic_systems_studio.creator.build_system",
        lambda *_args, **_kwargs: FakeCreator(),
    )
    created = tmp_path / "created-by-cli"
    create_database = tmp_path / "create.db"
    assert (
        main(
            [
                "create",
                str(created),
                "--name",
                "created-by-cli",
                "--template",
                "incident-response",
                "--input",
                "Create an incident response system.",
                "--db",
                str(create_database),
            ]
        )
        == 0
    )
    created_result = json.loads(capsys.readouterr().out)
    assert created_result["data"]["generated"] is True
    assert created_result["data"]["artifact"]["validation"]["ok"] is True
    assert (created / "manifest.json").is_file()

    database = tmp_path / "cli.db"
    assert main(["db", "--path", str(database)]) == 0
    inventory = json.loads(capsys.readouterr().out)["inventory"]
    assert inventory["systems"] == 10

    validation_report = {
        "schema_version": "agentic-systems.studio-live-validation/v1",
        "provider": "ollama-runtime",
        "framework": "agentic-systems",
        "model": "test-model",
        "requested": 1,
        "executed": 1,
        "passed": 1,
        "failed": 0,
        "ok": True,
        "systems": [{"id": "data-quality", "ok": True}],
    }
    monkeypatch.setattr(
        "agentic_systems_studio.__main__.validate_catalog",
        lambda config, system_ids, fail_fast: validation_report,
    )
    evidence = tmp_path / "validation.json"
    assert (
        main(
            [
                "validate",
                "data-quality",
                "--provider",
                "ollama-runtime",
                "--model",
                "test-model",
                "--output",
                str(evidence),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert json.loads(evidence.read_text(encoding="utf-8")) == validation_report


def test_streamlit_creator_exposes_generated_artifact_evidence():
    source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    assert "create_application(" in source
    assert "Generate and validate Agentic System" in source
    assert "Download generated Agentic System (.zip)" in source
    assert 'artifact["validation"]' in source
    assert 'artifact["mermaid"]' in source


def test_bundle_contains_ten_independent_nested_bundles(tmp_path: Path):
    module = _load_bundle_builder()
    bundle = module.build_bundle(tmp_path)
    assert bundle.name == "agentic-systems-studio-2.1.0.zip"

    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        assert "notebooks/02_launch_studio.ipynb" in names
        assert len(manifest["systems"]) == 10
        assert manifest["credentials_included"] is False
        assert "data/studio.db" in names
        assert "skills/agentic-systems/SKILL.md" in names
        assert "notebooks/01_system_composition.ipynb" in names
        assert "scripts/validate_sandbox.py" in names
        assert "evidence/ollama-native.json" in names
        assert "SHA256SUMS" in names
        nested = sorted(name for name in names if name.startswith("system-bundles/"))
        assert len(nested) == 10

        creator_bytes = archive.read("system-bundles/agentic-systems-creator.zip")
        nested_path = tmp_path / "creator.zip"
        nested_path.write_bytes(creator_bytes)
    with zipfile.ZipFile(nested_path) as creator:
        nested_names = set(creator.namelist())
        assert {
            "manifest.json",
            "assets/system.mmd",
            "data/app.db",
            "notebooks/00_walkthrough.ipynb",
            "tests/test_contract.py",
            "tests/test_execution.py",
            "src/agentic_systems_creator/tools.py",
            "src/agentic_systems_creator/skills.py",
            "src/agentic_systems_creator/settings.py",
            "skills/codex-agentic-application/SKILL.md",
        } <= nested_names


def test_official_skill_scaffolds_and_tests_every_catalog_system(tmp_path: Path):
    script = PROJECT_ROOT / "skills" / "agentic-systems" / "scripts" / "scaffold.py"
    for spec in SYSTEM_SPECS:
        target = tmp_path / spec.id
        package = f"skill_{spec.id.replace('-', '_')}"
        subprocess.run(
            [
                sys.executable,
                str(script),
                str(target),
                "--name",
                package,
                "--system",
                spec.id,
            ],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests"],
            cwd=target,
            check=True,
            capture_output=True,
            text=True,
        )
        env = dict(os.environ)
        env["RUN_LIVE"] = "0"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "nbconvert",
                "--to=notebook",
                "--execute",
                "notebooks/00_walkthrough.ipynb",
                "--output=executed.ipynb",
            ],
            cwd=target,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
