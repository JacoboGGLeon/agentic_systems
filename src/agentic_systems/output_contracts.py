"""Canonical output contracts for Agentic Systems.

The models in this module are intentionally runtime-agnostic. Bedrock,
python-runtime, LangGraph, evals, skills and environments should adapt into the
same small envelope instead of inventing notebook-specific shapes.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AGENTIC_OUTPUT_SCHEMA_VERSION = "agentic_systems.output.v1"

OutputKind = Literal[
    "tool", "agent", "skill", "system", "graph", "environment", "eval", "chain"
]


class RuntimeInfo(BaseModel):
    """Runtime/backend metadata. Runtime is metadata, not an output contract."""

    model_config = ConfigDict(extra="allow")

    provider: str | None = None
    engine: str | None = None
    mode: str | None = None
    model: str | None = None


class UsageInfo(BaseModel):
    """Comparable usage evidence across providers.

    ``service_latency_ms`` is provider-reported. ``client_duration_ms`` may be
    measured around the provider/framework call by Agentic Systems.
    """

    model_config = ConfigDict(extra="allow")

    requests: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    service_latency_ms: float | None = None
    client_duration_ms: float | None = None
    duration_ms: float | None = None


class OutputToolEvent(BaseModel):
    """Normalized tool evidence used by every notebook/output view."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    ok: bool | None = None
    input: Any = Field(default_factory=dict)
    output: Any = Field(default_factory=dict)
    error: Any | None = None


class OutputValidation(BaseModel):
    """Validation outcome for the output contract and/or business contract."""

    model_config = ConfigDict(extra="allow")

    ok: bool | None = None
    issues: list[Any] = Field(default_factory=list)


class TraceEvent(BaseModel):
    """Optional compact trace event. Hidden by default in notebooks."""

    model_config = ConfigDict(extra="allow")

    name: str | None = None
    kind: str | None = None
    payload: Any = None


class GraphStateOutput(BaseModel):
    """Portable graph state envelope for LangGraph or invoke(state) adapters."""

    model_config = ConfigDict(extra="allow")

    selected_agent: str | None = None
    plan: dict[str, Any] = Field(default_factory=dict)
    agent_output: dict[str, Any] | None = None


class EpisodeResult(BaseModel):
    """Environment episode summary."""

    model_config = ConfigDict(extra="allow")

    name: str | None = None
    episode_id: str | None = None
    steps_done: int | None = None
    total_records: int | None = None
    reward_total: float | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)


class AgenticOutput(BaseModel):
    """Universal output envelope returned by adapters and notebook summaries."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = AGENTIC_OUTPUT_SCHEMA_VERSION
    kind: OutputKind | str = "agent"
    ok: bool | None = None
    answer: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    data: Any = Field(default_factory=dict)
    tools: list[OutputToolEvent] = Field(default_factory=list)
    runtime: RuntimeInfo = Field(default_factory=RuntimeInfo)
    usage: dict[str, Any] = Field(default_factory=dict)
    validation_ok: bool | None = None
    validation: OutputValidation = Field(default_factory=OutputValidation)
    trace: list[Any] = Field(default_factory=list)

    def compact_dict(self, *, include_empty: bool = True) -> dict[str, Any]:
        """Return a JSON-ready dict, optionally dropping empty optional fields."""

        payload = self.model_dump(mode="json")
        if include_empty:
            return payload
        return {
            key: value
            for key, value in payload.items()
            if value not in ({}, [], "", None)
        }


__all__ = [
    "AGENTIC_OUTPUT_SCHEMA_VERSION",
    "AgenticOutput",
    "EpisodeResult",
    "GraphStateOutput",
    "OutputKind",
    "OutputToolEvent",
    "OutputValidation",
    "RuntimeInfo",
    "TraceEvent",
    "UsageInfo",
]
