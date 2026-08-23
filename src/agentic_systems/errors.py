"""Stable errors and provider-neutral retry classification."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


_TRANSIENT_STATUS_CODES = frozenset({408, 409, 425, 429, 500, 502, 503, 504})
_REDACTION_PATTERNS = (
    re.compile(
        r"(?i)(api[-_ ]?key|authorization|bearer|token|secret)\s*[:=]\s*([^\s,;]+)"
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)


def redact_sensitive_text(value: object) -> str:
    """Return an exception-safe message with common credential shapes removed."""

    text = str(value)
    text = _REDACTION_PATTERNS[0].sub(r"\1=[REDACTED]", text)
    return _REDACTION_PATTERNS[1].sub("[REDACTED]", text)


def exception_status_code(exc: BaseException) -> int | None:
    """Extract a conventional HTTP status without importing an SDK."""

    for candidate in (
        getattr(exc, "status_code", None),
        getattr(getattr(exc, "response", None), "status_code", None),
    ):
        if isinstance(candidate, int):
            return candidate
    response = getattr(exc, "response", None)
    if isinstance(response, Mapping):
        candidate = response.get("status_code") or response.get("StatusCode")
        if isinstance(candidate, int):
            return candidate
        metadata = response.get("ResponseMetadata")
        if isinstance(metadata, Mapping) and isinstance(
            metadata.get("HTTPStatusCode"), int
        ):
            return int(metadata["HTTPStatusCode"])
    return None


def classify_exception_category(exc: BaseException) -> str:
    """Classify common SDK failures without depending on concrete SDK classes."""

    status = exception_status_code(exc)
    name = type(exc).__name__.lower()
    if isinstance(exc, TimeoutError) or status in {408, 504} or "timeout" in name:
        return "timeout"
    if status == 429 or "throttl" in name or "ratelimit" in name:
        return "rate_limit"
    if status == 401 or "authentication" in name or "unauthorized" in name:
        return "authentication"
    if status == 403 or "accessdenied" in name or "permission" in name:
        return "authorization"
    if status is not None and status >= 500:
        return "transient"
    if isinstance(exc, (ConnectionError, ConnectionResetError)):
        return "transient"
    if status is not None and 400 <= status < 500:
        return "invalid_request"
    return "provider"


def is_transient_exception(exc: BaseException) -> bool:
    """Return whether an exception is safe to retry under the shared policy."""

    status = exception_status_code(exc)
    return status in _TRANSIENT_STATUS_CODES or classify_exception_category(exc) in {
        "rate_limit",
        "timeout",
        "transient",
    }


def execution_error_payload(
    exc: BaseException,
    *,
    provider: str,
    framework: str,
    code: str | None = None,
    retryable: bool | None = None,
) -> dict[str, Any]:
    """Normalize an external exception into the public execution error shape."""

    status = exception_status_code(exc)
    payload: dict[str, Any] = {
        "category": classify_exception_category(exc),
        "message": redact_sensitive_text(exc),
        "provider": provider,
        "framework": framework,
        "code": code or type(exc).__name__,
        "retryable": is_transient_exception(exc)
        if retryable is None
        else bool(retryable),
        "cause_type": type(exc).__name__,
        "details": {},
    }
    if status is not None:
        payload["details"] = {"status_code": status}
    return payload


def is_retryable_error_payload(value: object) -> bool:
    """Recognize only explicitly classified retryable error evidence."""

    if not isinstance(value, Mapping):
        return False
    if value.get("retryable") is True:
        return True
    return value.get("category") in {"rate_limit", "timeout", "transient"}


class AgenticSystemError(Exception):
    """Base class for Agentic Systems errors."""


class ToolContractError(AgenticSystemError):
    """Raised when a tool does not satisfy the public tool contract."""


class GraphContractError(AgenticSystemError):
    """Raised when LangGraph node mapping is invalid."""


class SkillLoadError(AgenticSystemError):
    """Raised when a Skill asset loader package cannot be loaded."""


__all__ = [
    "AgenticSystemError",
    "GraphContractError",
    "SkillLoadError",
    "ToolContractError",
    "classify_exception_category",
    "exception_status_code",
    "execution_error_payload",
    "is_retryable_error_payload",
    "is_transient_exception",
    "redact_sensitive_text",
]
