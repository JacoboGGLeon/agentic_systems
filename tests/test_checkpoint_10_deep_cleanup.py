from __future__ import annotations

import inspect

import agentic_systems as api
from agentic_systems.api import BEDROCK_PRIMITIVE_API, CHAIN_API, CORE_API, ENGINE_API, NOTEBOOK_API, PUBLIC_API
from agentic_systems.engines.names import BEDROCK_RUNTIME_ENGINE, PYTHON_DIRECT_ENGINE, supported_engine_names


def test_top_level_exports_are_intentional_and_grouped() -> None:
    assert tuple(api.__all__) == PUBLIC_API
    assert "AgenticSystem" in CORE_API
    assert "Skill" in CORE_API
    assert "Toolkit" not in PUBLIC_API
    assert "BedrockRuntimeClient" in BEDROCK_PRIMITIVE_API
    assert "Chain" in CHAIN_API
    assert "run_result_view" in NOTEBOOK_API
    assert "BEDROCK_RUNTIME_ENGINE" in ENGINE_API


def test_engine_constants_are_public_but_aliases_stay_out_of_supported_names() -> None:
    assert api.BEDROCK_RUNTIME_ENGINE == BEDROCK_RUNTIME_ENGINE
    assert api.PYTHON_DIRECT_ENGINE == PYTHON_DIRECT_ENGINE
    assert "bedrock" not in supported_engine_names(include_aliases=False)
    assert "bedrock" in supported_engine_names(include_aliases=True)


def test_compatibility_helpers_are_quarantined_to_explicit_module() -> None:
    from agentic_systems.tools.compat import Toolkit, ToolEvent

    assert not hasattr(api, "Toolkit")
    assert not hasattr(api, "ToolEvent")
    assert ToolEvent.__name__ == "ToolEvent"


def test_system_agent_canonicalizes_engine_once_without_private_wrapper() -> None:
    from agentic_systems.system import AgenticSystem

    source = inspect.getsource(AgenticSystem.agent)
    assert "_canonical_engine_name" not in source
    assert source.count("canonical_engine_name(engine)") == 1
