"""Canonical tool public surface.

Use ``Tool`` for explicit tool objects and ``@tool`` for quick functions.
"""

from __future__ import annotations

from .decorators import tool
from .tool import CheckResult, Tool

__all__ = [
    "tool",
    "Tool",
    "CheckResult",
]
