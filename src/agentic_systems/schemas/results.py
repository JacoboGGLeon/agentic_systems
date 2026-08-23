"""Typed projections for normalized execution evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ContractModel, JsonValue


class RuntimeIdentity(ContractModel):
    provider: str
    framework: str
    model: str = ""
    mode: str = "default"


class UsageInfo(ContractModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    requests: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    extra: dict[str, JsonValue] = Field(default_factory=dict)


class ExecutionError(ContractModel):
    category: Literal[
        "authentication",
        "authorization",
        "configuration",
        "invalid_request",
        "rate_limit",
        "timeout",
        "transient",
        "unsupported",
        "provider",
        "framework",
        "internal",
    ]
    message: str
    provider: str
    framework: str
    code: str | None = None
    retryable: bool = False
    cause_type: str | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict)


class ReasoningMetadata(ContractModel):
    present: bool = False
    format: str | None = None
    removed_from_public_text: bool = False


class ToolEvent(ContractModel):
    id: str | None = None
    name: str
    ok: bool
    input: dict[str, JsonValue] = Field(default_factory=dict)
    output: JsonValue = None
    error: ExecutionError | None = None


class NormalizedModelOutput(ContractModel):
    answer_text: str = ""
    structured_output: JsonValue = None
    reasoning: ReasoningMetadata = Field(default_factory=ReasoningMetadata)
    tool_events: tuple[ToolEvent, ...] = ()
    usage: UsageInfo = Field(default_factory=UsageInfo)
    errors: tuple[ExecutionError, ...] = ()
    raw_evidence: tuple[dict[str, JsonValue], ...] = ()


__all__ = [
    "ExecutionError",
    "NormalizedModelOutput",
    "ReasoningMetadata",
    "RuntimeIdentity",
    "ToolEvent",
    "UsageInfo",
]
