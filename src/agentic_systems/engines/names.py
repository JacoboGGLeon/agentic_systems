"""Canonical engine names and compatibility aliases for Agentic Systems."""

from __future__ import annotations

from typing import Iterable

BEDROCK_RUNTIME_ENGINE = "bedrock-runtime"
OPENAI_RUNTIME_ENGINE = "openai-runtime"
PYTHON_DIRECT_ENGINE = "python-runtime"
VLLM_RUNTIME_ENGINE = "vllm-runtime"
LANGGRAPH_ORCHESTRATOR = "langgraph"
OPENAI_AGENTS_FRAMEWORK = "openai-agents"
STRANDS_FRAMEWORK = "strands"

SUPPORTED_ENGINES = (
    BEDROCK_RUNTIME_ENGINE,
    OPENAI_RUNTIME_ENGINE,
    PYTHON_DIRECT_ENGINE,
    VLLM_RUNTIME_ENGINE,
)

SUPPORTED_FRAMEWORKS = (
    LANGGRAPH_ORCHESTRATOR,
    OPENAI_AGENTS_FRAMEWORK,
    STRANDS_FRAMEWORK,
)

# Central compatibility map. Public docs/notebooks should use canonical names.
COMPAT_ENGINE_ALIASES: dict[str, str] = {
    "bedrock": BEDROCK_RUNTIME_ENGINE,
    BEDROCK_RUNTIME_ENGINE: BEDROCK_RUNTIME_ENGINE,
    OPENAI_RUNTIME_ENGINE: OPENAI_RUNTIME_ENGINE,
    PYTHON_DIRECT_ENGINE: PYTHON_DIRECT_ENGINE,
    "vllm": VLLM_RUNTIME_ENGINE,
    VLLM_RUNTIME_ENGINE: VLLM_RUNTIME_ENGINE,
}


def normalize_engine_text(value: str) -> str:
    """Normalize user input before alias resolution."""

    return str(value).strip().lower().replace("_", "-")


def canonical_engine_name(value: str | None, *, default: str | None = None) -> str:
    """Return the stable engine identifier.

    Use canonical names in new code: ``bedrock-runtime``, ``openai-runtime``,
    ``python-runtime`` and ``vllm-runtime``.
    """

    if value is None or str(value).strip() == "":
        if default is None:
            raise ValueError("Engine name must be non-empty.")
        value = default
    text = normalize_engine_text(value)
    return COMPAT_ENGINE_ALIASES.get(text, text)


def supported_engine_names(*, include_langgraph: bool = False, include_aliases: bool = False) -> tuple[str, ...]:
    """Return supported engine names for errors and diagnostics."""

    names: Iterable[str] = SUPPORTED_ENGINES
    if include_langgraph:
        names = (*SUPPORTED_ENGINES, LANGGRAPH_ORCHESTRATOR)
    if include_aliases:
        names = (*names, *(alias for alias in COMPAT_ENGINE_ALIASES if alias not in names))
    return tuple(names)
