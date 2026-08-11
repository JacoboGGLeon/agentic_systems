"""Checkpoint 8: PythonDirectEngine local execution and output-first ergonomics."""

from __future__ import annotations

import asyncio
import os

from agentic_systems import Agent, AgenticSystem, Skill, tool
from agentic_systems.providers.python_direct import PythonDirectEngine


def build_system() -> AgenticSystem:
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(model="dummy", region="us-east-1")


@tool
def sumar(a: int, b: int) -> dict:
    """Suma dos enteros."""
    return {"result": a + b}


@tool
def multiplicar(a: int, b: int) -> dict:
    """Multiplica dos enteros."""
    return {"result": a * b}


def restar(a: int, b: int) -> dict:
    """Resta dos enteros."""
    return {"result": a - b}


def test_direct_agent_runs_single_tool_without_system_or_credentials() -> None:
    agent = Agent(name="calculator", tools=[sumar], engine="python-runtime")

    result = agent.run({"a": 17, "b": 25})

    assert result.ok is True
    assert result.engine == "python-runtime"
    assert result.data["result"] == 42
    assert result.data["tool"] == "sumar"
    assert result.text.startswith("sumar ->")
    assert [event.name for event in result.tool_events] == ["sumar"]


def test_direct_agent_runs_structured_multi_tool_plan() -> None:
    agent = Agent(name="calculator", tools=[sumar, multiplicar], engine="python-runtime")

    result = agent.run(
        {
            "steps": [
                {"tool": "sumar", "input": {"a": 17, "b": 25}},
                {"tool": "multiplicar", "input": {"a": 42, "b": 3}},
            ]
        }
    )

    assert result.ok is True
    assert result.data["ok"] is True
    assert result.data["last"] == {"result": 126}
    assert [step["tool"] for step in result.data["steps"]] == ["sumar", "multiplicar"]
    assert [event.name for event in result.tool_events] == ["sumar", "multiplicar"]


def test_python_direct_returns_helpful_failure_for_natural_language_multi_tool_prompt() -> None:
    agent = Agent(name="calculator", tools=[sumar, multiplicar], engine="python-runtime")

    result = agent.run("suma 17 y 25")

    assert result.ok is False
    assert result.engine == "python-runtime"
    assert "does not parse natural language" in result.text
    assert result.data["error"]["code"] == "ValueError"


def test_system_agent_can_select_python_direct_engine_with_runtime_skill() -> None:
    system = build_system()
    skill = Skill(name="math", tools=[sumar, restar])
    agent = system.agent(
        name="local_math_agent",
        instructions="Ejecuta tools locales.",
        skills=[skill],
        engine="python-runtime",
    )

    result = agent.run({"tool": "restar", "input": {"a": 100, "b": 58}})

    assert isinstance(system._engine("python-runtime"), PythonDirectEngine)
    assert result.ok is True
    assert result.data["result"] == 42
    assert result.data["tool"] == "restar"


def test_direct_agent_async_python_direct_run() -> None:
    agent = Agent(name="calculator", tools=[sumar], engine="python-runtime")

    result = asyncio.run(agent.arun({"a": 20, "b": 22}))

    assert result.ok is True
    assert result.data["result"] == 42
