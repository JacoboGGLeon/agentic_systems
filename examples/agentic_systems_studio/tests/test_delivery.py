from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

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
        assert all("outputs" in cell for cell in payload["cells"] if cell["cell_type"] == "code")
        combined += "\n".join(
            "".join(cell["source"])
            for cell in payload["cells"]
            if cell["cell_type"] == "code"
        )
    assert "build_system(" in combined
    assert "compose_systems(" in combined


def test_cli_reads_same_catalog_and_scaffolder(tmp_path: Path, capsys):
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    assert SYSTEM_SPECS[0].id in output

    assert main(["describe", "data-quality"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "data-quality"

    target = tmp_path / "cli-app"
    assert main(["init", str(target), "--name", "cli-app", "--system", "prompt-security"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["system_id"] == "prompt-security"
    assert (target / "manifest.json").exists()

    database = tmp_path / "cli.db"
    assert main(["db", "--path", str(database)]) == 0
    inventory = json.loads(capsys.readouterr().out)["inventory"]
    assert inventory["systems"] == 10


def test_bundle_contains_ten_independent_nested_bundles(tmp_path: Path):
    module = _load_bundle_builder()
    bundle = module.build_bundle(tmp_path)
    assert bundle.name == "agentic-systems-studio-2.0.zip"

    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        assert "notebooks/02_launch_studio.ipynb" in names
        assert len(manifest["systems"]) == 10
        assert manifest["credentials_included"] is False
        assert "data/studio.db" in names
        assert "skills/agentic-systems/SKILL.md" in names
        assert "notebooks/01_system_composition.ipynb" in names
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
            "skills/codex-agentic-application/SKILL.md",
        } <= nested_names
