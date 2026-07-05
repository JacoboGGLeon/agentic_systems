"""Canonical runtime/provider names for Agentic Systems."""

from __future__ import annotations

from typing import Iterable

BEDROCK_RUNTIME_ENGINE = "bedrock-runtime"
OPENAI_RUNTIME_ENGINE = "openai-runtime"
PYTHON_RUNTIME_ENGINE = "python-runtime"
VLLM_RUNTIME_ENGINE = "vllm-runtime"
AUTO_RUNTIME_SELECTOR = "auto"
LANGGRAPH_ORCHESTRATOR = "langgraph"
OPENAI_AGENTS_FRAMEWORK = "openai-agents"
STRANDS_FRAMEWORK = "strands"

# Internal implementation alias. Public docs and notebooks should use
# PYTHON_RUNTIME_ENGINE / "python-runtime".
PYTHON_DIRECT_ENGINE = PYTHON_RUNTIME_ENGINE

SUPPORTED_ENGINES = (
    BEDROCK_RUNTIME_ENGINE,
    OPENAI_RUNTIME_ENGINE,
    PYTHON_RUNTIME_ENGINE,
    VLLM_RUNTIME_ENGINE,
)

SUPPORTED_RUNTIME_SELECTORS = (
    AUTO_RUNTIME_SELECTOR,
    *SUPPORTED_ENGINES,
)

SUPPORTED_FRAMEWORKS = (
    LANGGRAPH_ORCHESTRATOR,
    OPENAI_AGENTS_FRAMEWORK,
    STRANDS_FRAMEWORK,
)


def normalize_engine_text(value: str) -> str:
    """Normalize casing and surrounding whitespace without accepting aliases."""

    return str(value).strip().lower()


def canonical_engine_name(value: str | None, *, default: str | None = None) -> str:
    """Return a supported runtime/provider identifier.

    Use canonical names in new code: ``python-runtime``, ``bedrock-runtime``,
    ``openai-runtime``, ``vllm-runtime`` or ``auto``.
    """

    if value is None or str(value).strip() == "":
        if default is None:
            raise ValueError("Engine name must be non-empty.")
        value = default
    text = normalize_engine_text(value)
    if text not in SUPPORTED_RUNTIME_SELECTORS:
        supported = ", ".join(SUPPORTED_RUNTIME_SELECTORS)
        raise ValueError(f"Unknown runtime/provider {value!r}. Use one of: {supported}.")
    return text


def supported_engine_names(*, include_langgraph: bool = False, include_aliases: bool = False) -> tuple[str, ...]:
    """Return supported canonical runtime/provider names for errors and diagnostics.

    ``include_aliases`` is retained as a no-op keyword for old internal callers;
    Agentic Systems no longer exposes runtime aliases.
    """

    names: Iterable[str] = SUPPORTED_ENGINES
    if include_langgraph:
        names = (*SUPPORTED_ENGINES, LANGGRAPH_ORCHESTRATOR)
    return tuple(names)
