"""Reusable non-system assets displayed by Agentic Systems Studio."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import agentic_systems as toolkit

from typing import Any

from .catalog import SYSTEM_SPECS
from .operators import TOOLS


@dataclass(frozen=True)
class ComponentAsset:
    id: str
    name: str
    description: str
    capability: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TOOL_ASSETS = tuple(
    ComponentAsset(
        id=name,
        name=name.replace("_", " ").title(),
        description=tool.description,
        capability="deterministic-operation",
        metadata={"tool_identity": tool.identity, "input_schema": tool.input_schema},
    )
    for name, tool in TOOLS.items()
)

SKILL_ASSETS = tuple(
    ComponentAsset(
        id=spec.runtime_skill,
        name=spec.runtime_skill.replace("-", " ").title(),
        description=f"Runtime skill family for {spec.name}.",
        capability=", ".join(spec.capabilities),
        metadata={
            "system_id": spec.id,
            "tools": list(spec.tools),
            "version": toolkit.__version__,
        },
    )
    for spec in SYSTEM_SPECS
)

AGENT_ASSETS = tuple(
    ComponentAsset(
        id=f"{spec.id}.{stage.id}",
        name=stage.name,
        description=stage.instructions,
        capability=stage.capability,
        metadata={
            "system_id": spec.id,
            "kind": stage.kind,
            "tool": stage.tool_key,
            "runtime": "python-runtime"
            if stage.kind == "operator"
            else "selected-provider",
        },
    )
    for spec in SYSTEM_SPECS
    for stage in spec.stages
)

ENVIRONMENT_ASSETS = (
    ComponentAsset(
        "incident-game-day",
        "Incident Game Day",
        "Timed incident records with escalating signals.",
        "episodic-operations",
        {"episodes": 5, "step": "incident update"},
    ),
    ComponentAsset(
        "support-queue",
        "Support Queue",
        "Ticket arrivals, SLAs and escalation transitions.",
        "queue-simulation",
        {"episodes": 10, "step": "ticket"},
    ),
    ComponentAsset(
        "data-drift-lab",
        "Data Drift Lab",
        "Data-quality snapshots that change through time.",
        "data-drift",
        {"episodes": 6, "step": "snapshot"},
    ),
    ComponentAsset(
        "prompt-red-team",
        "Prompt Red Team",
        "Benign and adversarial prompt rounds.",
        "security-simulation",
        {"episodes": 8, "step": "attack round"},
    ),
    ComponentAsset(
        "delivery-sprint",
        "Delivery Sprint",
        "Requirements and constraints revealed by iteration.",
        "planning-simulation",
        {"episodes": 4, "step": "sprint"},
    ),
    ComponentAsset(
        "research-corpus",
        "Research Corpus",
        "Evidence batches with disagreement and uncertainty.",
        "evidence-over-time",
        {"episodes": 5, "step": "source batch"},
    ),
)

EVAL_ASSETS = (
    ComponentAsset(
        "tool-contract",
        "Tool Contract",
        "Checks deterministic tool schemas and return contracts.",
        "contract-eval",
        {"targets": ["tool", "agent", "system"]},
    ),
    ComponentAsset(
        "groundedness",
        "Groundedness",
        "Scores whether claims remain supported by supplied evidence.",
        "quality-eval",
        {"targets": ["agent", "system"]},
    ),
    ComponentAsset(
        "deterministic-boundary",
        "Deterministic Boundary",
        "Verifies arithmetic, parsing and rules happen in operators.",
        "architecture-eval",
        {"targets": ["system"]},
    ),
    ComponentAsset(
        "task-success",
        "Task Success",
        "Measures domain acceptance criteria.",
        "outcome-eval",
        {"targets": ["agent", "system"]},
    ),
    ComponentAsset(
        "latency-budget",
        "Latency Budget",
        "Checks elapsed time and turn budgets.",
        "performance-eval",
        {"targets": ["agent", "system", "environment"]},
    ),
    ComponentAsset(
        "provider-parity",
        "Provider Parity",
        "Compares normalized RunResult behavior across providers.",
        "portability-eval",
        {"targets": ["system"]},
    ),
    ComponentAsset(
        "framework-parity",
        "Framework Parity",
        "Compares normalized behavior across frameworks.",
        "portability-eval",
        {"targets": ["system"]},
    ),
    ComponentAsset(
        "composition-lineage",
        "Composition Lineage",
        "Checks nested RunResult children and execution identities.",
        "composition-eval",
        {"targets": ["system-of-systems"]},
    ),
)


__all__ = [
    "AGENT_ASSETS",
    "ENVIRONMENT_ASSETS",
    "EVAL_ASSETS",
    "SKILL_ASSETS",
    "TOOL_ASSETS",
    "ComponentAsset",
]
