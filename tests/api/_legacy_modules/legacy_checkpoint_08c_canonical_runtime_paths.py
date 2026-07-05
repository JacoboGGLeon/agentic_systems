"""Checkpoint 8c: canonical runtime paths with safe compatibility relocation."""

from __future__ import annotations

import os

import pytest

from agentic_systems import Agent, AgenticSystem, tool
from agentic_systems.providers.python_direct import PythonDirectEngine
from agentic_systems.engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    PYTHON_DIRECT_ENGINE,
    VLLM_RUNTIME_ENGINE,
    canonical_engine_name,
    supported_engine_names,
)
from agentic_systems.tools.compat import ToolEvent as CompatToolEvent
from agentic_systems.tools.compat import ToolEvent as RelocatedToolEvent


def build_system() -> AgenticSystem:
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(model="dummy", region="us-east-1")


@tool
def sumar(a: int, b: int) -> dict:
    """Suma dos enteros."""

    return {"result": a + b}


def test_direct_agent_default_is_cloud_configuration_not_local_execution() -> None:
    agent = Agent(name="portable_agent", tools=[sumar])

    assert agent.engine == BEDROCK_RUNTIME_ENGINE
    with pytest.raises(RuntimeError, match=r"bind\(system\)"):
        agent.run({"a": 1, "b": 2}, mode="eval")


def test_python_direct_is_explicit_smoke_test_engine() -> None:
    agent = Agent(name="local_smoke", tools=[sumar], engine=PYTHON_DIRECT_ENGINE)

    result = agent.run({"tool": "sumar", "input": {"a": 17, "b": 25}}, mode="eval")

    assert result.ok is True
    assert result.engine == PYTHON_DIRECT_ENGINE
    assert result.data["result"] == 42


def test_ambiguous_local_aliases_are_not_engine_shortcuts() -> None:
    for value in ("local", "runtime", "python_runtime", "vllm", "vllm_runtime"):
        with pytest.raises(ValueError, match="Unknown runtime/provider"):
            canonical_engine_name(value)


def test_supported_engine_names_show_canonical_surface_only() -> None:
    assert supported_engine_names() == (BEDROCK_RUNTIME_ENGINE, "openai-runtime", PYTHON_DIRECT_ENGINE, VLLM_RUNTIME_ENGINE)
    assert "bedrock" not in supported_engine_names()


def test_relocated_tool_compat_path_keeps_old_imports_safe() -> None:
    assert RelocatedToolEvent is CompatToolEvent


def test_system_can_still_opt_into_python_direct_by_canonical_name() -> None:
    system = build_system()
    agent = system.agent(
        name="local_system_smoke",
        instructions="Ejecuta un plan estructurado.",
        tools=[sumar],
        engine=PYTHON_DIRECT_ENGINE,
    )

    result = agent.run({"tool": "sumar", "input": {"a": 20, "b": 22}}, mode="eval")

    assert isinstance(system._engine(PYTHON_DIRECT_ENGINE), PythonDirectEngine)
    assert result.ok is True
    assert result.data["result"] == 42
