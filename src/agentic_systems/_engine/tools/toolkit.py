"""Namespaced Toolkit composition."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolkitRef:
    """A resolved Toolkit reference used when expanding Agent tools."""

    name: str
    tool_names: tuple[str, ...]


class Toolkit:
    """Namespaced group of Tools, for example ``crm.get_customer``."""

    def __init__(self, system: Any, name: str) -> None:
        self.system = system
        self.name = name.strip()
        if not self.name:
            raise ValueError("Toolkit name must be non-empty.")
        self._tool_names: list[str] = []

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(self._tool_names)

    def __iter__(self):
        return iter(self._tool_names)

    def __len__(self) -> int:
        return len(self._tool_names)

    def __repr__(self) -> str:
        return f"Toolkit(name={self.name!r}, tools={self._tool_names!r})"

    def _full_name(self, fn: Callable[..., Any], name: str | None = None) -> str:
        short = name or fn.__name__
        return short if "." in short else f"{self.name}.{short}"

    def tool(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        on_conflict: str = "error",
    ):
        """Register a namespaced Tool in the parent System."""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            full_name = self._full_name(fn, name)
            registered = self.system.tool(
                fn,
                name=full_name,
                description=description,
                on_conflict=on_conflict,
                source=f"toolkit:{self.name}",
            )
            if full_name not in self._tool_names:
                self._tool_names.append(full_name)
            return registered

        return decorator if func is None else decorator(func)

    def add(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        description: str | None = None,
        on_conflict: str = "error",
    ) -> Callable[..., Any]:
        return self.tool(
            fn,
            name=name,
            description=description,
            on_conflict=on_conflict,
        )

    def ref(self) -> ToolkitRef:
        return ToolkitRef(name=self.name, tool_names=self.tool_names)


def expand_tool_inputs(items: Any) -> tuple[str, ...]:
    """Expand strings, Toolkits, or iterables into flat Tool names."""

    if items is None:
        return ()
    if isinstance(items, Toolkit):
        return items.tool_names
    if isinstance(items, str):
        return (items,)
    if isinstance(items, Iterable):
        out: list[str] = []
        for item in items:
            out.extend(expand_tool_inputs(item))
        return tuple(out)
    raise TypeError(f"Unsupported tools value: {items!r}")


__all__ = ["Toolkit", "ToolkitRef", "expand_tool_inputs"]
