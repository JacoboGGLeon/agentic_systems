"""Lazy Framework adapter registry."""

from __future__ import annotations

from importlib import import_module

from ..config import NATIVE_FRAMEWORK
from .base import FrameworkAdapter


_ADAPTERS = {
    NATIVE_FRAMEWORK: (
        "agentic_systems._engine.integrations.adapters.native",
        "NativeFrameworkAdapter",
    ),
    "langgraph": (
        "agentic_systems._engine.integrations.adapters.langgraph",
        "LangGraphFrameworkAdapter",
    ),
    "openai-agents": (
        "agentic_systems._engine.integrations.adapters.openai_agents",
        "OpenAIAgentsFrameworkAdapter",
    ),
    "strands": (
        "agentic_systems._engine.integrations.adapters.strands",
        "StrandsFrameworkAdapter",
    ),
}


def framework_adapter(name: str) -> FrameworkAdapter:
    """Return a fresh adapter without importing unrelated optional SDKs."""

    try:
        module_name, class_name = _ADAPTERS[name]
    except KeyError as exc:
        available = ", ".join(_ADAPTERS)
        raise ValueError(
            f"Unknown framework adapter {name!r}. Use one of: {available}."
        ) from exc
    module = import_module(module_name)
    return getattr(module, class_name)()
