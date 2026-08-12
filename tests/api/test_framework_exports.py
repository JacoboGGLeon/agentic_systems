from __future__ import annotations

from agentic_systems.engines.names import (
    LANGGRAPH_ORCHESTRATOR,
    OPENAI_AGENTS_FRAMEWORK,
    STRANDS_FRAMEWORK,
    SUPPORTED_FRAMEWORKS,
)


def test_integrations_langgraph_framework_name_is_public() -> None:
    assert LANGGRAPH_ORCHESTRATOR == "langgraph"
    assert LANGGRAPH_ORCHESTRATOR in SUPPORTED_FRAMEWORKS


def test_integrations_openai_agents_framework_name_is_public() -> None:
    assert OPENAI_AGENTS_FRAMEWORK == "openai-agents"
    assert OPENAI_AGENTS_FRAMEWORK in SUPPORTED_FRAMEWORKS


def test_integrations_strands_framework_name_is_public() -> None:
    assert STRANDS_FRAMEWORK == "strands"
    assert STRANDS_FRAMEWORK in SUPPORTED_FRAMEWORKS
