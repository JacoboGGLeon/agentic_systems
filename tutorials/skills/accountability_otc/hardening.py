"""Accountability hardening helpers for live OTC walkthroughs.

These helpers are intentionally domain-light.  They do not execute Athena or
Bedrock by themselves; they inspect already-produced tool/agent/environment
results and turn failures into structured, notebook-friendly diagnostics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

import agentic_systems as lab


@dataclass(frozen=True)
class AccountabilityDiagnostic:
    """Structured diagnosis for one live accountability step."""

    ok: bool
    stage: str
    where: str
    status: str
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    likely_causes: list[str] = field(default_factory=list)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def hardening_checklist() -> list[dict[str, str]]:
    """Return the 2.4.8 hardening story for accountability notebooks."""

    return [
        {
            "step": "structured_result",
            "why": "Every tool/agent/environment returns a structured result instead of crashing the notebook.",
        },
        {
            "step": "contract_policy",
            "why": "The expected tool route and execution limits are declared before the run.",
        },
        {
            "step": "lineage_memory",
            "why": "Every important output can explain what happened, how it happened and why to trust it.",
        },
        {
            "step": "environment_eval",
            "why": "free_sql vs nl2sql decisions can be scored step by step without coupling to one agent framework.",
        },
        {
            "step": "live_diagnostic",
            "why": "Athena/Bedrock failures are shown as evidence-rich diagnostics, not silent notebook deaths.",
        },
    ]


def diagnose_result(
    result: Any,
    *,
    stage: str = "accountability",
    expected_tool: str | None = None,
    expected_route: str | None = None,
) -> dict[str, Any]:
    """Inspect a tool/agent/environment result and return a stable diagnostic.

    Parameters
    ----------
    result:
        A raw tool payload, ``RunResult``, ``EvalReport`` or ``AgenticEnvironment``.
    stage:
        Notebook stage where the result was produced.
    expected_tool / expected_route:
        Optional expectations used to flag mismatched decisions.
    """

    payload = _extract_payload(result)
    ok = bool(payload.get("ok", True))
    tool = _first_text(payload, "tool", "name", default="")
    route = _first_text(payload, "route", default="")
    where = tool or route or stage
    summary = _first_text(payload, "summary", "text", "error", default="")
    if not summary:
        summary = "Resultado estructurado sin summary explícito."

    issues: list[str] = []
    if expected_tool and tool and tool != expected_tool:
        ok = False
        issues.append(f"expected_tool={expected_tool}, actual_tool={tool}")
    if expected_route and route and route != expected_route:
        ok = False
        issues.append(f"expected_route={expected_route}, actual_route={route}")

    error_message = _first_text(payload, "error", default="")
    likely_causes = classify_live_error(error_message or summary) if not ok or error_message else []
    next_action = _next_action(likely_causes, ok=ok)
    evidence = _diagnostic_evidence(payload, expected_tool=expected_tool, expected_route=expected_route, issues=issues)

    diagnostic = AccountabilityDiagnostic(
        ok=ok,
        stage=stage,
        where=where,
        status="OK" if ok else "ERROR",
        summary=summary,
        evidence=evidence,
        likely_causes=likely_causes,
        next_action=next_action,
    )
    return diagnostic.to_dict()


def classify_live_error(message: str) -> list[str]:
    """Classify common live Athena/Bedrock failure messages."""

    text = (message or "").lower()
    causes: list[str] = []
    if any(token in text for token in ("credential", "unable to locate credentials", "expiredtoken", "invalidclienttoken")):
        causes.append("AWS credentials/session are missing or expired.")
    if any(token in text for token in ("accessdenied", "not authorized", "permission", "forbidden")):
        causes.append("AWS permissions are insufficient for the requested Bedrock/Athena action.")
    if any(token in text for token in ("timeout", "timed out", "throttl", "too many requests", "rate exceeded")):
        causes.append("The live service timed out or throttled the request.")
    if any(token in text for token in ("athena", "invalidrequestexception", "syntax", "line ", "query")):
        causes.append("Athena query execution or SQL validation needs inspection.")
    if any(token in text for token in ("bedrock", "validationexception", "model", "converse")):
        causes.append("Bedrock Runtime request/model configuration needs inspection.")
    if not causes:
        causes.append("The live runtime returned a structured error; inspect summary, sql and query evidence.")
    return causes


def diagnostic_lineage(
    diagnostic: Mapping[str, Any],
    *,
    name: str = "accountability.diagnostic.lineage",
    question: str = "",
    goal: str = "Explain live accountability diagnostic evidence.",
) -> lab.LineageMemory:
    """Convert one diagnostic into Lineage Memory for consistent display."""

    status = str(diagnostic.get("status") or "UNKNOWN")
    summary = str(diagnostic.get("summary") or "")
    evidence = dict(diagnostic.get("evidence") or {})
    causes = list(diagnostic.get("likely_causes") or [])
    steps = [
        lab.LineageStep(
            step_id="diagnostic_result",
            kind="decision",
            title=f"Live diagnostic: {diagnostic.get('where') or diagnostic.get('stage')}",
            summary=f"{status}: {summary}",
            source="accountability_hardening",
            why="Live notebooks should explain failures and partial evidence instead of hiding them.",
            evidence=evidence,
        )
    ]
    if causes:
        steps.append(
            lab.LineageStep(
                step_id="likely_causes",
                kind="validation",
                title="Likely causes",
                summary="; ".join(str(item) for item in causes),
                source="accountability_hardening",
                why="The diagnostic classifies common Athena/Bedrock failure modes for faster debugging.",
                evidence={"likely_causes": causes, "next_action": diagnostic.get("next_action")},
            )
        )
    return lab.LineageMemory(
        name=name,
        question=question,
        goal=goal,
        answer=f"{status}: {summary}",
        ok=bool(diagnostic.get("ok")),
        steps=steps,
        tags=["accountability", "hardening", "diagnostic"],
        metadata={"diagnostic": dict(diagnostic)},
    )


def hardening_summary(results: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize diagnostics across an accountability notebook."""

    diagnostics = [diagnose_result(value, stage=key) for key, value in results.items()]
    failed = [item for item in diagnostics if not item["ok"]]
    return {
        "ok": not failed,
        "total": len(diagnostics),
        "failed": len(failed),
        "diagnostics": diagnostics,
    }


