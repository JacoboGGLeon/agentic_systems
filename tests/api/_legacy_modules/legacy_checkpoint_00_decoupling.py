"""Checkpoint 0: core/providers/integrations decoupling."""

from __future__ import annotations

from pathlib import Path

import agentic_systems as lab
from agentic_systems.providers.base import ToolRegistryRuntime

LEGACY_AGENTS_DEP = "openai" + "-agents"


def test_public_namespaces_are_available() -> None:
    assert lab.core.RunResult is lab.RunResult
    assert lab.providers.ToolRegistryRuntime is ToolRegistryRuntime
    assert hasattr(lab.integrations, "__all__")


def test_python_direct_agent_does_not_require_bedrock_runtime_hydration() -> None:
    @lab.tool
    def add(a: int, b: int) -> dict:
        """Add two numbers."""
        return {"result": a + b}

    agent = lab.agent(name="calculator", instructions="Run the selected tool.", tools=[add], engine="python-direct")

    assert isinstance(agent.system._runtime, ToolRegistryRuntime)
    result = agent.run({"tool": "add", "input": {"a": 2, "b": 3}}, mode="eval")

    assert result.ok is True
    assert result.data["result"] == 5
    assert isinstance(agent.system._runtime, ToolRegistryRuntime)


def test_pyproject_keeps_frameworks_and_aws_as_extras() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    base_deps = text.split("[project.optional-dependencies]", 1)[0]

    assert "langgraph" not in base_deps
    assert LEGACY_AGENTS_DEP not in base_deps
    assert "awswrangler" not in base_deps
    assert "boto3" not in base_deps
    assert "bedrock =" in text
    assert "langgraph =" in text
    assert LEGACY_AGENTS_DEP not in text
