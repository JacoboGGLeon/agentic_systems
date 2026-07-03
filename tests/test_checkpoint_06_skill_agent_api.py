"""Checkpoint 6: skill-backed agents with the canonical API."""

from __future__ import annotations

import os
from pathlib import Path

from agentic_systems import AgenticSystem, Skill, Tool


def build_system() -> AgenticSystem:
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(model="dummy", region="us-east-1")


def sumar(a: int, b: int) -> dict:
    """Suma dos enteros."""
    return {"result": a + b}


def restar(a: int, b: int) -> dict:
    """Resta dos enteros."""
    return {"result": a - b}


def test_system_agent_accepts_runtime_skill_and_registers_tools() -> None:
    system = build_system()
    skill = Skill(name="math", tools=[sumar, restar])

    agent = system.agent(
        name="math_agent",
        instructions="Usa tools matemáticas.",
        skills=[skill],
        contract={"must_call": ["sumar"]},
    )

    assert agent.skills == ("math",)
    assert agent.tools == ("sumar", "restar")
    assert system.skill_names == ("math",)
    assert [item.name for item in system.runtime_skills] == ["math"]
    assert system.execute_tool("sumar", {"a": 17, "b": 25}).data == {"result": 42}


def test_system_agent_dedupes_tools_from_skills_and_explicit_tools() -> None:
    system = build_system()
    skill = Skill(name="math", tools=[sumar])

    @system.tool
    def dividir(a: int, b: int) -> dict:
        """Divide dos enteros."""
        return {"result": a / b}

    agent = system.agent(
        name="mixed_agent",
        instructions="Usa skills y tools directas.",
        skills=[skill],
        tools=["sumar", "dividir"],
    )

    assert agent.tools == ("sumar", "dividir")
    assert agent.skills == ("math",)


def test_loaded_skill_exposes_runtime_skill_and_can_back_agent() -> None:
    system = build_system()
    skill_path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "skills" / "demo"
    loaded = system.load_skill(skill_path)

    assert loaded.runtime_skill is not None
    assert loaded.runtime_skill.name == "demo"
    assert loaded.runtime_skill.tool_names == tuple(loaded.manifest.tools)

    agent = system.agent(
        name="loaded_skill_agent",
        instructions="Usa la skill demo.",
        skills=[loaded],
    )

    assert agent.skills == ("demo",)
    assert agent.tools == tuple(loaded.manifest.tools)
    assert system.execute_tool("sumar", {"a": 17, "b": 25}).data == {"operation": "sumar", "result": 42}


def test_system_skill_registers_tool_objects_directly() -> None:
    system = build_system()
    skill = Skill(name="tool_object_skill", tools=[Tool(name="sumar_custom", function=sumar)])

    registered = system.skill(skill)

    assert registered is skill
    assert "sumar_custom" in system.tool_names
    assert system.execute_tool("sumar_custom", {"a": 40, "b": 2}).data == {"result": 42}
