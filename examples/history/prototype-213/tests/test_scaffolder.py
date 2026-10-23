import hashlib
import json
from pathlib import Path

import pytest
from unified_grammar.scaffold import HOME, create_project


def test_generated_project_is_complete_and_never_overwrites(tmp_path):
    project = create_project(tmp_path / "project")
    required = (
        "app.py", "pyproject.toml", ".env.example", "manifest.json", "SHA256SUMS.txt",
        "src/order_challenge/system.py", "src/order_challenge/skills.py",
        "src/order_challenge/fixtures/cases.json", "src/unified_grammar/core.py",
        "notebooks/01_order_challenge.ipynb", "tests/test_contract.py",
        "test_offline.py", "execute_notebook.py",
    )
    assert all((project / name).is_file() for name in required)
    manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["target_version"] == "2.1.3"
    assert manifest["base_distribution"]["version"] == "2.1.2"
    assert manifest["validation"] == "not-run-generated-project"
    for line in (project / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((project / name).read_bytes()).hexdigest() == digest
    before = (project / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        create_project(project)
    assert (project / "manifest.json").read_bytes() == before


def test_scaffolder_rejects_destination_inside_its_sources():
    forbidden = HOME / "must-not-be-created"
    assert not forbidden.exists()
    with pytest.raises(ValueError, match="outside"):
        create_project(forbidden)
    assert not forbidden.exists()
