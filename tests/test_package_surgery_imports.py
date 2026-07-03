"""Compatibility tests for the tools/skills module-to-package migration."""

from __future__ import annotations


def test_tools_package_preserves_legacy_imports() -> None:
    from agentic_systems.tools.compat import Toolkit, ToolEvent, assert_dict_tool_output, expand_tool_inputs, now_ms

    assert Toolkit.__name__ == "Toolkit"
    assert ToolEvent.__name__ == "ToolEvent"
    assert assert_dict_tool_output("demo", {"ok": True}) == {"ok": True}
    assert expand_tool_inputs(None) == ()
    assert isinstance(now_ms(), float)


def test_skills_package_preserves_loader_imports() -> None:
    from agentic_systems.skills import LoadedSkill, SkillManifest, load_skill

    assert LoadedSkill.__name__ == "LoadedSkill"
    assert SkillManifest.__name__ == "SkillManifest"
    assert callable(load_skill)


def test_future_module_slots_are_importable() -> None:
    import agentic_systems.skills.skill as skill_module
    import agentic_systems.tools.decorators as decorators_module
    import agentic_systems.tools.tool as tool_module

    assert tool_module is not None
    assert decorators_module is not None
    assert skill_module is not None
