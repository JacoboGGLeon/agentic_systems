"""Direct Agent API contracts."""

from __future__ import annotations

import os

from agentic_systems import Agent, AgenticSystem, RunResult, Skill, Tool, tool


def build_system() -> AgenticSystem:
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(model="dummy", region="us-east-1")


def sumar(a: int, b: int) -> dict:
    """Suma dos enteros."""
    return {"result": a + b}


@tool
def restar(a: int, b: int) -> dict:
    """Resta dos enteros."""
    return {"result": a - b}


class EchoEngine:
    name = "bedrock-runtime"

    def run(self, agent, input, policy, *, mode="default"):
        return RunResult(text=str(input), data={"answer": str(input)}, ok=True, engine=self.name, model=agent.model or "dummy", mode=mode)

    async def arun(self, agent, input, policy, *, mode="default"):
        return self.run(agent, input, policy, mode=mode)


def test_direct_agent_accepts_tools_and_skills_without_system() -> None:
    math_skill = Skill(name="math", tools=[sumar])
    agent = Agent(
        name="calculator_agent",
        instructions="Usa herramientas exactas.",
        tools=[restar],
        skills=[math_skill],
        contract={"must_call": ["sumar"]},
    )

    assert agent.system is None
    assert agent.tools == ("sumar", "restar")
    assert agent.skills == ("math",)
    assert agent.check().ok is True
    assert [item.name for item in agent.available_tools()] == ["sumar", "restar"]
    assert agent.info()["has_system"] is False
    assert agent.info()["direct_tool_count"] == 2


def test_direct_agent_defaults_to_bedrock_runtime_and_requires_binding() -> None:
    agent = Agent(name="direct_only", tools=[sumar])

    assert agent.engine == "bedrock-runtime"
    try:
        agent.run({"a": 1, "b": 2})
    except RuntimeError as exc:
        assert "bind(system)" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Unbound bedrock-runtime agent should not run locally")


def test_direct_agent_bind_registers_tools_and_preserves_compat_system_agent() -> None:
    system = build_system()
    direct_agent = Agent(
        name="calculator_agent",
        instructions="Usa tools matemáticas.",
        tools=[Tool(name="sumar_custom", function=sumar)],
        skills=[Skill(name="math", tools=[restar])],
    )

    bound = direct_agent.bind(system)

    assert bound.system is system
    assert bound.tools == ("restar", "sumar_custom")
    assert bound.skills == ("math",)
    assert "restar" in system.tool_names
    assert "sumar_custom" in system.tool_names
    assert system.execute_tool("sumar_custom", {"a": 17, "b": 25}).data == {"result": 42}


def test_system_agent_accepts_tool_objects_and_still_runs_with_existing_engine_path() -> None:
    system = build_system()
    system._engines["bedrock-runtime"] = EchoEngine()

    agent = system.agent(
        name="echo_agent",
        instructions="Echo.",
        tools=[Tool(name="sumar_object", function=sumar)],
    )

    assert agent.system is system
    assert agent.tools == ("sumar_object",)
    assert system.execute_tool("sumar_object", {"a": 20, "b": 22}).data == {"result": 42}
    assert agent.run("hola", mode="eval").data == {"answer": "hola"}