def _extract_payload(result: Any) -> dict[str, Any]:
    if hasattr(result, "normalized"):
        normalized = result.normalized()
        answer = normalized.get("answer") if isinstance(normalized.get("answer"), dict) else {}
        final = answer.get("final") if isinstance(answer.get("final"), dict) else {}
        data = answer.get("data") if isinstance(answer.get("data"), dict) else {}
        tools = normalized.get("tools") if isinstance(normalized.get("tools"), list) else []
        tool_payload = tools[0] if tools and isinstance(tools[0], dict) else {}
        errors = normalized.get("errors") if isinstance(normalized.get("errors"), list) else []
        error_text = "; ".join(str(item.get("message") or item.get("error") or item) for item in errors if isinstance(item, dict))
        return {
            **data,
            **final,
            **tool_payload,
            "ok": normalized.get("ok"),
            "summary": final.get("summary") or data.get("summary") or tool_payload.get("summary") or answer.get("text"),
            "error": final.get("error") or data.get("error") or tool_payload.get("error") or error_text,
        }
    if hasattr(result, "to_dict"):
        value = result.to_dict()
        return value if isinstance(value, dict) else {"value": value}
    if isinstance(result, Mapping):
        return dict(result)
    return {"ok": False, "summary": str(result), "error": "Unsupported result object for accountability diagnostics."}


def _first_text(payload: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return str(value)
    return default


def _diagnostic_evidence(
    payload: Mapping[str, Any],
    *,
    expected_tool: str | None,
    expected_route: str | None,
    issues: list[str],
) -> dict[str, Any]:
    table = payload.get("table") if isinstance(payload.get("table"), Mapping) else {}
    query = payload.get("query") if isinstance(payload.get("query"), Mapping) else {}
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else table.get("rows") or []
    evidence = {
        "tool": payload.get("tool") or payload.get("name"),
        "route": payload.get("route"),
        "query_id": query.get("query_id") or payload.get("query_id"),
        "rows": table.get("n_rows", len(rows) if isinstance(rows, list) else None),
        "has_sql": bool(payload.get("sql")),
        "expected_tool": expected_tool,
        "expected_route": expected_route,
        "issues": issues,
    }
    return {key: value for key, value in evidence.items() if value not in (None, "", [], {})}


def _next_action(causes: list[str], *, ok: bool) -> str:
    if ok:
        return "Continue: result is structured and aligned with the declared expectation."
    joined = " ".join(causes).lower()
    if "credentials" in joined or "permissions" in joined:
        return "Refresh AWS session/role permissions, then rerun only the failed cell."
    if "athena" in joined or "sql" in joined:
        return "Inspect the rendered SQL and run the direct free_sql path before the agent path."
    if "bedrock" in joined or "model" in joined:
        return "Run a small Bedrock Runtime sanity check before the NL2SQL/agent cell."
    if "timed out" in joined or "throttled" in joined:
        return "Reduce limit/batch size or rerun after the live service recovers."
    return "Inspect the structured error and preserve the diagnostic lineage for review."


__all__ = [
    "AccountabilityDiagnostic",
    "classify_live_error",
    "diagnose_result",
    "diagnostic_lineage",
    "hardening_checklist",
    "hardening_summary",
]
