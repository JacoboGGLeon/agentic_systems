from __future__ import annotations

from agentic_systems.engines.names import SUPPORTED_FRAMEWORKS, OPENAI_AGENTS_FRAMEWORK


def test_integrations_openai_agents_framework_name_is_public() -> None:
    assert OPENAI_AGENTS_FRAMEWORK == 'openai-agents'
    assert OPENAI_AGENTS_FRAMEWORK in SUPPORTED_FRAMEWORKS
