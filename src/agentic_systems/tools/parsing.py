"""Conservative parsing helpers for provider Tool-call boundaries."""

from __future__ import annotations

import json
import re
from collections.abc import Collection
from typing import Any

_TEXTUAL_TOOL_CALL = re.compile(
    r"\s*([a-zA-Z0-9_-]{1,64})\s*\(\s*(\{[\s\S]*\})\s*\)\s*"
)


def parse_textual_tool_call(
    content: str,
    allowed_names: Collection[str],
) -> tuple[str, dict[str, Any]] | None:
    """Parse an entire ``name(JSON-object)`` response for a declared Tool."""

    match = _TEXTUAL_TOOL_CALL.fullmatch(content)
    if match is None:
        return None
    name = match.group(1)
    if name not in allowed_names:
        return None
    try:
        arguments = json.loads(match.group(2))
    except json.JSONDecodeError:
        return None
    if not isinstance(arguments, dict):
        return None
    return name, arguments


__all__ = ["parse_textual_tool_call"]
