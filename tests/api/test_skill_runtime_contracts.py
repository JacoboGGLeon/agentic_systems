"""Tests for the public runtime Skill API."""

from __future__ import annotations

import json
from pathlib import Path

from agentic_systems import AgenticSystem, Skill, Tool, tool
from agentic_systems.skills import LoadedSkill, SkillManifest, load_skill


def sumar(a: int, b: int) -> dict:
    """Suma dos enteros."""
    return {"result": a + b}


def restar(a: int, b: int) -> dict:
    """Resta b a a."""
    return {"result": a - b}


@tool
def multiplicar(a: int, b: int) -> dict:
    """Multiplica dos enteros."""
    return {"result": a * b}


def test_skill_holds_tools() -> None:
    sumar_tool = Tool(name="sumar", function=sumar)
    skill = Skill(name="math", tools=[sumar_tool, multiplicar])

    assert skill.tool_names == ("sumar", "multiplicar")
    assert len(skill) == 2
    assert [item.name for item in skill] == ["sumar", "multiplicar"]


def test_skill_holds_prompts() -> None:
    skill = Skill(
        name="demo",
        description="Skill demo.",
        tools=[sumar],
        prompts={"math_agent": "Usa tools para cálculo."},
        contracts={"expected_output": {"result": 42}},
        policy={"tool_choice": "required", "temperature": 0.0, "max_tool_calls": 12},
    )

    info = skill.info()
    assert info["prompts"] == {"math_agent": "Usa tools para cálculo."}
    assert info["contracts"] == {"expected_output": {"result": 42}}
    assert info["policy"]["max_tool_calls"] == 12
    assert skill.describe().startswith("Skill `demo`: Skill demo.")


def test_skill_check_catches_duplicate_tool_names() -> None:
    skill = Skill(name="duplicates", tools=[sumar, Tool(name="sumar", function=restar)])

    validation = skill.check()
    assert validation.ok is False
    assert any(issue.code == "duplicate_tool_name" for issue in validation.issues)


def test_skill_info_is_serializable() -> None:
    skill = Skill(
        name="serializable",
        tools=[sumar, multiplicar],
        prompts={"path_like": Path("prompts/math_agent.md")},
        metadata={"owner": "tutorial"},
    )

    payload = skill.info()
    encoded = json.dumps(payload, ensure_ascii=False)
    assert '"name": "serializable"' in encoded
    assert payload["prompts"] == {"path_like": str(Path("prompts/math_agent.md"))}


def test_skill_available_tools_returns_direct_tools() -> None:
    sumar_tool = Tool(name="sumar", function=sumar)
    skill = Skill(name="math", tools=[sumar_tool])

    tools = skill.available_tools()
    assert tools == [sumar_tool]
    assert isinstance(tools[0], Tool)
    tools.append(Tool(name="restar", function=restar))
    assert skill.tool_names == ("sumar",)


def test_skill_can_be_created_from_demo_tutorial_tools() -> None:
    skill = Skill(
        name="demo",
        description="Skill demo de cálculo, verbalización y lectura markdown.",
        tools=[sumar, restar, multiplicar],
        prompts={"math_agent": "..."},
        policy={"tool_choice": "required", "temperature": 0.0, "max_tool_calls": 12},
    )

    assert skill.check().ok is True
    assert skill.tool_names == ("sumar", "restar", "multiplicar")
    assert [tool.name for tool in skill.available_tools()] == list(skill.tool_names)


def test_compatibility_skill_loader_imports_and_loads() -> None:
    assert SkillManifest.__name__ == "SkillManifest"
    assert LoadedSkill.__name__ == "LoadedSkill"
    assert callable(load_skill)

    system = AgenticSystem(model="dummy", region="us-east-1")
    skill_path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "skills" / "demo"
    loaded = system.load_skill(skill_path)

    assert loaded.manifest.name == "demo"
    assert "sumar" in system.tool_names
