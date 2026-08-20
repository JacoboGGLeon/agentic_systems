"""Canonical tool public surface.

Use ``Tool`` for explicit tool objects and ``@tool`` for quick functions.
"""

from __future__ import annotations

from .decorators import tool
from .events import ToolEvent
from .runtime import assert_dict_tool_output, now_ms
from .tool import CheckResult, Tool
from .toolkit import Toolkit, ToolkitRef, expand_tool_inputs
from .toolset import ToolSet, ToolSetRef

__all__ = [
    "tool",
    "Tool",
    "CheckResult",
    "ToolEvent",
    "ToolSet",
    "ToolSetRef",
    "Toolkit",
    "ToolkitRef",
    "assert_dict_tool_output",
    "expand_tool_inputs",
    "now_ms",
]
