from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[2]


def test_quarantine_infrastructure_is_fully_retired():
    assert not (ROOT / "tests" / "api" / "_legacy_modules").exists()
    assert not (ROOT / "tests" / "api" / "_load_legacy.py").exists()

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    excluded = project.get("tool", {}).get("ruff", {}).get("extend-exclude", [])
    assert "tests/api/_legacy_modules" not in excluded


def test_modern_test_names_do_not_reintroduce_migration_labels():
    forbidden = (
        "legacy_",
        "checkpoint_",
        "_coverage",
        "phase1",
        "phase2",
        "phase3",
        "phase4",
        "phase5",
        "phase6",
        "phase7",
    )
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tests").rglob("test_*.py")
        if any(token in path.name for token in forbidden)
    ]
    assert offenders == []

def test_core_and_bedrock_quality_gates_remain_separate_and_blocking():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    core_omit = set(project["tool"]["coverage"]["run"]["omit"])
    assert core_omit >= {
        "src/agentic_systems/providers/bedrock_runtime.py",
        "src/agentic_systems/providers/bedrock/*",
    }
    assert project["tool"]["coverage"]["report"]["fail_under"] == 100

    bedrock = ConfigParser()
    assert bedrock.read(ROOT / ".coveragerc-bedrock", encoding="utf-8")
    sources = {source for source in bedrock.get("run", "source").splitlines() if source}
    assert sources == {
        "agentic_systems.providers.bedrock_runtime",
        "agentic_systems.providers.bedrock",
    }
    assert bedrock.getint("report", "precision") == 2
    assert bedrock.getfloat("report", "fail_under") == 53.1
