"""Static, side-effect-free AgenticSystem inspection."""

from __future__ import annotations

import json
from typing import Any

from .integrations.boundary import framework_profiles
from .providers.conformance import provider_profiles


INSPECTION_SCHEMA_VERSION = "agentic_systems.inspect.v1"


class InspectReport(dict):
    """Serializable static-system report with a stable human projection."""

    def raise_if_errors(self) -> "InspectReport":
        if not self.get("ok"):
            errors = self.get("errors", [])
            raise ValueError(f"Agentic Systems inspect failed: {errors}")
        return self

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible report."""

        return json.loads(json.dumps(dict(self)))

    def human_text(self) -> str:
        """Return a stable, compact human-readable inspection."""

        entities = self.get("entities") or {}
        counts = {
            name: len(entities.get(name) or [])
            for name in ("tools", "skills", "agents", "toolkits")
        }
        providers = [
            item["provider"]
            for item in self.get("providers") or []
            if item.get("selected_by")
        ]
        frameworks = [
            item["framework"]
            for item in self.get("frameworks") or []
            if item.get("selected_by")
        ]
        diagnostics = self.get("diagnostics") or []
        lines = [
            "Agentic Systems static inspection",
            f"Status: {'OK' if self.get('ok') else 'ERROR'}",
            (
                "Entities: "
                f"tools={counts['tools']}, skills={counts['skills']}, "
                f"agents={counts['agents']}, toolkits={counts['toolkits']}"
            ),
            f"Relationships: {len(self.get('relationships') or [])}",
            f"Providers: {', '.join(providers) if providers else 'none selected'}",
            f"Frameworks: {', '.join(frameworks) if frameworks else 'none selected'}",
            f"Diagnostics: {len(diagnostics)}",
        ]
        for item in diagnostics:
            lines.append(
                f"- {str(item.get('severity') or 'warning').upper()} "
                f"{item.get('code')}: {item.get('message')} "
                f"Action: {item.get('suggestion')}"
            )
        return "\n".join(lines)


def build_inspection_report(
    system: Any,
    *,
    warnings: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> InspectReport:
    """Build one static report without executing Tools, Agents, or Providers."""

    agents = list(system._agents)
    composition = system.composition()
    entities = _entities(system, agents)
    relationships = _relationships(system, agents)
    contracts = _contracts(system, agents)
    providers, provider_risks = _providers(system, agents)
    frameworks, framework_risks = _frameworks(agents)
    conflicts = _conflicts(composition)
    limits = _limits(system, agents)
    risks = [*provider_risks, *framework_risks]
    diagnostics = [
        *(_diagnostic(item, severity="error") for item in errors),
        *(_diagnostic(item, severity="warning") for item in warnings),
        *risks,
    ]
    return InspectReport(
        schema_version=INSPECTION_SCHEMA_VERSION,
        inspection_kind="static",
        side_effects={"models_executed": 0, "tools_executed": 0},
        ok=not errors,
        model=system.model,
        region=system.region,
        strict=system.strict,
        tool_count=len(system.tools),
        tools=list(system.tool_names),
        agent_count=len(agents),
        agents=[agent.name for agent in agents],
        toolkit_count=len(system._toolkits),
        toolkits={
            name: list(toolkit.tool_names) for name, toolkit in system._toolkits.items()
        },
        skill_count=len(system._skills) + len(system._runtime_skills),
        skills=[skill.manifest.model_dump(mode="json") for skill in system._skills],
        runtime_skill_count=len(system._runtime_skills),
        runtime_skills=[skill.info() for skill in system._runtime_skills.values()],
        entities=entities,
        relationships=relationships,
        contracts=contracts,
        providers=providers,
        frameworks=frameworks,
        capabilities=_capabilities(providers),
        conflicts=conflicts,
        limits=limits,
        degradation_risks=risks,
        composition=composition,
        diagnostics=diagnostics,
        warnings=warnings,
        errors=errors,
    )


def _entities(system: Any, agents: list[Any]) -> dict[str, Any]:
    public_tools = {tool.name: tool for tool in system.public_tools}
    tools = []
    for name in system.tool_names:
        tool = public_tools.get(name)
        tools.append(
            tool.info()
            if tool is not None
            else {
                "identity": name,
                "name": name,
                "description": next(
                    (
                        spec.description
                        for spec in system._runtime.tools
                        if spec.name == name
                    ),
                    "",
                ),
                "registry": "runtime-only",
            }
        )
    runtime_skills = [skill.info() for skill in system._runtime_skills.values()]
    loaded_skills = [
        {
            "identity": skill.manifest.name,
            "kind": "loaded",
            "manifest": skill.manifest.model_dump(mode="json"),
        }
        for skill in system._skills
    ]
    return {
        "system": {
            "type": "AgenticSystem",
            "model": system.model,
            "region": system.region,
            "strict": system.strict,
        },
        "tools": tools,
        "skills": [*runtime_skills, *loaded_skills],
        "agents": [_agent_entity(agent) for agent in agents],
        "toolkits": [
            {"name": name, "tool_names": list(toolkit.tool_names)}
            for name, toolkit in system._toolkits.items()
        ],
    }


def _agent_entity(agent: Any) -> dict[str, Any]:
    return {
        "name": agent.name,
        "engine": getattr(agent, "engine", None),
        "framework": getattr(agent, "framework", None),
        "model": getattr(agent, "model", None),
        "tool_names": list(getattr(agent, "tools", ()) or ()),
        "skill_names": list(getattr(agent, "skills", ()) or ()),
    }


def _relationships(system: Any, agents: list[Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    def add(source: str, relation: str, target: str) -> None:
        items.append({"source": source, "relation": relation, "target": target})

    for name in system.tool_names:
        add("system", "owns", f"tool:{name}")
    for name, toolkit in system._toolkits.items():
        add("system", "owns", f"toolkit:{name}")
        for tool_name in toolkit.tool_names:
            add(f"toolkit:{name}", "groups", f"tool:{tool_name}")
    for skill in system._runtime_skills.values():
        add("system", "owns", f"skill:{skill.identity}")
        for tool_name in skill.tool_names:
            add(f"skill:{skill.identity}", "packages", f"tool:{tool_name}")
    for skill in system._skills:
        add("system", "owns", f"skill:{skill.manifest.name}")
        for tool_name in skill.manifest.tools:
            add(f"skill:{skill.manifest.name}", "packages", f"tool:{tool_name}")
    for agent in agents:
        source = f"agent:{agent.name}"
        add("system", "owns", source)
        for tool_name in getattr(agent, "tools", ()) or ():
            add(source, "uses", f"tool:{tool_name}")
        for skill_name in getattr(agent, "skills", ()) or ():
            add(source, "uses", f"skill:{skill_name}")
        if getattr(agent, "engine", None):
            add(source, "requests", f"provider:{agent.engine}")
        if getattr(agent, "framework", None):
            add(source, "requests", f"framework:{agent.framework}")
    return sorted(
        items, key=lambda item: (item["source"], item["relation"], item["target"])
    )


def _contracts(system: Any, agents: list[Any]) -> dict[str, Any]:
    return {
        "tools": [
            {
                "tool": tool.name,
                "strict": tool.strict,
                "input_schema": _schema(tool.input_schema),
                "output_schema": _schema(tool.output_schema),
            }
            for tool in system.public_tools
        ],
        "skills": [
            {
                "skill": skill.identity,
                "contracts": dict(skill.contracts),
                "policy": dict(skill.policy),
                "tools": [
                    {
                        "tool": tool.name,
                        "input_schema": _schema(tool.input_schema),
                        "output_schema": _schema(tool.output_schema),
                    }
                    for tool in skill.tools
                ],
            }
            for skill in system._runtime_skills.values()
        ],
        "agents": [
            {
                "agent": agent.name,
                "contract": _payload(getattr(agent, "contract", None)),
                "policy": _payload(getattr(agent, "policy", None)),
                "input_schema": _schema(getattr(agent, "input_contract", None)),
                "output_schema": _schema(getattr(agent, "output_contract", None)),
            }
            for agent in agents
        ],
    }


def _providers(
    system: Any, agents: list[Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    users: dict[str, list[str]] = {}
    runtime_config = getattr(system, "runtime_config", None)
    if runtime_config is not None:
        users.setdefault(runtime_config.provider, []).append("system")
    for agent in agents:
        provider = getattr(agent, "engine", None)
        if provider:
            users.setdefault(provider, []).append(f"agent:{agent.name}")

    profiles = []
    risks = []
    for profile in provider_profiles():
        payload = profile.to_dict()
        selected_by = sorted(users.get(profile.provider, ()))
        payload["selected_by"] = selected_by
        profiles.append(payload)
        if selected_by:
            for capability in (*profile.degradations, *profile.unsupported):
                risks.append(
                    _risk(
                        code=f"provider_capability_{capability.status}",
                        message=(
                            f"Provider {profile.provider!r} declares "
                            f"{capability.name!r} as {capability.status}: {capability.detail}"
                        ),
                        path=f"providers.{profile.provider}.capabilities.{capability.name}",
                        suggestion=(
                            "Choose a Provider that supports this capability or design the "
                            "workflow around the declared limitation."
                        ),
                        source=profile.provider,
                    )
                )
    if runtime_config is not None and runtime_config.provider == "auto":
        risks.append(
            _risk(
                code="provider_resolution_deferred",
                message="Provider selection is deferred through provider='auto'.",
                path="providers.auto",
                suggestion="Inspect RuntimeConfig.describe() in the target environment before execution.",
                source="auto",
            )
        )
    return profiles, risks


def _frameworks(agents: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    users: dict[str, list[str]] = {}
    for agent in agents:
        framework = getattr(agent, "framework", None)
        if framework:
            users.setdefault(framework, []).append(f"agent:{agent.name}")

    profiles = []
    risks = []
    for profile in framework_profiles():
        payload = profile.to_dict()
        selected_by = sorted(users.get(profile.framework, ()))
        payload["selected_by"] = selected_by
        profiles.append(payload)
    return profiles, risks


def _capabilities(providers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "providers": [
            {
                "provider": profile["provider"],
                "selected": bool(profile["selected_by"]),
                "capabilities": profile["capabilities"],
            }
            for profile in providers
        ]
    }


def _conflicts(composition: dict[str, Any]) -> dict[str, Any]:
    resolved = [
        event
        for event in composition.get("events", ())
        if event.get("decision") in {"keep", "replace"}
    ]
    return {"resolved": resolved, "unresolved": []}


def _limits(system: Any, agents: list[Any]) -> dict[str, Any]:
    runtime_config = getattr(system, "runtime_config", None)
    scheduler = runtime_config.scheduler.to_dict() if runtime_config is not None else {}
    return {
        "system_defaults": dict(system.defaults),
        "scheduler": scheduler,
        "agents": [
            {
                "agent": agent.name,
                "policy": _payload(getattr(agent, "policy", None)),
            }
            for agent in agents
        ],
    }


def _diagnostic(item: dict[str, Any], *, severity: str) -> dict[str, Any]:
    code = str(item.get("code") or item.get("issue") or "static_validation_issue")
    subject = item.get("tool") or item.get("path") or item.get("source") or "system"
    message = str(item.get("message") or f"{subject}: {code}")
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "path": item.get("path") or item.get("tool") or item.get("source"),
        "suggestion": _suggestion(code),
        "source": item.get("source") or "static_validation",
    }


def _risk(
    *,
    code: str,
    message: str,
    path: str,
    suggestion: str,
    source: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": "warning",
        "message": message,
        "path": path,
        "suggestion": suggestion,
        "source": source,
    }


def _suggestion(code: str) -> str:
    suggestions = {
        "tool_return_annotation_must_be_dict": (
            "Annotate the Tool as returning dict or configure an explicit output schema."
        ),
        "return_annotation_must_be_dict": (
            "Annotate the Tool as returning dict or configure an explicit output schema."
        ),
        "missing_description": "Add a non-empty Tool description for model-facing registries.",
    }
    return suggestions.get(
        code, "Review the referenced entity and update its static configuration."
    )


def _payload(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return dict(value)
    return {"type": _type_name(value)}


def _schema(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_json_schema"):
        return value.model_json_schema()
    return {"type": _type_name(value)}


def _type_name(value: Any) -> str:
    target = value if isinstance(value, type) else type(value)
    return f"{target.__module__}.{target.__qualname__}"


__all__ = ["INSPECTION_SCHEMA_VERSION", "InspectReport", "build_inspection_report"]
