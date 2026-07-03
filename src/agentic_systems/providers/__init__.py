"""Provider namespace for Agentic Systems.

Providers answer: where does a model/runtime call execute?  The base package is
safe to import without cloud dependencies; provider-specific dependencies are
loaded only when their module/class is used.
"""

from __future__ import annotations

from typing import Any

from .base import RuntimeToolSpec, ToolEnvelope, ToolRegistryRuntime
from .python_direct import PythonDirectEngine, PythonDirectProvider
from .openai_runtime import OpenAIRuntimeProvider

_LAZY = {
    "BedrockRuntime": ("agentic_systems.providers.bedrock_runtime", "BedrockRuntime"),
    "BedrockRunResult": ("agentic_systems.providers.bedrock_runtime", "BedrockRunResult"),
    "RuntimeToolCallRecord": ("agentic_systems.providers.bedrock_runtime", "RuntimeToolCallRecord"),
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY:
        raise AttributeError(name)
    module_name, attr_name = _LAZY[name]
    module = __import__(module_name, fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = [
    "RuntimeToolSpec",
    "ToolEnvelope",
    "ToolRegistryRuntime",
    "PythonDirectEngine",
    "PythonDirectProvider",
    "OpenAIRuntimeProvider",
    "BedrockRuntime",
    "BedrockRunResult",
    "RuntimeToolCallRecord",
]
