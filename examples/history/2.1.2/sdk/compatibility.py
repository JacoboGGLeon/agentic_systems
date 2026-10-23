"""Framework/provider compatibility inventory for Agentic Systems 2.1."""

from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass
from .core.runtime import (
    _bedrock_signal_present,
    _load_dotenv,
    _ollama_signal_present,
    _openai_signal_present,
    _vllm_signal_present,
)
from .registry import (
    FRAMEWORK_NAMES,
    PROVIDER_NAMES,
    framework_definition,
    matrix_contract,
    provider_definition,
)


@dataclass(frozen=True)
class CompatibilityCase:
    provider: str
    framework: str
    offline_certified: bool
    ready: bool
    status: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def compatibility_matrix() -> tuple[CompatibilityCase, ...]:
    """Return all twenty supported framework/provider combinations."""

    _load_dotenv()
    return tuple(
        _case(provider, framework)
        for provider in PROVIDER_NAMES
        for framework in FRAMEWORK_NAMES
    )


def compatibility_report() -> dict[str, object]:
    cases = compatibility_matrix()
    return {
        "schema_version": "agentic_systems.compatibility.v2",
        "providers": list(PROVIDER_NAMES),
        "frameworks": list(FRAMEWORK_NAMES),
        "combination_count": len(cases),
        "offline_certified": all(case.offline_certified for case in cases),
        "ready_count": sum(case.ready for case in cases),
        "cases": [case.to_dict() for case in cases],
    }


def _case(provider: str, framework: str) -> CompatibilityCase:
    contract = matrix_contract(provider, framework)
    dependency = framework_definition(framework).dependency
    if dependency and importlib.util.find_spec(dependency) is None:
        return CompatibilityCase(
            provider,
            framework,
            True,
            False,
            "missing-dependency",
            f"Install the optional dependency for {framework}.",
        )

    provider_dependency = provider_definition(provider).dependency
    if provider_dependency and importlib.util.find_spec(provider_dependency) is None:
        return CompatibilityCase(
            provider,
            framework,
            True,
            False,
            "missing-dependency",
            f"Install the optional dependency for {provider}.",
        )

    configured = {
        "python-runtime": True,
        "openai-runtime": _openai_signal_present(),
        "ollama-runtime": _ollama_signal_present(),
        "vllm-runtime": _vllm_signal_present(),
        "bedrock-runtime": _bedrock_signal_present(None),
    }[provider]
    if not configured:
        return CompatibilityCase(
            provider,
            framework,
            contract.status != "unsupported",
            False,
            "needs-configuration",
            f"Configure {provider} before live execution.",
        )
    return CompatibilityCase(
        provider,
        framework,
        contract.status != "unsupported",
        True,
        "ready",
        "Offline contract certified and runtime signals available.",
    )


__all__ = [
    "CompatibilityCase",
    "FRAMEWORK_NAMES",
    "PROVIDER_NAMES",
    "compatibility_matrix",
    "compatibility_report",
]
