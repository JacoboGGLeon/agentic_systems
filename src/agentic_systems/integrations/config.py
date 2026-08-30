"""Canonical Framework configuration for Agentic Systems 2.1."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..engines.names import SUPPORTED_FRAMEWORKS, normalize_engine_text


NATIVE_FRAMEWORK = "native"
CANONICAL_FRAMEWORKS = (NATIVE_FRAMEWORK, *SUPPORTED_FRAMEWORKS)
RESERVED_AGENT_KWARGS = frozenset({"model", "name", "instructions", "system_prompt"})
RESERVED_RUN_KWARGS = frozenset({"input", "prompt", "agent", "starting_agent"})


class FrameworkConfig(BaseModel):
    """Framework identity and exact constructor/run keyword forwarding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = NATIVE_FRAMEWORK
    agent_kwargs: dict[str, Any] = Field(default_factory=dict)
    run_kwargs: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = normalize_engine_text(value)
        if name not in CANONICAL_FRAMEWORKS:
            available = ", ".join(CANONICAL_FRAMEWORKS)
            raise ValueError(f"Unknown framework {value!r}. Use one of: {available}.")
        return name

    @field_validator("agent_kwargs", "run_kwargs", mode="before")
    @classmethod
    def copy_kwargs(cls, value: Mapping[str, Any] | None) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TypeError("Framework kwargs must be mappings.")
        return dict(value)

    @model_validator(mode="after")
    def reject_reserved_kwargs(self) -> "FrameworkConfig":
        agent_conflicts = sorted(RESERVED_AGENT_KWARGS.intersection(self.agent_kwargs))
        run_conflicts = sorted(RESERVED_RUN_KWARGS.intersection(self.run_kwargs))
        if agent_conflicts:
            raise ValueError(
                "Framework agent_kwargs cannot override Agentic Systems-owned keys: "
                f"{', '.join(agent_conflicts)}."
            )
        if run_conflicts:
            raise ValueError(
                "Framework run_kwargs cannot override Agentic Systems-owned keys: "
                f"{', '.join(run_conflicts)}."
            )
        return self

    @classmethod
    def coerce(cls, value: "FrameworkConfig | str | None") -> "FrameworkConfig":
        if isinstance(value, cls):
            return value
        if value is None or str(value).strip() == "":
            return cls()
        return cls(name=str(value))

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")

    def inspect(self) -> dict[str, Any]:
        """Describe forwarded options by name and type without exposing values."""

        return {
            "name": self.name,
            "agent_kwargs": {
                key: type(value).__name__ for key, value in self.agent_kwargs.items()
            },
            "run_kwargs": {
                key: type(value).__name__ for key, value in self.run_kwargs.items()
            },
        }


__all__ = [
    "CANONICAL_FRAMEWORKS",
    "NATIVE_FRAMEWORK",
    "RESERVED_AGENT_KWARGS",
    "RESERVED_RUN_KWARGS",
    "FrameworkConfig",
]
