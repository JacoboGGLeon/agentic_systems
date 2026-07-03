"""Environment helpers for the packaged Accountability OTC skill."""

from __future__ import annotations

from typing import Any

import agentic_systems as lab

from .prompts import ACCOUNTABILITY_NL2SQL_PROMPT
from .skill import build_skill
from .contracts import build_lineage_memory


def decision_cases(*, load_date: str = "", limit: int = 10) -> list[dict[str, Any]]:
    """Return two route-decision cases against the packaged skill tools."""

    return [
        {
            "case_id": "skill_free_sql_catalog",
            "route": "free_sql",
            "input": {"query_id": "otc_exposure_by_currency", "load_date": load_date, "limit": limit},
            "expected_tool": "free_sql",
            "why": "Known catalog query should use the skill free_sql tool.",
        },
        {
            "case_id": "skill_nl2sql_question",
            "route": "nl2sql",
            "input": {"question": "mtm por clase de activo", "load_date": load_date, "limit": limit},
            "expected_tool": "nl2sql",
            "why": "Natural-language OTC question should use the skill nl2sql tool.",
        },
    ]


def _tool_by_name(tools: list[Any], name: str) -> Any:
    for tool in tools:
        if tool.name == name:
            return tool
    raise KeyError(f"Tool {name!r} not found. Available: {[tool.name for tool in tools]}")


def make_skill_decision_transition(tools: list[Any]):
    """Create a transition function that routes each row to one skill tool."""

    def _transition(row: dict[str, Any], action: Any, info: dict[str, Any]) -> dict[str, Any]:
        selected = str(((action or {}).get("tool") if isinstance(action, dict) else "") or row["route"])
        tool = _tool_by_name(tools, selected)
        result = tool.run(row["input"])
        data = getattr(result, "data", {}) or {}
        summary = data.get("summary") if isinstance(data, dict) else None
        memory = info.get("memory") or {}
        return {
            "selected_tool": selected,
            "tool_result": result.to_dict(),
            "summary": summary or getattr(result, "text", ""),
            "ok": result.ok and selected == row.get("expected_tool"),
            "memory": {
                **memory,
                "routes": [*memory.get("routes", []), selected],
                "case_ids": [*memory.get("case_ids", []), row.get("case_id")],
            },
        }

    return _transition


def reward_skill_decision(state: dict[str, Any], row: dict[str, Any], action: Any, env: lab.AgenticEnvironment) -> float:
    """Reward correct skill-tool selection plus successful tool result."""

    return 1.0 if state.get("ok") else 0.0


def build_skill_decision_environment(
    *,
    skill: Any | None = None,
    cases: list[dict[str, Any]] | None = None,
    name: str = "accountability_skill_decision_environment",
    **skill_kwargs: Any,
) -> lab.AgenticEnvironment:
    """Build a two-step environment over the packaged skill's public tools."""

    resolved_skill = skill or build_skill(**skill_kwargs)
    return lab.AgenticEnvironment(
        records=cases or decision_cases(),
        name=name,
        transition_fn=make_skill_decision_transition(resolved_skill.tools),
        reward_fn=reward_skill_decision,
        render_mode="history",
    )


def lineage_for_environment(env: lab.AgenticEnvironment, *, question: str = "") -> lab.LineageMemory:
    """Return skill-environment lineage with Accountability wording."""

    return env.lineage(
        name=f"{env.name}.lineage",
        question=question,
        goal="Explain which packaged skill tool was selected at each step and why the result is supported.",
        tags=["accountability", "skills", "environment"],
    )


__all__ = [
    "build_skill_decision_environment",
    "decision_cases",
    "lineage_for_environment",
    "make_skill_decision_transition",
    "reward_skill_decision",
]
