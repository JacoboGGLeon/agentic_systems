"""Deterministic operators used by the Agentic Systems Studio examples."""

from __future__ import annotations

import ast
import csv
import io
import re
from statistics import mean

import agentic_systems as toolkit
from agentic_systems.registry import FRAMEWORK_NAMES, PROVIDER_NAMES


def _lines(text: str) -> list[str]:
    return [line.strip(" -\t") for line in str(text).splitlines() if line.strip()]


def _sentences(text: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+|\n+", str(text))
        if item.strip()
    ]


@toolkit.tool
def inspect_creator_request(text: str) -> dict:
    """Extract explicit requirements and architecture signals from a creator request."""

    lowered = text.lower()
    providers = [
        name
        for name in (item.removesuffix("-runtime") for item in PROVIDER_NAMES)
        if name in lowered
    ]
    frameworks = [name for name in FRAMEWORK_NAMES if name in lowered]
    return {
        "summary": "Creator request inspected deterministically.",
        "requirements": _lines(text),
        "provider_signals": providers,
        "framework_signals": frameworks,
        "needs_tools": any(
            word in lowered for word in ("tool", "api", "database", "file")
        ),
        "needs_environment": any(
            word in lowered for word in ("episode", "environment", "simulation")
        ),
        "needs_evals": "eval" in lowered or "test" in lowered,
    }


@toolkit.tool
def extract_research_evidence(text: str) -> dict:
    """Extract claim, URL, number and uncertainty candidates without browsing."""

    sentences = _sentences(text)
    return {
        "summary": "Research evidence candidates extracted.",
        "claims": sentences[:12],
        "urls": re.findall(r"https?://[^\s)]+", text),
        "numbers": re.findall(r"(?<!\w)[+-]?(?:\d+[.,]?\d*|\.\d+)%?", text),
        "uncertainty_markers": [
            marker
            for marker in (
                "quizá",
                "tal vez",
                "posiblemente",
                "aproximadamente",
                "maybe",
            )
            if marker in text.lower()
        ],
    }


@toolkit.tool
def normalize_decision_context(text: str) -> dict:
    """Normalize options, criteria, constraints and assumptions in a decision request."""

    lines = _lines(text)
    return {
        "summary": "Decision context normalized.",
        "options": [
            line
            for line in lines
            if re.search(r"\b(opci[oó]n|alternativa|vs\.?|versus)\b", line, re.I)
        ],
        "criteria": [
            line
            for line in lines
            if re.search(
                r"\b(costo|tiempo|riesgo|calidad|latencia|seguridad)\b", line, re.I
            )
        ],
        "constraints": [
            line
            for line in lines
            if re.search(
                r"\b(debe|l[ií]mite|m[aá]ximo|no puede|restricci[oó]n)\b", line, re.I
            )
        ],
        "assumptions": [
            line
            for line in lines
            if re.search(r"\b(asum|supong|hip[oó]tesis)\b", line, re.I)
        ],
    }


