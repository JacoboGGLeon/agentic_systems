"""Framework-neutral native Tool merging and collision checks."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def tool_identity(tool: Any) -> str:
    """Return the stable native identity used for collision detection."""

    if isinstance(tool, Mapping):
        spec = (
            tool.get("toolSpec") if isinstance(tool.get("toolSpec"), Mapping) else tool
        )
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


__all__ = ["merge_tools", "tool_identity"]
