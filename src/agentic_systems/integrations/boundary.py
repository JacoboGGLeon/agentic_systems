"""Framework and Graph boundary declarations for optional integrations."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from ..contracts import ValidationResult
from ..engines.names import (
    LANGGRAPH_ORCHESTRATOR,
    OPENAI_AGENTS_FRAMEWORK,
    STRANDS_FRAMEWORK,
    normalize_engine_text,
)
from ..results import RunResult
from .config import NATIVE_FRAMEWORK


FRAMEWORK_BOUNDARY_SCHEMA_VERSION = "agentic_systems.framework-boundary.v1"
GRAPH_BOUNDARY_SCHEMA_VERSION = "agentic_systems.graph-boundary.v1"

FrameworkIntegrationKind = Literal["native-adapter"]
GraphBoundaryKind = Literal["agentic-systems-native", "framework-native"]

PRESERVED_RUN_RESULT_FIELDS = (
    "ok",
    "final",
    "data",
    "tool_events",
    "usage",
    "engine",
    "model",
    "mode",
    "validation",
    "errors",
)


class FrameworkProfile(BaseModel):
    """Machine-readable declaration of one framework integration boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = FRAMEWORK_BOUNDARY_SCHEMA_VERSION
    framework: str
    integration_kind: FrameworkIntegrationKind
    adapter_module: str | None
    native_object_access: bool
    detail: str

    @property
    def has_adapter(self) -> bool:
        return (
            self.integration_kind == "native-adapter"
            and self.adapter_module is not None
        )

    def check(self, *, require_adapter: bool = False) -> ValidationResult:
        result = ValidationResult(ok=True)
        if require_adapter and not self.has_adapter:
            result.add(
                "framework_adapter_unavailable",
                f"Framework {self.framework!r} is {self.integration_kind}; no external adapter executes it. "
                f"{self.detail}",
                path="framework",
                meta=self.model_dump(mode="json"),
            )
        return result

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class GraphBoundary(BaseModel):
    """Inspectable distinction between internal and framework-native Graphs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = GRAPH_BOUNDARY_SCHEMA_VERSION
    kind: GraphBoundaryKind
    framework: str | None
    graph_type: str
    native_type: str
    owns: tuple[str, ...]
    preserves: tuple[str, ...] = PRESERVED_RUN_RESULT_FIELDS

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class FrameworkProjectionReport(BaseModel):
    """Serializable result of checking a Framework state projection."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = FRAMEWORK_BOUNDARY_SCHEMA_VERSION
    framework: str
    ok: bool
    checks: dict[str, bool]
    issues: list[dict[str, Any]]

    def raise_if_failed(self) -> "FrameworkProjectionReport":
        if not self.ok:
            raise ValueError(
                f"Framework projection failed for {self.framework!r}: {self.issues}"
            )
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def framework_profile(framework: str) -> FrameworkProfile:
    """Return the declared boundary for a supported framework identity."""

    name = normalize_engine_text(framework)
    try:
        return _FRAMEWORK_PROFILES[name]
    except KeyError as exc:
        available = ", ".join(_FRAMEWORK_PROFILES)
        raise ValueError(
            f"Unknown framework {framework!r}. Use one of: {available}."
        ) from exc


def framework_profiles() -> tuple[FrameworkProfile, ...]:
    return tuple(_FRAMEWORK_PROFILES.values())


def describe_graph_boundary(graph: Any) -> GraphBoundary:
    """Describe an Agentic Systems Graph wrapper without executing it."""

    kind = getattr(graph, "graph_kind", None)
    if kind not in {"agentic-systems-native", "framework-native"}:
        raise TypeError(
            "Graph boundary is not declared. Expected graph_kind to be "
            "'agentic-systems-native' or 'framework-native'."
        )
    framework = getattr(graph, "framework", None)
    if kind == "framework-native" and not framework:
        raise ValueError(
            "A framework-native Graph must declare its framework identity."
        )
    native = getattr(graph, "native", graph)
    owns = (
        ("portable_state_transition", "agent_invocation", "result_projection")
        if kind == "agentic-systems-native"
        else ("framework_state", "nodes", "edges", "compilation", "lifecycle")
    )
    return GraphBoundary(
        kind=kind,
        framework=str(framework) if framework else None,
        graph_type=type(graph).__name__,
        native_type=type(native).__name__,
        owns=owns,
    )


