"""Provider namespace for Agentic Systems.

Providers answer: where does a model/runtime call execute?  The base package is
safe to import without cloud dependencies; provider-specific dependencies are
loaded only when their module/class is used.
"""

from __future__ import annotations

from typing import Any

from .base import RuntimeToolSpec, ToolEnvelope, ToolRegistryRuntime
from .conformance import (
    OPTIONAL_PROVIDER_CAPABILITIES,
    PROVIDER_CONFORMANCE_SCHEMA_VERSION,
    REQUIRED_PROVIDER_CAPABILITIES,
    CapabilityDeclaration,
    ProviderConformanceReport,
    ProviderProfile,
    evaluate_provider_conformance,
    provider_profile,
    provider_profiles,
)
from .python_runtime import PythonRuntimeEngine, PythonRuntimeProvider
from .openai_runtime import OpenAIRuntimeProvider, openai_environment_snapshot
from .ollama_runtime import OllamaRuntimeProvider
from .vllm_runtime import VLLMRuntimeProvider

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
    "PROVIDER_CONFORMANCE_SCHEMA_VERSION",
    "REQUIRED_PROVIDER_CAPABILITIES",
    "OPTIONAL_PROVIDER_CAPABILITIES",
    "CapabilityDeclaration",
    "ProviderProfile",
    "ProviderConformanceReport",
    "provider_profile",
    "provider_profiles",
    "evaluate_provider_conformance",
    "PythonRuntimeEngine",
    "PythonRuntimeProvider",
    "OpenAIRuntimeProvider",
    "openai_environment_snapshot",
    "OllamaRuntimeProvider",
    "VLLMRuntimeProvider",
    "BedrockRuntime",
    "BedrockRunResult",
    "RuntimeToolCallRecord",
]
