import os

import pytest

from agentic_systems import (
    AgenticSystem,
)
from agentic_systems.skills import load_skill


def build_system(strict=True, defaults=None):

    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(
        model="demo-model", region="us-east-1", strict=strict, defaults=defaults
    )


def test_skill_loader_error_paths(tmp_path, monkeypatch):
    system = build_system()
    with pytest.raises(Exception, match="does not exist"):
        load_skill(system, tmp_path / "missing")

    no_md = tmp_path / "no_md"
    no_md.mkdir()
    with pytest.raises(Exception, match="missing SKILL.md"):
        load_skill(system, no_md)

    no_py = tmp_path / "no_py"
    no_py.mkdir()
    (no_py / "SKILL.md").write_text("# Title\n", encoding="utf-8")
    with pytest.raises(Exception, match="missing skill.py"):
        load_skill(system, no_py)

    no_register = tmp_path / "no_register"
    no_register.mkdir()
    (no_register / "SKILL.md").write_text("# Title\n", encoding="utf-8")
    (no_register / "skill.py").write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(Exception, match="register"):
        load_skill(system, no_register)

    none_register = tmp_path / "none_register"
    none_register.mkdir()
    (none_register / "SKILL.md").write_text("\n", encoding="utf-8")
    (none_register / "skill.py").write_text(
        "def register(system):\n    return None\n", encoding="utf-8"
    )
    loaded = load_skill(system, none_register)
    assert loaded.manifest.description == ""

    bad_return = tmp_path / "bad_return"
    bad_return.mkdir()
    (bad_return / "SKILL.md").write_text("# Bad\n", encoding="utf-8")
    (bad_return / "skill.py").write_text(
        "def register(system):\n    return []\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match="must return a dict"):
        load_skill(system, bad_return)

    spec_none = tmp_path / "spec_none"
    spec_none.mkdir()
    (spec_none / "SKILL.md").write_text("# Spec none\n", encoding="utf-8")
    (spec_none / "skill.py").write_text(
        "def register(system):\n    return {}\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        "agentic_systems.skills.importlib.util.spec_from_file_location",
        lambda *a, **k: None,
    )
    with pytest.raises(Exception, match="Cannot import"):
        load_skill(system, spec_none)
