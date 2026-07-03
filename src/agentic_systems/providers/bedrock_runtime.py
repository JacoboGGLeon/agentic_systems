"""Bedrock Runtime provider facade.

Checkpoint 0 keeps the mature implementation in ``engines.bedrock_runtime`` and
exposes it here as the provider namespace. Imports are lazy so the core package
can be imported without AWS dependencies until this provider is actually used.
"""

from __future__ import annotations

from typing import Any

_INSTALL_HINT = "Install with: pip install -e '.[bedrock]'"


def _bedrock_module() -> Any:
    try:
        from agentic_systems.engines import bedrock_runtime as module
    except Exception as exc:  # pragma: no cover - depends on optional install
        raise ImportError(f"Bedrock Runtime provider requires optional AWS dependencies. {_INSTALL_HINT}.") from exc
    return module


def __getattr__(name: str) -> Any:
    module = _bedrock_module()
    try:
        return getattr(module, name)
    except AttributeError as exc:  # pragma: no cover - standard module behavior
        raise AttributeError(name) from exc


__all__ = [
    "BedrockRuntime",
    "BedrockRunResult",
    "RuntimeToolCallRecord",
    "RuntimeToolSpec",
    "ToolEnvelope",
]
