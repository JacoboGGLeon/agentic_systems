"""Build and compose the systems declared by the Studio catalog."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import agentic_systems as toolkit

from .catalog import SystemSpec, composition_mermaid, get_system_spec
from .operators import TOOLS

CompositionMode = Literal["sequential", "parallel"]


@dataclass(frozen=True)
class StudioConfig:
    """Provider/framework configuration shared by every reasoning stage."""

    provider: str = "openai-runtime"
    framework: str = "agentic-systems"
    model: str | None = None
    timeout_s: float = 120.0
    max_turns: int = 6
    max_tool_calls: int = 4
    max_tokens: int = 1024

    @property
    def framework_value(self) -> str | None:
        return None if self.framework in {"agentic-systems", "native", ""} else self.framework

    def runtime(self):
        return toolkit.runtime(
            provider=self.provider,
            model=self.model,
            scheduler=toolkit.scheduler(
                timeout_s=self.timeout_s,
                max_turns=self.max_turns,
                max_tool_calls=self.max_tool_calls,
            ),
        )

    def operator_runtime(self):
        return toolkit.runtime(
            provider="python-runtime",
            scheduler=toolkit.scheduler(
                timeout_s=self.timeout_s,
                max_turns=2,
                max_tool_calls=1,
            ),
        )


@dataclass
class StudioSystem:
    """Executable system plus its portable declaration and runtime assets."""

    spec: SystemSpec
    config: StudioConfig
    system: Any
    compiled: toolkit.CompiledSystem
    skills: tuple[Any, ...] = field(default_factory=tuple)

    def run(self, input: Any = None, **kwargs: Any) -> toolkit.RunResult:
        result = self.compiled.run(self.spec.sample_input if input is None else input, **kwargs)
        result.meta.update(
            {
                "studio_system_id": self.spec.id,
                "studio_size": self.spec.size,
                "provider": self.config.provider,
                "framework": self.config.framework,
                "capabilities": list(self.spec.capabilities),
            }
        )
        return result

    def inspect(self) -> dict[str, Any]:
        report = self.system.inspect()
        payload = report.model_dump(mode="json") if hasattr(report, "model_dump") else dict(report)
        payload["compiled"] = self.compiled.inspect()
        payload["catalog"] = self.spec.to_dict()
        return payload

    def mermaid(self) -> str:
        return self.spec.mermaid(
            provider=self.config.provider,
            framework=self.config.framework,
        )


@dataclass
class StudioComposition:
    """System-of-systems with a hierarchical RunResult."""

    systems: tuple[StudioSystem, ...]
    mode: CompositionMode
    compiled: toolkit.CompiledSystem

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(system.spec.id for system in self.systems)

    def run(self, input: Any = None, **kwargs: Any) -> toolkit.RunResult:
        result = self.compiled.run(input, **kwargs)
        result.meta.update(
            {
                "studio_composition": list(self.ids),
                "composition_mode": self.mode,
            }
        )
        return result

    def inspect(self) -> dict[str, Any]:
        return {
            "systems": [system.inspect() for system in self.systems],
            "composition": self.compiled.inspect(),
            "mode": self.mode,
        }

    def mermaid(self) -> str:
        return composition_mermaid(self.ids, mode=self.mode)


def _stage_skill(spec: SystemSpec, stage: Any, tool: Any):
    return toolkit.skill(
        name=f"{spec.runtime_skill}-{stage.id}",
        description=f"{stage.name}: {stage.capability}",
        tools=[tool],
        prompts={"instructions": stage.instructions},
        metadata={
            "studio_system_id": spec.id,
            "stage_id": stage.id,
            "stage_kind": stage.kind,
            "capability": stage.capability,
        },
        version="2.0.0",
    )


def build_system(
    system_id: str,
    config: StudioConfig | None = None,
    *,
    validate: bool = True,
) -> StudioSystem:
    """Materialize one catalog declaration through the public 2.0 API."""

    spec = get_system_spec(system_id)
    selected = config or StudioConfig()
    if selected.provider == "python-runtime":
        raise ValueError(
            "Studio systems contain reasoning agents. Choose openai-runtime, "
            "ollama-runtime, bedrock-runtime, vllm-runtime or auto."
        )

    system = toolkit.system(runtime=selected.runtime(), model=selected.model)
    runtime_skills: list[Any] = []

    for stage in spec.stages:
        tool = TOOLS[stage.tool_key]
        runtime_skill = _stage_skill(spec, stage, tool)
        runtime_skills.append(runtime_skill)
        is_operator = stage.kind == "operator"
        instructions = (
            f"You are the {stage.name} in {spec.name}. {stage.instructions} "
            "Use the supplied input as data. Do not fabricate unavailable evidence. "
            "Call your registered tool when it can establish or preserve deterministic evidence. "
            "Return a concise handoff for the next computation unit."
        )
        system.agent(
            name=f"{spec.id}.{stage.id}",
            instructions=instructions,
            skills=[runtime_skill],
            engine="python-runtime" if is_operator else selected.provider,
            framework=None if is_operator else selected.framework_value,
            model=None if is_operator else selected.model,
            runtime=selected.operator_runtime() if is_operator else selected.runtime(),
            policy={
                "max_tool_calls": 1 if is_operator else selected.max_tool_calls,
                "max_turns": 2 if is_operator else selected.max_turns,
                "max_tokens": selected.max_tokens,
            },
        )

    if validate:
        inspection = system.inspect()
        if hasattr(inspection, "raise_if_errors"):
            inspection.raise_if_errors()
        elif getattr(inspection, "errors", None):
            raise ValueError(f"Invalid Studio system {system_id}: {inspection.errors}")

    compiled = system.compile(
        execution=toolkit.SequentialPlan(),
        name=spec.id,
    )
    return StudioSystem(
        spec=spec,
        config=selected,
        system=system,
        compiled=compiled,
        skills=tuple(runtime_skills),
    )


def build_all(config: StudioConfig | None = None, *, validate: bool = True) -> tuple[StudioSystem, ...]:
    selected = config or StudioConfig()
    from .catalog import SYSTEM_SPECS

    return tuple(build_system(spec.id, selected, validate=validate) for spec in SYSTEM_SPECS)


def compose_systems(
    system_ids: list[str] | tuple[str, ...],
    config: StudioConfig | None = None,
    *,
    mode: CompositionMode = "sequential",
    validate: bool = True,
) -> StudioComposition:
    """Compose reusable systems as computation units in a larger system."""

    ids = tuple(system_ids)
    if not ids:
        raise ValueError("compose_systems(...) requires at least one system id.")
    if mode not in {"sequential", "parallel"}:
        raise ValueError("mode must be 'sequential' or 'parallel'.")

    systems = tuple(build_system(system_id, config, validate=validate) for system_id in ids)
    boundary = toolkit.system(runtime=toolkit.runtime(provider="python-runtime"))
    for system in systems:
        boundary.add(system.compiled)
    plan = toolkit.SequentialPlan() if mode == "sequential" else toolkit.ParallelPlan()
    compiled = boundary.compile(
        execution=plan,
        name=f"studio-{mode}-composition",
    )
    return StudioComposition(systems=systems, mode=mode, compiled=compiled)


__all__ = [
    "CompositionMode",
    "StudioComposition",
    "StudioConfig",
    "StudioSystem",
    "build_all",
    "build_system",
    "compose_systems",
]
