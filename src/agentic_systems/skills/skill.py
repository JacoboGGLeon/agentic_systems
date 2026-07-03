"""Runtime Skill API.

A :class:`Skill` is a reusable runtime package of tools, prompts, contracts and
policy. It is intentionally independent from cloud providers and from the
filesystem skill loader so users can create skills directly in notebooks while
filesystem ``load_skill(...)`` assets continue to work unchanged.
"""

from __future__ import annotations

import dataclasses
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..contracts import ValidationResult
from ..tools import Tool


class Skill:
    """Reusable runtime capability made of tools, prompts, contracts and policy.

    Parameters
    ----------
    name:
        Public skill name. It must be non-empty.
    description:
        Human-readable description.
    tools:
        Tools exposed by the skill. Items may be public ``Tool`` objects,
        ``@tool``-decorated functions (which are ``Tool`` objects), or plain
        callables. Plain callables are wrapped as strict ``Tool`` instances.
    prompts:
        Prompt templates or instructions keyed by logical prompt name.
    contracts:
        JSON-like contract metadata for the skill.
    policy:
        JSON-like runtime policy metadata. It is stored, not executed, so
        constructing a Skill never requires Bedrock/AWS credentials.
    metadata:
        Extra JSON-like metadata.
    version:
        Optional skill version.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        tools: Iterable[Tool | Callable[..., Any]] | None = None,
        prompts: Mapping[str, Any] | None = None,
        contracts: Mapping[str, Any] | None = None,
        policy: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        version: str = "0.1.0",
    ) -> None:
        self.name = name.strip() if isinstance(name, str) else ""
        if not self.name:
            raise ValueError("Skill name must be non-empty.")
        self.description = str(description or "").strip()
        self.version = str(version or "0.1.0")
        self._tools = [_coerce_tool(item) for item in _as_iterable(tools)]
        self.prompts = _string_keyed_dict(prompts, field_name="prompts")
        self.contracts = _string_keyed_dict(contracts, field_name="contracts")
        self.policy = _string_keyed_dict(policy, field_name="policy")
        self.metadata = _string_keyed_dict(metadata, field_name="metadata")

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Return tool names in the order provided by the user."""

        return tuple(tool.name for tool in self._tools)

    @property
    def tools(self) -> list[Tool]:
        """Return the direct ``Tool`` objects exposed by this skill.

        This property is intentionally notebook-friendly so users can pass
        ``tools=skill.tools`` or inspect the skill without learning internal
        registries. It returns a copy to keep the skill immutable from callers.
        """

        return list(self._tools)

    @property
    def instructions(self) -> str:
        """Return the default agent instructions for this skill, if any."""

        for key in ("instructions", "agent", "agent_instructions", "default"):
            value = self.prompts.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return self.description

    def prompt(self, name: str = "user_prompt", default: Any | None = None) -> Any:
        """Return a named prompt value from ``skill.prompts``.

        ``user_prompt`` is the preferred key for tutorial notebooks.
        """

        if name in self.prompts:
            return self.prompts[name]
        if default is not None:
            return default
        raise KeyError(f"Skill '{self.name}' has no prompt named {name!r}. Available: {sorted(self.prompts)}")

    def tool(self, name: str) -> Tool:
        """Return a concrete tool by name."""

        for item in self._tools:
            if item.name == name:
                return item
        raise KeyError(f"Skill '{self.name}' has no tool named {name!r}. Available: {list(self.tool_names)}")

    def available_tools(self) -> list[Tool]:
        """Return the direct ``Tool`` objects exposed by this skill."""

        return self.tools

    def info(self) -> dict[str, Any]:
        """Return a JSON-like serializable description of the skill."""

        return _json_like(
            {
                "name": self.name,
                "version": self.version,
                "description": self.description,
                "tool_names": list(self.tool_names),
                "tools": [tool.info() for tool in self._tools],
                "prompts": self.prompts,
                "contracts": self.contracts,
                "policy": self.policy,
                "metadata": self.metadata,
            }
        )

    def describe(self) -> str:
        """Return a short human-readable description."""

        suffix = f": {self.description}" if self.description else ""
        tools = ", ".join(self.tool_names) if self.tool_names else "no tools"
        return f"Skill `{self.name}`{suffix} ({tools})"

    def check(self) -> ValidationResult:
        """Validate the local skill definition without contacting a runtime."""

        result = ValidationResult(ok=True)
        names = list(self.tool_names)
        counts = Counter(names)
        for tool_name in sorted(name for name, count in counts.items() if count > 1):
            result.add(
                "duplicate_tool_name",
                f"Skill '{self.name}' contains duplicate tool name '{tool_name}'.",
                path="tools",
                meta={"tool_name": tool_name, "count": counts[tool_name]},
            )

        for index, tool in enumerate(self._tools):
            tool_validation = tool.check()
            for issue in tool_validation.issues:
                result.add(
                    issue.code,
                    issue.message,
                    severity=issue.severity,
                    path=f"tools[{index}].{issue.path}" if issue.path else f"tools[{index}]",
                    meta={"tool_name": tool.name, **issue.meta},
                )
        return result

    def __len__(self) -> int:
        return len(self._tools)

    def __iter__(self):
        return iter(self._tools)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Skill(name={self.name!r}, tools={list(self.tool_names)!r})"


def _as_iterable(items: Iterable[Tool | Callable[..., Any]] | None) -> tuple[Tool | Callable[..., Any], ...]:
    if items is None:
        return ()
    if isinstance(items, (str, bytes)):
        raise TypeError("Skill tools must be an iterable of Tool objects or callables, not a string.")
    if isinstance(items, Tool):
        return (items,)
    return tuple(items)


def _coerce_tool(item: Tool | Callable[..., Any]) -> Tool:
    if isinstance(item, Tool):
        return item
    if callable(item):
        return Tool(name=getattr(item, "__name__", ""), function=item)
    raise TypeError(f"Unsupported skill tool value: {item!r}. Expected Tool or callable.")


def _string_keyed_dict(value: Mapping[str, Any] | None, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"Skill {field_name} must be a mapping.")
    return {str(key): _json_like(item) for key, item in value.items()}


def _json_like(value: Any) -> Any:
    """Best-effort conversion to JSON-like structures for public ``info``."""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _json_like(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_like(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_like(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, type):
        return value.__name__
    if callable(value):
        return getattr(value, "__name__", repr(value))
    return value


__all__ = ["Skill"]
