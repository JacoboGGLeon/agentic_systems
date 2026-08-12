"""Canonical bedrock-runtime engine contracts."""

from __future__ import annotations

import os

import pytest

from agentic_systems import Agent, AgenticSystem, RunResult, tool
from agentic_systems.engines.names import BEDROCK_RUNTIME_ENGINE, canonical_engine_name


def build_system() -> AgenticSystem:
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(model="dummy", region="us-east-1")


@tool
def sumar(a: int, b: int) -> dict:
    """Suma dos enteros."""
    return {"result": a + b}


class EchoBedrockRuntimeEngine:
    name = BEDROCK_RUNTIME_ENGINE

    def run(self, agent, input, policy, *, mode="default"):
        return RunResult(
            text=str(input),
            data={"answer": str(input)},
            ok=True,
            engine=self.name,
            model=agent.model or "dummy",
            mode=mode,
        )


def test_engine_names_keep_one_canonical_cloud_path() -> None:
    assert canonical_engine_name("bedrock-runtime") == BEDROCK_RUNTIME_ENGINE
    with pytest.raises(ValueError, match="Unknown runtime/provider"):
        canonical_engine_name("bedrock_runtime")
    with pytest.raises(ValueError, match="Unknown runtime/provider"):
        canonical_engine_name("bedrock")


def test_system_agent_uses_bedrock_runtime_as_default_engine() -> None:
    system = build_system()
    agent = system.agent(name="cloud_agent", instructions="Echo.", tools=[sumar])

    assert agent.engine == BEDROCK_RUNTIME_ENGINE


def test_relocated_bedrock_runtime_uses_canonical_injected_engine() -> None:
    system = build_system()
    system._engines[BEDROCK_RUNTIME_ENGINE] = EchoBedrockRuntimeEngine()
    agent = system.agent(name="cloud_agent", instructions="Echo.", tools=[sumar], engine=BEDROCK_RUNTIME_ENGINE)

    result = agent.run("hola", mode="eval")

    assert agent.engine == BEDROCK_RUNTIME_ENGINE
    assert result.engine == BEDROCK_RUNTIME_ENGINE
    assert result.data == {"answer": "hola"}


def test_direct_bedrock_runtime_agent_requires_binding_before_run() -> None:
    agent = Agent(name="portable_cloud_agent", tools=[sumar], engine="bedrock-runtime")

    with pytest.raises(RuntimeError, match=r"bind\(system\)"):
        agent.run({"a": 1, "b": 2}, mode="eval")
