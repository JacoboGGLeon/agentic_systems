from __future__ import annotations

from agentic_systems.engines.names import SUPPORTED_FRAMEWORKS, STRANDS_FRAMEWORK


def test_integrations_strands_framework_name_is_public() -> None:
    assert STRANDS_FRAMEWORK == 'strands'
    assert STRANDS_FRAMEWORK in SUPPORTED_FRAMEWORKS
