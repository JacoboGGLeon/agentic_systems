"""Versioned declarative specs for the Agentic Systems grammar."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import JsonValue, PersistedSpec
from .execution import ExecutionLimits, ProviderRuntimeSpec, PythonRuntimeSpec


SPEC_SCHEMA_VERSION = "agentic_systems.spec.v1"


class FrameworkSpec(PersistedSpec):
    schema_version: str = SPEC_SCHEMA_VERSION
    name: Literal["native", "langgraph", "openai-agents", "strands"] = "native"
    options: dict[str, JsonValue] = Field(default_factory=dict)


class ToolSpec(PersistedSpec):
    schema_version: str = SPEC_SCHEMA_VERSION
    name: str
    description: str = ""
    input_schema: dict[str, JsonValue] = Field(default_factory=dict)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class SkillSpec(PersistedSpec):
    schema_version: str = SPEC_SCHEMA_VERSION
    name: str
    description: str = ""
    tool_names: tuple[str, ...] = ()
    instructions: str = ""
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class AgentSpec(PersistedSpec):
    schema_version: str = SPEC_SCHEMA_VERSION
    name: str
    instructions: str = ""
    runtime: ProviderRuntimeSpec = Field(default_factory=PythonRuntimeSpec)
    framework: FrameworkSpec = Field(default_factory=FrameworkSpec)
    tool_names: tuple[str, ...] = ()
    skill_names: tuple[str, ...] = ()
    limits: ExecutionLimits = Field(default_factory=ExecutionLimits)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class SystemSpec(PersistedSpec):
    schema_version: str = SPEC_SCHEMA_VERSION
    name: str
    component_names: tuple[str, ...]
    execution: Literal["sequential", "parallel", "graph"] = "sequential"
    limits: ExecutionLimits = Field(default_factory=ExecutionLimits)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class EnvironmentSpec(PersistedSpec):
    schema_version: str = SPEC_SCHEMA_VERSION
    name: str
    system_name: str
    max_episodes: int | None = Field(default=None, ge=1)
    max_steps: int | None = Field(default=None, ge=1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class EvalSpec(PersistedSpec):
    schema_version: str = SPEC_SCHEMA_VERSION
    name: str
    target_name: str
    target_kind: Literal["agent", "system"]
    evaluator_names: tuple[str, ...] = ()
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


__all__ = [
    "SPEC_SCHEMA_VERSION",
    "AgentSpec",
    "EnvironmentSpec",
    "EvalSpec",
    "FrameworkSpec",
    "SkillSpec",
    "SystemSpec",
    "ToolSpec",
]
