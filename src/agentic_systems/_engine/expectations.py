"""Notebook-friendly expectation helpers for Agentic Systems.

The runtime validation still consumes plain dictionaries, but users should not
have to remember the exact shape of those dictionaries in notebooks. The
``lab.expect`` namespace is the recommended public API for tool-call
expectations.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _tool_names(*names: Any) -> list[str]:
    """Normalize one or many tool names into a clean list of strings."""

    if len(names) == 1 and not isinstance(names[0], str) and isinstance(names[0], Iterable):
        values = list(names[0])
    else:
        values = list(names)
    return [str(item) for item in values if str(item)]


class ExpectationBuilder:
    """Build plain-dict tool expectations with a small fluent namespace."""

    def exactly(self, *tool_names: Any) -> dict[str, list[str]]:
        """Require exactly this set of tools and no other tool names."""

        return {"exactly": _tool_names(*tool_names)}

    def any_of(self, *tool_names: Any, allowed: Iterable[str] | None = None) -> dict[str, list[str]]:
        """Require at least one of the tools.

        ``allowed`` defaults to the same tools, which keeps notebook examples
        strict enough to catch accidental extra tool calls while staying terse.
        """

        names = _tool_names(*tool_names)
        allowed_names = _tool_names(allowed) if allowed is not None else list(names)
        return {"any_of": names, "allowed": allowed_names}

    def all_of(self, *tool_names: Any, allowed: Iterable[str] | None = None) -> dict[str, list[str]]:
        """Require all listed tools.

        ``allowed`` defaults to the same tools, which means extra tool calls are
        treated as unexpected unless the caller explicitly broadens the set.
        """

        names = _tool_names(*tool_names)
        allowed_names = _tool_names(allowed) if allowed is not None else list(names)
        return {"all_of": names, "allowed": allowed_names}

    def allowed(self, *tool_names: Any) -> dict[str, list[str]]:
        """Allow these tools without requiring any specific one."""

        return {"allowed": _tool_names(*tool_names)}

    def at_least(self, count: int, *tool_names: Any) -> dict[str, Any]:
        """Require at least ``count`` calls from the allowed tool pool."""

        return {"min_count": int(count), "allowed": _tool_names(*tool_names)}


expect = ExpectationBuilder()

__all__ = ["ExpectationBuilder", "expect"]
