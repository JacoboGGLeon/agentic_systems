from __future__ import annotations

import ast
from configparser import ConfigParser
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[2]


def test_test_suite_has_no_dynamic_or_quarantined_modules():
    assert not (ROOT / "tests" / "api" / "_legacy_modules").exists()
    assert not (ROOT / "tests" / "api" / "_load_legacy.py").exists()

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    excluded = project.get("tool", {}).get("ruff", {}).get("extend-exclude", [])
    assert "tests/api/_legacy_modules" not in excluded


def test_test_names_follow_owner_based_conventions():
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
        "branches",
        "residual",
        "remaining",
        "extended",
    )
    paths = sorted((ROOT / "tests").rglob("test_*.py"))
    module_offenders = [
        path.relative_to(ROOT).as_posix()
        for path in paths
        if any(token in path.name for token in forbidden)
    ]
    function_offenders = [
        f"{path.relative_to(ROOT).as_posix()}::{node.name}"
        for path in paths
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        and any(token in node.name for token in forbidden)
    ]

    assert module_offenders == []
    assert function_offenders == []


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
    assert bedrock.getfloat("report", "fail_under") == 100
