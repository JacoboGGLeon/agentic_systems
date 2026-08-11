from __future__ import annotations

from types import SimpleNamespace
import importlib

import pytest

from agentic_systems.skills.loader import (
    SkillLoadError,
    load_skill as load_skill_from_path,
)
from agentic_systems.skills.skill import Skill

tool_module = importlib.import_module("agentic_systems.tools.tool")


def test_skill_loader_edges(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(SkillLoadError):
        load_skill_from_path(SimpleNamespace(), missing)

    no_md = tmp_path / "no_md"
    no_md.mkdir()
    with pytest.raises(SkillLoadError):
        load_skill_from_path(SimpleNamespace(), no_md)

    no_py = tmp_path / "no_py"
    no_py.mkdir()
    (no_py / "SKILL.md").write_text("Skill docs\n", encoding="utf-8")
    with pytest.raises(SkillLoadError):
        load_skill_from_path(SimpleNamespace(), no_py)

    not_callable = tmp_path / "not_callable"
    not_callable.mkdir()
    (not_callable / "SKILL.md").write_text("Skill docs\n", encoding="utf-8")
    (not_callable / "skill.py").write_text("register = 1\n", encoding="utf-8")
    with pytest.raises(SkillLoadError):
        load_skill_from_path(SimpleNamespace(), not_callable)

    bad_runtime = tmp_path / "bad_runtime"
    bad_runtime.mkdir()
    (bad_runtime / "SKILL.md").write_text("Skill docs\n", encoding="utf-8")
    (bad_runtime / "skill.py").write_text(
        "def register(system):\n    return {'runtime_skill': object()}\n",
        encoding="utf-8",
    )
    with pytest.raises(SkillLoadError):
        load_skill_from_path(SimpleNamespace(), bad_runtime)

    valid = tmp_path / "valid"
    valid.mkdir()
    (valid / "__init__.py").write_text("", encoding="utf-8")
    (valid / "SKILL.md").write_text("\n\nFirst description line\n", encoding="utf-8")
    (valid / "skill.py").write_text(
        "from agentic_systems.skills import Skill\n"
        "def register(system):\n"
        "    return {'runtime_skill': Skill(name='loaded', tools=[]), 'manifest': {'tools': []}}\n",
        encoding="utf-8",
    )
    loaded = load_skill_from_path(
        SimpleNamespace(tools=[], agents=[], public_tools={}, _skills=[]), valid
    )
    assert loaded.manifest.name == "loaded"
    assert isinstance(loaded.runtime_skill, Skill)
