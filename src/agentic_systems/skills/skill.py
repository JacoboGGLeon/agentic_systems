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

from ..composition import conflict_message, normalize_conflict_policy, same_tool_definition
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
        self._composition = {
            "schema_version": "agentic_systems.skill-composition.v1",
            "identity": self.name,
            "on_conflict": "error",
            "sources": [self.name],
            "events": [
                {
                    "kind": "tool",
                    "identity": item.name,
                    "decision": "add",
                    "selected_source": self.name,
                }
                for item in self._tools
            ],
        }

    @property
    def identity(self) -> str:
        """Return the Skill identity used inside a composition boundary."""

        return self.name

    @classmethod
    def compose(
        cls,
        *skills: "Skill",
        name: str,
        description: str = "",
        version: str = "0.1.0",
        metadata: Mapping[str, Any] | None = None,
        on_conflict: str = "error",
    ) -> "Skill":
        """Compose Skills without executing them or applying implicit overrides."""

        if not skills:
            raise ValueError("Skill.compose(...) requires at least one source Skill.")
        if not all(isinstance(skill, Skill) for skill in skills):
            raise TypeError("Skill.compose(...) accepts only Skill instances.")
        policy = normalize_conflict_policy(on_conflict)
        selected_sources: dict[str, Skill] = {}
        events: list[dict[str, Any]] = []
        for source in skills:
            existing = selected_sources.get(source.identity)
            if existing is None:
                selected_sources[source.identity] = source
                continue
            if existing is source:
                events.append(_composition_event("skill", source.identity, "reuse", source.identity))
                continue
            if policy == "error":
                raise ValueError(conflict_message("Skill", source.identity, existing.identity, source.identity))
            decision = policy
            if policy == "replace":
                selected_sources[source.identity] = source
            events.append(_composition_event("skill", source.identity, decision, source.identity))

        tools: dict[str, Tool] = {}
        tool_sources: dict[str, str] = {}
        prompts: dict[str, Any] = {}
        prompt_sources: dict[str, str] = {}
        contracts: dict[str, Any] = {}
        contract_sources: dict[str, str] = {}
        composed_policy: dict[str, Any] = {}
        policy_sources: dict[str, str] = {}
        sources = list(selected_sources.values())
        for source in sources:
            for item in source.tools:
                existing = tools.get(item.identity)
                if existing is None:
                    tools[item.identity] = item
                    tool_sources[item.identity] = source.identity
                    events.append(_composition_event("tool", item.identity, "add", source.identity))
                    continue
                if same_tool_definition(existing, item):
                    events.append(
                        _composition_event(
                            "tool",
                            item.identity,
                            "reuse",
                            source.identity,
                            selected_source=tool_sources[item.identity],
                        )
                    )
                    continue
                if policy == "error":
                    raise ValueError(
                        conflict_message("Tool", item.identity, tool_sources[item.identity], source.identity)
                    )
                if policy == "replace":
                    tools[item.identity] = item
                    tool_sources[item.identity] = source.identity
                events.append(
                    _composition_event(
                        "tool",
                        item.identity,
                        policy,
                        source.identity,
                        selected_source=tool_sources[item.identity],
                    )
                )
            _merge_mapping(prompts, prompt_sources, source.prompts, source.identity, "prompt", policy, events)
            _merge_mapping(
                contracts, contract_sources, source.contracts, source.identity, "contract", policy, events
            )
            _merge_mapping(
                composed_policy, policy_sources, source.policy, source.identity, "policy", policy, events
            )

        source_metadata = {source.identity: source.metadata for source in sources}
        composed_metadata = {
            "composed_from": [source.identity for source in sources],
            "source_metadata": source_metadata,
            **dict(metadata or {}),
        }
        result = cls(
            name=name,
            description=description,
            version=version,
            tools=tools.values(),
            prompts=prompts,
            contracts=contracts,
            policy=composed_policy,
            metadata=composed_metadata,
        )
        result._composition = {
            "schema_version": "agentic_systems.skill-composition.v1",
            "identity": result.identity,
            "on_conflict": policy,
            "sources": [source.identity for source in sources],
            "events": events,
        }
        return result

    def composition(self) -> dict[str, Any]:
        """Return the serializable provenance and decisions for this Skill."""

        return _json_like(self._composition)

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
                "identity": self.identity,
                "name": self.name,
                "version": self.version,
                "description": self.description,
                "tool_names": list(self.tool_names),
                "tools": [tool.info() for tool in self._tools],
                "prompts": self.prompts,
                "contracts": self.contracts,
                "policy": self.policy,
                "metadata": self.metadata,
                "composition": self.composition(),
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


def _composition_event(
    kind: str,
    identity: str,
    decision: str,
    incoming_source: str,
    *,
    selected_source: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "identity": identity,
        "decision": decision,
        "incoming_source": incoming_source,
        "selected_source": selected_source or incoming_source,
    }


def _merge_mapping(
    target: dict[str, Any],
    selected_sources: dict[str, str],
    incoming: Mapping[str, Any],
    incoming_source: str,
    kind: str,
    policy: str,
    events: list[dict[str, Any]],
) -> None:
    for key, value in incoming.items():
        if key not in target:
            target[key] = value
            selected_sources[key] = incoming_source
            events.append(_composition_event(kind, key, "add", incoming_source))
            continue
        if target[key] == value:
            events.append(
                _composition_event(
                    kind,
                    key,
                    "reuse",
                    incoming_source,
                    selected_source=selected_sources[key],
                )
            )
            continue
        if policy == "error":
            raise ValueError(conflict_message(kind.title(), key, selected_sources[key], incoming_source))
        if policy == "replace":
            target[key] = value
            selected_sources[key] = incoming_source
        events.append(
            _composition_event(
                kind,
                key,
                policy,
                incoming_source,
                selected_source=selected_sources[key],
            )
        )


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