@toolkit.tool
def triage_incident_signals(text: str) -> dict:
    """Score visible incident signals and preserve them as deterministic evidence."""

    lowered = text.lower()
    weights = {
        "outage": 4,
        "caído": 4,
        "data loss": 5,
        "pérdida de datos": 5,
        "security": 4,
        "seguridad": 4,
        "latency": 2,
        "latencia": 2,
        "error": 1,
        "customer": 1,
        "cliente": 1,
    }
    hits = {signal: score for signal, score in weights.items() if signal in lowered}
    score = min(10, sum(hits.values()))
    severity = (
        "critical"
        if score >= 8
        else "high"
        if score >= 5
        else "medium"
        if score >= 2
        else "low"
    )
    return {
        "summary": f"Incident signals indicate {severity} heuristic severity.",
        "severity": severity,
        "score": score,
        "signals": hits,
        "timestamps": re.findall(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", text),
        "facts": _lines(text),
    }


@toolkit.tool
def inspect_python_source(text: str) -> dict:
    """Inspect Python syntax and static structure without executing source code."""

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {
            "summary": "Python source is invalid.",
            "valid": False,
            "error": {"line": exc.lineno, "offset": exc.offset, "message": exc.msg},
        }
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    risky = sorted(set(calls) & {"eval", "exec", "compile", "open", "__import__"})
    return {
        "summary": "Python source inspected without execution.",
        "valid": True,
        "functions": [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ],
        "classes": [
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ],
        "imports": [
            ast.unparse(node)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ],
        "risky_calls": risky,
        "node_count": sum(1 for _ in ast.walk(tree)),
    }


def _extract_csv_payload(text: str) -> str:
    raw = str(text).strip()
    fenced = re.search(
        r"\x60\x60\x60(?:csv)?\s*(.*?)\x60\x60\x60", raw, flags=re.I | re.S
    )
    if fenced:
        raw = fenced.group(1).strip()

    lines = [line for line in raw.splitlines() if line.strip()]
    for start, line in enumerate(lines):
        header = next(csv.reader([line]))
        if len(header) < 2:
            continue
        accepted = [line]
        width = len(header)
        for candidate in lines[start + 1 :]:
            values = next(csv.reader([candidate]))
            if len(values) != width:
                break
            accepted.append(candidate)
        if len(accepted) >= 2:
            return "\n".join(accepted)
    return raw


@toolkit.tool
def profile_csv_text(text: str) -> dict:
    """Profile CSV-shaped text deterministically."""

    rows = list(csv.DictReader(io.StringIO(_extract_csv_payload(text))))
    columns = list(rows[0]) if rows else []
    null_counts = {
        column: sum(not str(row.get(column, "")).strip() for row in rows)
        for column in columns
    }
    fingerprints = [tuple(row.get(column, "") for column in columns) for row in rows]
    return {
        "summary": "CSV profile calculated deterministically.",
        "row_count": len(rows),
        "columns": columns,
        "null_counts": null_counts,
        "duplicate_rows": len(fingerprints) - len(set(fingerprints)),
        "sample": rows[:5],
    }


@toolkit.tool
def scan_prompt_security(text: str) -> dict:
    """Detect visible prompt-injection and secret-exfiltration patterns."""

    rules = {
        "ignore_instructions": r"ignore (?:all |previous |prior )?instructions|ignora (?:todas )?las instrucciones",
        "system_prompt": r"system prompt|mensaje del sistema",
        "secret_request": r"api[_ -]?key|password|contrase(?:ñ|n)a|secret|token",
        "tool_abuse": r"call (?:the )?tool|ejecuta (?:la )?herramienta|run shell",
        "exfiltration": r"send .* to https?://|env[ií]a .* a https?://",
    }
    hits = {
        name: re.findall(pattern, text, flags=re.I) for name, pattern in rules.items()
    }
    hits = {name: values for name, values in hits.items() if values}
    return {
        "summary": "Prompt security rules evaluated.",
        "risk": "high" if len(hits) >= 3 else "medium" if hits else "low",
        "rule_hits": hits,
        "treat_as_untrusted_data": bool(hits),
    }


@toolkit.tool
def extract_meeting_actions(text: str) -> dict:
    """Extract explicit decisions, actions, owners and dates from meeting notes."""

    lines = _lines(text)
    return {
        "summary": "Meeting evidence extracted.",
        "actions": [
            line
            for line in lines
            if re.search(
                r"\b(todo|action|acci[oó]n|har[aá]|debe|follow.?up)\b", line, re.I
            )
        ],
        "decisions": [
            line
            for line in lines
            if re.search(r"\b(decid|acord|approved|aprob)\b", line, re.I)
        ],
        "dates": re.findall(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b", text),
        "owners": re.findall(r"@([A-Za-z0-9_.-]+)", text),
    }


@toolkit.tool
def calculate_quant_evidence(text: str) -> dict:
    """Extract numeric values and calculate basic descriptive evidence."""

    numbers = [
        float(value.replace(",", ""))
        for value in re.findall(r"[+-]?\d+(?:,\d{3})*(?:\.\d+)?", text)
    ]
    return {
        "summary": "Quantitative evidence calculated.",
        "values": numbers,
        "count": len(numbers),
        "sum": sum(numbers) if numbers else None,
        "mean": mean(numbers) if numbers else None,
        "minimum": min(numbers) if numbers else None,
        "maximum": max(numbers) if numbers else None,
    }


@toolkit.tool
def classify_support_ticket(text: str) -> dict:
    """Classify a customer-support ticket using transparent keyword rules."""

    lowered = text.lower()
    categories = {
        "billing": ("invoice", "charge", "charged", "factura", "cobro"),
        "access": ("login", "password", "access", "sesión", "contraseña", "acceso"),
        "incident": ("down", "error", "failed", "caído", "falla"),
        "feature": ("feature", "request", "funcionalidad", "mejora"),
    }
    scores = {
        name: sum(word in lowered for word in words)
        for name, words in categories.items()
    }
    category = max(scores, key=scores.get) if any(scores.values()) else "general"
    urgent = any(
        word in lowered
        for word in (
            "urgent",
            "urgente",
            "production",
            "producción",
            "blocked",
            "bloqueado",
        )
    )
    return {
        "summary": "Support ticket classified deterministically.",
        "category": category,
        "priority": "high" if urgent else "normal",
        "scores": scores,
        "facts": _lines(text),
    }


@toolkit.tool
def record_reasoning_evidence(note: str) -> dict:
    """Record a concise evidence note emitted by a reasoning agent."""

    return {"summary": "Reasoning evidence recorded.", "note": note.strip()}


@toolkit.tool
def validate_review_claim(answer: str) -> dict:
    """Perform deterministic surface validation of a proposed final answer."""

    text = answer.strip()
    return {
        "summary": "Review claim validated at the deterministic boundary.",
        "non_empty": bool(text),
        "length": len(text),
        "contains_unqualified_guarantee": bool(
            re.search(r"\b(always|never fails|guaranteed|100%)\b", text, re.I)
        ),
    }


OPERATOR_TOOLS = {
    "agentic-systems-creator": inspect_creator_request,
    "research-synthesis": extract_research_evidence,
    "decision-intelligence": normalize_decision_context,
    "incident-response": triage_incident_signals,
    "code-review": inspect_python_source,
    "data-quality": profile_csv_text,
    "prompt-security": scan_prompt_security,
    "meeting-action-center": extract_meeting_actions,
    "quantitative-analysis": calculate_quant_evidence,
    "customer-support": classify_support_ticket,
}

TOOLS = {
    **{tool.name: tool for tool in OPERATOR_TOOLS.values()},
    record_reasoning_evidence.name: record_reasoning_evidence,
    validate_review_claim.name: validate_review_claim,
}


__all__ = [
    "OPERATOR_TOOLS",
    "TOOLS",
    "record_reasoning_evidence",
    "validate_review_claim",
]
