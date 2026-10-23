"""Named collections of Tools.

ToolSet replaces the overloaded Toolkit namespace class. The package alias
import agentic_systems as toolkit continues to mean the whole toolbox.
"""

from __future__ import annotations

from .toolkit import Toolkit, ToolkitRef


class ToolSet(Toolkit):
    """A named, reusable collection of Tools under one namespace."""


ToolSetRef = ToolkitRef


__all__ = ["ToolSet", "ToolSetRef"]
