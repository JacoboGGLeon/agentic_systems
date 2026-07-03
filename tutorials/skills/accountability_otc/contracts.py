"""Declarative contracts and policies for the packaged Accountability OTC skill."""

from __future__ import annotations

from typing import Any

import agentic_systems as lab

ACCOUNTABILITY_EXPECTED_FREE_SQL = lab.expect.exactly("free_sql")
ACCOUNTABILITY_EXPECTED_NL2SQL = lab.expect.exactly("nl2sql")
ACCOUNTABILITY_EXPECTED_TOOLS = lab.expect.all_of("free_sql", "nl2sql")
ACCOUNTABILITY_EXPECTED_TOOLS_ANY = lab.expect.any_of("free_sql", "nl2sql")


def single_tool_contract(tool_name: str) -> lab.AgentContract:
    return lab.AgentContract(
        must_call=[tool_name],
        tool_expectation=lab.expect.exactly(tool_name),
        completion="when_required_tools_satisfied",
        failure_policy="no_unresolved",
        expected_tool_outputs={tool_name: {"ok": True}},
    )


def single_tool_policy(tool_name: str, *, max_turns: int = 4) -> lab.RunPolicy:
    return lab.RunPolicy(
        max_turns=max_turns,
        max_tool_calls=1,
        temperature=0.0,
        tool_choice=tool_name,
        finalize="after_required_tools",
        trace="compact",
        strict=True,
    )


def skill_agent_contract() -> lab.AgentContract:
    return lab.AgentContract(
        tool_expectation=ACCOUNTABILITY_EXPECTED_TOOLS_ANY,
        completion="when_required_tools_satisfied",
        failure_policy="no_unresolved",
    )


def skill_agent_policy() -> lab.RunPolicy:
    return lab.RunPolicy(
        max_turns=6,
        max_tool_calls=1,
        temperature=0.0,
        tool_choice="auto",
        finalize="after_required_tools",
        trace="compact",
        strict=True,
    )


ACCOUNTABILITY_FREE_SQL_SPEC = lab.ContractPolicySpec(
    name="accountability_otc_skill.free_sql",
    description="Skill tool contract: one successful free_sql call.",
    contract=single_tool_contract("free_sql"),
    policy=single_tool_policy("free_sql"),
    tags=["accountability", "skill", "free_sql"],
)

ACCOUNTABILITY_NL2SQL_SPEC = lab.ContractPolicySpec(
    name="accountability_otc_skill.nl2sql",
    description="Skill tool contract: one successful nl2sql call.",
    contract=single_tool_contract("nl2sql"),
    policy=single_tool_policy("nl2sql", max_turns=6),
    tags=["accountability", "skill", "nl2sql"],
)

ACCOUNTABILITY_SKILL_AGENT_SPEC = lab.ContractPolicySpec(
    name="accountability_otc_skill.agent",
    description="Skill agent contract: route to one of the packaged public tools.",
    contract=skill_agent_contract(),
    policy=skill_agent_policy(),
    tags=["accountability", "skill", "agent"],
)

ACCOUNTABILITY_SKILL_CONTRACTS = {
    "free_sql": ACCOUNTABILITY_FREE_SQL_SPEC,
    "nl2sql": ACCOUNTABILITY_NL2SQL_SPEC,
    "agent": ACCOUNTABILITY_SKILL_AGENT_SPEC,
}


LINEAGE_GOALS = {
    "free_sql": "Explain what SQL evidence was executed, how it was constrained, and why the answer follows from returned rows.",
    "nl2sql": "Explain the business question, the generated SQL plan, the executed evidence, and why the final answer is supported.",
    "agent": "Explain which accountability route was selected and why the selected tool evidence supports the answer.",
}


def lineage_goal_for_route(route: str) -> str:
    """Return the explanation goal used when building LineageMemory for this route."""

    key = str(route or "").strip()
    if key not in LINEAGE_GOALS:
        raise KeyError(f"Unknown lineage route {route!r}. Available: {sorted(LINEAGE_GOALS)}")
    return LINEAGE_GOALS[key]



def build_lineage_memory(
    result: Any,
    *,
    route: str = "agent",
    name: str | None = None,
    question: Any = "",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    max_tool_rows: int = 3,
) -> lab.LineageMemory:
    """Build route-aware Lineage Memory for Accountability OTC results.

    The package owns the explanation goal for each route. Notebooks only pass
    the actual result and question, keeping business lineage consistent across
    direct tools, agents and skills.
    """

    key = str(route or "agent").strip()
    memory_name = name or f"accountability_otc_skill.{key}.lineage"
    lineage_tags = ["accountability", "skill", key]
    lineage_tags.extend(str(item) for item in (tags or []) if str(item))
    return result.lineage(
        name=memory_name,
        question=question,
        goal=lineage_goal_for_route(key),
        tags=lineage_tags,
        metadata=metadata or {},
        max_tool_rows=max_tool_rows,
    )


def contract_policy_for_route(route: str) -> lab.ContractPolicySpec:
    key = str(route or "").strip()
    if key not in ACCOUNTABILITY_SKILL_CONTRACTS:
        raise KeyError(f"Unknown skill contract route {route!r}. Available: {sorted(ACCOUNTABILITY_SKILL_CONTRACTS)}")
    return ACCOUNTABILITY_SKILL_CONTRACTS[key]


def describe_contracts(*, available_tools: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    return {
        key: {
            **spec.describe(),
            "static_check": spec.check(available_tools=available_tools).to_dict(),
        }
        for key, spec in ACCOUNTABILITY_SKILL_CONTRACTS.items()
    }


__all__ = [
    "ACCOUNTABILITY_EXPECTED_FREE_SQL",
    "ACCOUNTABILITY_EXPECTED_NL2SQL",
    "ACCOUNTABILITY_EXPECTED_TOOLS",
    "ACCOUNTABILITY_EXPECTED_TOOLS_ANY",
    "ACCOUNTABILITY_FREE_SQL_SPEC",
    "ACCOUNTABILITY_NL2SQL_SPEC",
    "ACCOUNTABILITY_SKILL_AGENT_SPEC",
    "ACCOUNTABILITY_SKILL_CONTRACTS",
    "lineage_goal_for_route",
    "build_lineage_memory",
    "contract_policy_for_route",
    "describe_contracts",
    "LINEAGE_GOALS",
    "single_tool_contract",
    "single_tool_policy",
    "skill_agent_contract",
    "skill_agent_policy",
]