def evaluate_framework_projection(
    profile: FrameworkProfile | str,
    *,
    source_result: Any,
    projected_state: Any,
    result_key: str,
    trace_key: str | None = None,
) -> FrameworkProjectionReport:
    """Check that a Framework state projection retains the central RunResult contract."""

    selected = framework_profile(profile) if isinstance(profile, str) else profile
    validation = ValidationResult(ok=True)
    checks: dict[str, bool] = {}

    def record(name: str, condition: bool, message: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            validation.add(name, message, path=name)

    adapter_check = selected.check(require_adapter=True)
    record(
        "adapter_available",
        adapter_check.ok,
        "A real Framework adapter is required for conformance.",
    )
    for issue in adapter_check.issues:
        validation.add(
            issue.code,
            issue.message,
            severity=issue.severity,
            path=issue.path,
            meta=issue.meta,
        )

    source_is_result = isinstance(source_result, RunResult)
    state_is_mapping = isinstance(projected_state, Mapping)
    record(
        "source_run_result",
        source_is_result,
        "Framework projection source must be RunResult.",
    )
    record(
        "state_mapping",
        state_is_mapping,
        "Framework projection must return mapping-shaped state.",
    )

    if source_is_result and state_is_mapping:
        projected = projected_state.get(result_key)
        projected_is_mapping = isinstance(projected, Mapping)
        record(
            "result_projection",
            projected_is_mapping,
            f"State must contain serialized RunResult at {result_key!r}.",
        )
        if projected_is_mapping:
            expected = source_result.to_dict()
            for field in PRESERVED_RUN_RESULT_FIELDS:
                record(
                    f"preserve_{field}",
                    projected.get(field) == expected.get(field),
                    f"Framework projection changed central RunResult field {field!r}.",
                )
            meta = (
                projected.get("meta")
                if isinstance(projected.get("meta"), Mapping)
                else {}
            )
            record(
                "adapter_identity",
                meta.get("framework_adapter") == selected.framework,
                "Projected result must identify the Framework adapter that performed the projection.",
            )
        if trace_key is not None:
            trace = projected_state.get(trace_key)
            trace_is_mapping = isinstance(trace, Mapping)
            record(
                "trace_projection",
                trace_is_mapping,
                f"State must contain compact trace at {trace_key!r}.",
            )
            if trace_is_mapping:
                record(
                    "trace_status",
                    trace.get("run_ok") == source_result.ok,
                    "Compact trace changed result status.",
                )
                record(
                    "trace_engine",
                    trace.get("engine") == source_result.engine,
                    "Compact trace changed engine identity.",
                )

        try:
            json.dumps(dict(projected_state))
            serializable = True
        except (TypeError, ValueError):
            serializable = False
        record(
            "json_serialization",
            serializable,
            "Projected Framework state must serialize to JSON.",
        )

    return FrameworkProjectionReport(
        framework=selected.framework,
        ok=validation.ok and all(checks.values()),
        checks=checks,
        issues=[issue.model_dump(mode="json") for issue in validation.issues],
    )


_FRAMEWORK_PROFILES = {
    NATIVE_FRAMEWORK: FrameworkProfile(
        framework=NATIVE_FRAMEWORK,
        integration_kind="native-adapter",
        adapter_module="agentic_systems.integrations.adapters.native",
        native_object_access=True,
        detail="Agentic Systems executes the selected Provider directly.",
    ),
    LANGGRAPH_ORCHESTRATOR: FrameworkProfile(
        framework=LANGGRAPH_ORCHESTRATOR,
        integration_kind="native-adapter",
        adapter_module="agentic_systems.integrations.adapters.langgraph",
        native_object_access=True,
        detail="A compiled one-node StateGraph owns Framework execution.",
    ),
    OPENAI_AGENTS_FRAMEWORK: FrameworkProfile(
        framework=OPENAI_AGENTS_FRAMEWORK,
        integration_kind="native-adapter",
        adapter_module="agentic_systems.integrations.adapters.openai_agents",
        native_object_access=True,
        detail="OpenAI Agents Runner owns turns, tools, handoffs, guardrails, sessions, and MCP.",
    ),
    STRANDS_FRAMEWORK: FrameworkProfile(
        framework=STRANDS_FRAMEWORK,
        integration_kind="native-adapter",
        adapter_module="agentic_systems.integrations.adapters.strands",
        native_object_access=True,
        detail="Strands Agent owns its loop, hooks, interventions, tools, and MCP lifecycle.",
    ),
}


__all__ = [
    "FRAMEWORK_BOUNDARY_SCHEMA_VERSION",
    "GRAPH_BOUNDARY_SCHEMA_VERSION",
    "PRESERVED_RUN_RESULT_FIELDS",
    "FrameworkProfile",
    "GraphBoundary",
    "FrameworkProjectionReport",
    "framework_profile",
    "framework_profiles",
    "describe_graph_boundary",
    "evaluate_framework_projection",
]
