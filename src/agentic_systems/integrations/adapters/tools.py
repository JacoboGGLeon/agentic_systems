"""Framework-neutral Tool bridging, aliases, and collision checks."""

from __future__ import annotations

import functools
import ast
import hashlib
import inspect
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

_NATIVE_TOOL_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_TOOL_RESULT_MARKER = "__agentic_systems_tool_result__"


@dataclass(frozen=True, slots=True)
class ToolNameAliases:
    """Reversible mapping between public and SDK-safe Tool identities."""

    canonical_to_native: dict[str, str]
    native_to_canonical: dict[str, str]

    @classmethod
    def from_names(cls, names: Iterable[str]) -> "ToolNameAliases":
        canonical_to_native: dict[str, str] = {}
        native_to_canonical: dict[str, str] = {}
        for canonical in names:
            native = _portable_tool_name(canonical)
            owner = native_to_canonical.get(native)
            if owner is not None and owner != canonical:
                suffix = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8]
                native = f"{native[:55]}_{suffix}"
            canonical_to_native[canonical] = native
            native_to_canonical[native] = canonical
        return cls(canonical_to_native, native_to_canonical)

    def native(self, canonical: str) -> str:
        return self.canonical_to_native.get(canonical, canonical)

    def canonical(self, native: str) -> str:
        return self.native_to_canonical.get(native, native)

    def map_input(self, value: Any) -> Any:
        """Translate explicit Tool selectors while preserving ordinary names."""

        if isinstance(value, Mapping):
            mapped = {str(key): self.map_input(item) for key, item in value.items()}
            for key in ("tool", "tool_name"):
                selected = mapped.get(key)
                if isinstance(selected, str):
                    mapped[key] = self.native(selected)
            return mapped
        if isinstance(value, list):
            return [self.map_input(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.map_input(item) for item in value)
        return value


def tool_name_aliases(tools: Iterable[Any]) -> ToolNameAliases:
    """Build deterministic aliases for a collection of Agentic Systems Tools."""

    return ToolNameAliases.from_names(tool.name for tool in tools)


def canonical_tool_callable(tool: Any) -> Callable[..., Any]:
    """Execute an SDK Tool through the canonical Tool contract."""

    function = tool.function
    if function is None:
        raise ValueError(f"Tool {tool.name!r} has no function.")
    signature = inspect.signature(function)

    @functools.wraps(function)
    def invoke(*args: Any, **kwargs: Any) -> Any:
        if kwargs:
            payload: Any = kwargs
        elif len(args) > 1:
            try:
                payload = dict(signature.bind(*args).arguments)
            except TypeError:
                payload = list(args)
        elif len(args) == 1:
            payload = args[0]
        else:
            payload = None
        result = tool.run(payload)
        if result.ok:
            return result.data
        error = (
            result.errors[0]
            if result.errors
            else {
                "code": "tool_execution_failed",
                "message": result.text or f"Tool {tool.name!r} failed.",
            }
        )
        return {_TOOL_RESULT_MARKER: {"ok": False, "data": result.data, "error": error}}

    invoke.__signature__ = signature  # type: ignore[attr-defined]
    return invoke


def decode_tool_output(value: Any) -> tuple[Any, bool, dict[str, Any] | None]:
    """Decode the private Tool result marker from a vendor SDK output."""

    payload = value
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            try:
                payload = ast.literal_eval(payload)
            except (SyntaxError, ValueError):
                return value, True, None
    if not isinstance(payload, Mapping):
        return value, True, None
    envelope = payload.get(_TOOL_RESULT_MARKER)
    if not isinstance(envelope, Mapping):
        return payload, True, None
    error_value = envelope.get("error")
    error = dict(error_value) if isinstance(error_value, Mapping) else None
    return envelope.get("data"), bool(envelope.get("ok", False)), error


def _portable_tool_name(canonical: str) -> str:
    if _NATIVE_TOOL_NAME.fullmatch(canonical):
        return canonical
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", canonical).strip("_-")
    if not normalized:
        normalized = "tool"
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8]
    return f"{normalized[:55]}_{digest}"


def tool_identity(tool: Any) -> str:
    """Return the stable native identity used for collision detection."""

    if isinstance(tool, Mapping):
        candidate = tool.get("toolSpec")
        spec: Mapping[Any, Any] = candidate if isinstance(candidate, Mapping) else tool
        value = spec.get("name")
    else:
        value = getattr(tool, "name", None) or getattr(tool, "__name__", None)
    identity = str(value or "").strip()
    if not identity:
        identity = f"{type(tool).__module__}.{type(tool).__qualname__}:{id(tool)}"
    return identity


def merge_tools(converted: Iterable[Any], native: Iterable[Any] | None) -> list[Any]:
    """Combine converted Agentic Tools with untouched native Tools."""

    merged: list[Any] = []
    owners: dict[str, str] = {}
    for owner, items in (("agentic-systems", converted), ("native", native or ())):
        for item in items:
            identity = tool_identity(item)
            previous = owners.get(identity)
            if previous is not None:
                raise ValueError(
                    f"Tool identity collision for {identity!r}: {previous} and {owner}."
                )
            owners[identity] = owner
            merged.append(item)
    return merged


__all__ = [
    "ToolNameAliases",
    "canonical_tool_callable",
    "decode_tool_output",
    "merge_tools",
    "tool_identity",
    "tool_name_aliases",
]
