"""Canonical 1:1 API contract for Agentic Systems.

The public namespace is the only source of export identities. Class members,
signatures, fields, and source locations are projected from that namespace into
one deterministic manifest consumed by documentation, notebooks, the CLI, and
pytest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from hashlib import sha256
import json
import inspect
import re
from types import ModuleType
from typing import Any, Mapping


API_CONTRACT_SCHEMA_VERSION = "agentic_systems.api_contract.v2"
_MISSING = object()


@dataclass(frozen=True, slots=True)
class ApiContractEntry:
    """One public export or public member in the canonical API contract."""

    id: str
    export: str
    member: str | None
    kind: str
    tier: str
    source: str
    signature: str | None = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True, slots=True)
class ContractScenario:
    """One shared executable story across API, notebook, CLI, and pytest."""

    id: str
    summary: str
    cli: str
    notebooks: tuple[str, ...]
    api_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["notebooks"] = list(self.notebooks)
        payload["api_ids"] = list(self.api_ids)
        payload["pytest"] = (
            "tests/contracts/test_api_coherence_v2.py::"
            f"test_shared_scenario_cli_executes[{self.id}]"
        )
        return payload


CONTRACT_SCENARIOS = (
    ContractScenario(
        id="runtime",
        summary="Resolve runtime/provider configuration without model execution.",
        cli="agentic-systems runtime --provider python-runtime --json",
        notebooks=(
            "providers/00_auto.ipynb",
            "providers/01_openai.ipynb",
            "providers/02_bedrock.ipynb",
            "providers/03_vllm.ipynb",
            "providers/04_ollama.ipynb",
            "core/00_runtime_scheduler.ipynb",
        ),
        api_ids=("runtime", "scheduler", "RuntimeConfig.describe"),
    ),
    ContractScenario(
        id="tool",
        summary="Execute a deterministic Tool and normalize its RunResult.",
        cli="agentic-systems tool run --json",
        notebooks=("core/01_tool.ipynb",),
        api_ids=("tool", "Tool.run", "RunResult"),
    ),
    ContractScenario(
        id="skill",
        summary="Construct and inspect a reusable Skill.",
        cli="agentic-systems skill inspect --json",
        notebooks=("core/02_skills.ipynb",),
        api_ids=("skill", "Skill.describe"),
    ),
    ContractScenario(
        id="agent",
        summary="Execute one Agent through a selected Provider and Framework.",
        cli="agentic-systems agent run --json",
        notebooks=(
            "core/03_agent.ipynb",
            "core/04_results_lineage.ipynb",
            "core/08_single_agentic_system.ipynb",
            "frameworks/00_langgraph.ipynb",
            "frameworks/01_openai_agents.ipynb",
            "frameworks/02_aws_strands.ipynb",
        ),
        api_ids=("agent", "Agent.run", "RunResult"),
    ),
    ContractScenario(
        id="system",
        summary="Compile and execute connected computation units as a System.",
        cli="agentic-systems system run --json",
        notebooks=(
            "core/05_system.ipynb",
            "core/09_multi_agentic_system.ipynb",
        ),
        api_ids=("system", "AgenticSystem.run", "RunResult"),
    ),
    ContractScenario(
        id="graph",
        summary="Build and execute a portable Graph.",
        cli="agentic-systems graph run --json",
        notebooks=(
            "core/06_graph_native.ipynb",
            "core/10_multi_agent_graph.ipynb",
        ),
        api_ids=("graph", "GraphApp.run"),
    ),
    ContractScenario(
        id="environment",
        summary="Execute an episodic Environment step with observable reward.",
        cli="agentic-systems environment run --json",
        notebooks=("core/07_environment_eval.ipynb",),
        api_ids=(
            "environment",
            "AgenticEnvironment.reset",
            "AgenticEnvironment.step",
        ),
    ),
    ContractScenario(
        id="eval",
        summary="Evaluate an Agent or System against declared cases.",
        cli="agentic-systems eval run --json",
        notebooks=("core/07_environment_eval.ipynb",),
        api_ids=("eval", "Evaluator.run", "EvalReport"),
    ),
    ContractScenario(
        id="matrix",
        summary="Execute or explicitly mark not-run every Provider x Framework pair.",
        cli="agentic-systems matrix check --json",
        notebooks=("frameworks/03_provider_framework_matrix.ipynb",),
        api_ids=(
            "compatibility_matrix",
            "runtime",
            "framework",
            "Agent.run",
            "RunResult",
        ),
    ),
    ContractScenario(
        id="api_contract",
        summary="Resolve every stable export/member ID across all public layers.",
        cli="agentic-systems api exercise --all --json",
        notebooks=("api/14_api_contract_matrix.ipynb",),
        api_ids=("api_contract", "exercise_api"),
    ),
)



def _signature(value: Any) -> str | None:
    try:
        return re.sub(r" at 0x[0-9A-Fa-f]+", "", str(inspect.signature(value)))
    except (TypeError, ValueError):
        return None


def _summary(value: Any, kind: str, identifier: str) -> str:
    documentation = inspect.getdoc(value) if value is not None else None
    if documentation:
        paragraph = documentation.split("\n\n", 1)[0]
        return " ".join(line.strip() for line in paragraph.splitlines())
    return f"Public {kind} contract for {identifier}."


def _source(value: Any) -> str:
    module = getattr(value, "__module__", None)
    qualified = getattr(value, "__qualname__", None) or getattr(value, "__name__", None)
    if module and qualified:
        return f"{module}:{qualified}"
    if isinstance(value, ModuleType):
        return value.__name__
    return type(value).__name__


def _kind(value: Any) -> str:
    if isinstance(value, ModuleType):
        return "namespace"
    if inspect.isclass(value):
        return "class"
    if inspect.iscoroutinefunction(value):
        return "async-function"
    if inspect.isfunction(value) or inspect.ismethod(value) or callable(value):
        return "function"
    return "constant"


def _member_value(owner: type[Any], name: str) -> Any:
    raw = inspect.getattr_static(owner, name, None)
    if isinstance(raw, (classmethod, staticmethod)):
        return raw.__func__
    if isinstance(raw, property):
        return raw.fget
    return raw
def _member_source(owner: type[Any], name: str) -> str:
    """Locate the defining library class while preserving the public API ID."""

    for base in owner.__mro__:
        if name not in base.__dict__:
            continue
        value = _member_value(base, name)
        if callable(value):
            return _source(value)
        return f"{_source(base)}.{name}"
    return f"{_source(owner)}.{name}"
def _field_exists(owner: type[Any], name: str) -> bool:
    """Resolve a declared field without constructing its owner."""

    static_member = inspect.getattr_static(owner, name, _MISSING) is not _MISSING
    annotated = any(
        isinstance(annotations := getattr(base, "__annotations__", {}), Mapping)
        and name in annotations
        for base in owner.__mro__
    )
    model_fields = getattr(owner, "model_fields", {})
    model_field = isinstance(model_fields, Mapping) and name in model_fields
    dataclass_field = is_dataclass(owner) and any(
        field.name == name for field in fields(owner)
    )
    return static_member or annotated or model_field or dataclass_field






def _public_member_names(owner: type[Any]) -> tuple[str, ...]:
    """Return the library-owned public surface visible on one exported class."""

    names: set[str] = set()
    owner_module = getattr(owner, "__module__", "")
    for base in owner.__mro__:
        base_module = getattr(base, "__module__", "")
        if (
            base is not owner
            and base_module != owner_module
            and not base_module.startswith("agentic_systems")
        ):
            continue

        annotations = getattr(base, "__annotations__", {})
        if isinstance(annotations, Mapping):
            names.update(name for name in annotations if not name.startswith("_"))

        for name, value in base.__dict__.items():
            if name.startswith("_") or name == "model_config":
                continue
            if inspect.ismodule(value) or inspect.isclass(value):
                continue
            names.add(name)

    model_fields = getattr(owner, "model_fields", {})
    if isinstance(model_fields, Mapping):
        names.update(name for name in model_fields if not name.startswith("_"))

    if is_dataclass(owner):
        names.update(field.name for field in fields(owner) if not field.name.startswith("_"))

    return tuple(sorted(names))


def _member_kind(owner: type[Any], name: str) -> str:
    raw = inspect.getattr_static(owner, name, None)
    if isinstance(raw, property):
        return "property"
    if isinstance(raw, classmethod):
        return "class-method"
    if isinstance(raw, staticmethod):
        return "static-method"
    if callable(raw):
        return "method"
    return "field"


def contract_entries(
    namespace: Any,
    names: tuple[str, ...],
    *,
    recommended: tuple[str, ...] = (),
) -> tuple[ApiContractEntry, ...]:
    """Project one public namespace into deterministic contract entries."""

    recommended_names = set(recommended)
    entries: list[ApiContractEntry] = []
    for name in names:
        value = getattr(namespace, name)
        tier = "recommended" if name in recommended_names else "advanced"
        entries.append(
            ApiContractEntry(
                id=name,
                export=name,
                member=None,
                kind=_kind(value),
                tier=tier,
                source=_source(value),
                summary=_summary(value, _kind(value), name),
                signature=_signature(value),
            )
        )
        if not inspect.isclass(value):
            continue
        for member in _public_member_names(value):
            member_value = _member_value(value, member)
            entries.append(
                ApiContractEntry(
                    id=f"{name}.{member}",
                    export=name,
                    member=member,
                    kind=_member_kind(value, member),
                    tier=tier,
                    source=_member_source(value, member),
                    summary=_summary(member_value, _member_kind(value, member), f"{name}.{member}"),
                    signature=_signature(member_value),
                )
            )
    return tuple(entries)


def _manifest_checksum(
    entries: tuple[ApiContractEntry, ...],
    scenarios: tuple[dict[str, Any], ...],
) -> str:
    entry_payload = "\n".join(
        f"{entry.id}|{entry.kind}|{entry.tier}|{entry.source}|{entry.signature or ''}|{entry.summary}"
        for entry in entries
    )
    scenario_payload = json.dumps(scenarios, sort_keys=True, separators=(",", ":"))
    payload = entry_payload + "\n--scenarios--\n" + scenario_payload
    return sha256(payload.encode("utf-8")).hexdigest()


def api_contract() -> dict[str, Any]:
    """Return the complete, JSON-serializable public API manifest."""

    import agentic_systems as namespace

    from .api import PUBLIC_API, RECOMMENDED_API

    entries = contract_entries(namespace, PUBLIC_API, recommended=RECOMMENDED_API)
    scenarios = tuple(scenario.to_dict() for scenario in CONTRACT_SCENARIOS)
    return {
        "schema_version": API_CONTRACT_SCHEMA_VERSION,
        "export_count": len(PUBLIC_API),
        "entry_count": len(entries),
        "scenario_count": len(scenarios),
        "scenario_ids": [scenario["id"] for scenario in scenarios],
        "scenarios": list(scenarios),
        "checksum": _manifest_checksum(entries, scenarios),
        "ids": [entry.id for entry in entries],
        "entries": [entry.to_dict() for entry in entries],
    }


def exercise_api(identifier: str | None = None) -> dict[str, Any]:
    """Resolve and verify one or every public API contract entry."""

    import agentic_systems as namespace

    manifest = api_contract()
    selected = [
        entry
        for entry in manifest["entries"]
        if identifier is None or entry["id"] == identifier
    ]
    if identifier is not None and not selected:
        raise KeyError(f"Unknown public API contract id {identifier!r}.")

    results: list[dict[str, Any]] = []
    for entry in selected:
        owner = getattr(namespace, entry["export"])
        if entry["member"] is None:
            resolved = owner is not None
        elif entry["kind"] == "field":
            resolved = _field_exists(owner, entry["member"])
        else:
            resolved = (
                inspect.getattr_static(owner, entry["member"], _MISSING) is not _MISSING
            )
        results.append(
            {
                "id": entry["id"],
                "ok": resolved,
                "kind": entry["kind"],
                "signature": entry["signature"],
                "source": entry["source"],
            }
        )
    return {
        "schema_version": API_CONTRACT_SCHEMA_VERSION,
        "ok": all(result["ok"] for result in results),
        "count": len(results),
        "checksum": manifest["checksum"],
        "results": results,
    }


__all__ = [
    "API_CONTRACT_SCHEMA_VERSION",
    "ApiContractEntry",
    "api_contract",
    "contract_entries",
    "exercise_api",
]
