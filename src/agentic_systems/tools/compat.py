"""Tool registry helpers and observable tool events."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from pydantic import BaseModel, ConfigDict, Field


class ToolEvent(BaseModel):
    """Stable trace event for one tool invocation."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    ok: bool = True
    error: dict[str, Any] | None = None
    duration_ms: float | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_runtime_record(cls, record: Any) -> "ToolEvent":
        """Convert an internal runtime tool-call record into a ToolEvent."""

        raw = record.model_dump(mode="json") if hasattr(record, "model_dump") else dict(record)
        tool_output = raw.get("tool_output") or {}
        data = tool_output.get("data") if isinstance(tool_output, dict) else None
        error = None
        if raw.get("ok") is False:
            error = data if isinstance(data, dict) else {"message": str(data)}
        return cls(
            id=str(raw.get("tool_use_id") or raw.get("id") or ""),
            name=str(raw.get("tool_name") or raw.get("name") or ""),
            input=raw.get("tool_input") or raw.get("input") or {},
            output=tool_output if isinstance(tool_output, dict) else {"value": tool_output},
            ok=bool(raw.get("ok")),
            error=error,
            meta={"source": "bedrock_runtime", **(raw.get("meta") or {})},
        )


def assert_dict_tool_output(tool_name: str, value: Any) -> dict[str, Any]:
    """Enforce the Agentic Systems public contract: tools return dict."""

    if isinstance(value, dict):
        return value

    if isinstance(value, list):
        fix = "return {'items': your_list}"
    elif isinstance(value, str):
        fix = "return {'text': your_text}"
    elif value is None:
        fix = "return {'ok': True}"
    elif hasattr(value, "model_dump"):
        fix = "return model.model_dump(mode='json')"
    else:
        fix = "return {'value': your_value}"

    raise TypeError(
        f"ToolContractError: Tool '{tool_name}' returned {type(value).__name__}. "
        "AgenticSystem tools must return dict. "
        f"Fix: {fix}."
    )


@dataclass(frozen=True)
class ToolkitRef:
    """A resolved toolkit reference used when expanding agent tools."""

    name: str
    tool_names: tuple[str, ...]


class Toolkit:
    """Namespaced group of tools, e.g. crm.get_customer."""

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

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Toolkit(name={self.name!r}, tools={self._tool_names!r})"

    def _full_name(self, fn: Callable[..., Any], name: str | None = None) -> str:
        short = name or fn.__name__
        if "." in short:
            return short
        return f"{self.name}.{short}"

    def tool(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        on_conflict: str = "error",
    ):
        """Register a namespaced tool in the parent system."""

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

        if func is None:
            return decorator
        return decorator(func)

    def add(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        description: str | None = None,
        on_conflict: str = "error",
    ) -> Callable[..., Any]:
        return self.tool(fn, name=name, description=description, on_conflict=on_conflict)

    def ref(self) -> ToolkitRef:
        return ToolkitRef(name=self.name, tool_names=self.tool_names)


def expand_tool_inputs(items: Any) -> tuple[str, ...]:
    """Expand strings, Toolkit objects, or iterables into a flat tool-name tuple."""

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


def now_ms() -> float:
    return time.perf_counter() * 1000.0
