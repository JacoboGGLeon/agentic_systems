from __future__ import annotations

from agentic_systems.engines.names import SUPPORTED_FRAMEWORKS, LANGGRAPH_ORCHESTRATOR


def test_integrations_langgraph_framework_name_is_public() -> None:
    assert LANGGRAPH_ORCHESTRATOR == 'langgraph'
    assert LANGGRAPH_ORCHESTRATOR in SUPPORTED_FRAMEWORKS
