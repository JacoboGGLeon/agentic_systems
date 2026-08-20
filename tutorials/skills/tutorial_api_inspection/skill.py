"""Small, domain-neutral runtime Skill for the Core 02 tutorial."""

from __future__ import annotations

import agentic_systems as toolkit


@toolkit.tool
def describe_public_symbol(symbol: str = "skill") -> dict[str, object]:
    """Describe whether a name belongs to the installed public API."""

    value = getattr(toolkit, symbol, None)
    return {
        "symbol": symbol,
        "is_public": symbol in toolkit.__all__,
        "kind": type(value).__name__ if value is not None else None,
    }


@toolkit.tool
def installed_version() -> dict[str, str]:
    """Return the installed Agentic Systems version."""

    return {"package_version": toolkit.__version__}


def build_skill() -> toolkit.Skill:
    """Build the portable runtime Skill without creating a system."""

    return toolkit.skill(
        name="tutorial_api_inspection",
        version="2.0.0",
        description="Inspecciona la API pública instalada desde una Skill de filesystem.",
        tools=[describe_public_symbol, installed_version],
        prompts={
            "instructions": (
                "Usa describe_public_symbol para responder con evidencia de la "
                "instalación local de Agentic Systems."
            )
        },
        contracts={
            "default": toolkit.AgentContract(
                must_call=["describe_public_symbol"]
            ).model_dump(mode="json")
        },
        policy=toolkit.RunPolicy(max_tool_calls=1, max_turns=2).model_dump(mode="json"),
        metadata={"domain": "tutorial", "tutorial": "core/02_skills"},
    )
