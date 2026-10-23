"""Provider-agnostic usage normalization.

The public contract distinguishes facts reported by a provider from timings
measured by Agentic Systems. Missing evidence stays missing in ``RunResult``
and becomes ``None`` only in the stable normalized projection.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .output_contracts import UsageInfo

CANONICAL_USAGE_FIELDS = (
    "requests",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "client_duration_ms",
    "service_latency_ms",
    "duration_ms",
)

_ALIASES: dict[str, tuple[str, ...]] = {
    "requests": ("request_count",),
    "input_tokens": ("prompt_tokens", "inputTokens"),
    "output_tokens": ("completion_tokens", "outputTokens"),
    "total_tokens": ("totalTokens",),
    "service_latency_ms": ("latencyMs",),
}


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def normalize_usage(value: Any) -> dict[str, Any]:
    """Add canonical names while preserving provider-specific evidence."""

    if not isinstance(value, Mapping):
        return {}
    payload = {str(key): item for key, item in value.items()}
    for canonical, aliases in _ALIASES.items():
        if _number(payload.get(canonical)) is not None:
            continue
        for alias in aliases:
            candidate = _number(payload.get(alias))
            if candidate is not None:
                payload[canonical] = candidate
                break

    if _number(payload.get("total_tokens")) is None:
        input_tokens = _number(payload.get("input_tokens"))
        output_tokens = _number(payload.get("output_tokens"))
        if input_tokens is not None and output_tokens is not None:
            payload["total_tokens"] = input_tokens + output_tokens
    return payload


def merge_usage(*items: Any) -> dict[str, Any]:
    """Accumulate several provider responses without losing their aliases."""

    totals: dict[str, Any] = {}
    for item in items:
        for key, value in normalize_usage(item).items():
            number = _number(value)
            if number is not None:
                totals[key] = totals.get(key, 0) + number
            elif key not in totals:
                totals[key] = value
    return normalize_usage(totals)


def usage_view(value: Any) -> dict[str, Any]:
    """Return the stable public shape, retaining truthful extension fields."""

    normalized = normalize_usage(value)
    valid = {
        key: item
        for key, item in normalized.items()
        if key not in CANONICAL_USAGE_FIELDS or _number(item) is not None
    }
    return UsageInfo.model_validate(valid).model_dump(mode="json", exclude_none=True)


__all__ = [
    "CANONICAL_USAGE_FIELDS",
    "merge_usage",
    "normalize_usage",
    "usage_view",
]
