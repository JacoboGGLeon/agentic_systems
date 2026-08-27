"""Lineage memory for compact, explainable Agentic Systems runs.

Lineage Memory is intentionally smaller than observability.  It does not own
runtime execution, tracing backends, logs, or distributed spans.  It projects a
``RunResult`` into a compact narrative/evidence object that can answer:

- what happened,
- how it happened,
- why this answer is supported,
- what compact context can be reused in the next prompt.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

LINEAGE_SCHEMA_VERSION = "agentic_systems.lineage.v1"
LineageKind = Literal[
    "input", "execution", "decision", "tool", "validation", "answer", "error", "context"
]


def _safe_json(value: Any, *, max_chars: int = 800) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        text = str(value)
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)] + "..."


def _short(value: Any, *, max_chars: int = 220) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)] + "..."


def _is_missing(value: Any) -> bool:
    """Return true when a routing/metadata value should not be printed as evidence."""

    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in {
        "",
        "none",
        "null",
        "n/a",
        "-",
    }:
        return True
    return False


def _natural_summary(text: Any) -> str:
    """Small renderer polish for common framework/internal summaries."""

    clean = str(text or "").strip()
    if not clean:
        return ""

    lower = clean.lower()
    if lower.startswith("route=none;"):
        reason = clean.split(";", 1)[1].strip() if ";" in clean else ""
        if reason.lower() == "the graph produced a routing plan.":
            return "El orquestador generó un plan de ejecución."
        return reason or "El orquestador generó un plan de ejecución."
    if lower == "the graph produced a routing plan.":
        return "El orquestador generó un plan de ejecución."
    if " executed via " in lower:
        name, rest = clean.split(" executed via ", 1)
        rest = rest.rstrip(".").strip()
        if rest == "tool call":
            return f"Tool {name} ejecutada correctamente."
        if " and returned " in rest:
            route, rows = rest.split(" and returned ", 1)
            return f"Tool {name} ejecutada vía {route}; {rows}."
        return f"Tool {name} ejecutada vía {rest}."
    if lower.endswith(" executed."):
        name = clean[: -len(" executed.")].strip()
        if name:
            return f"Tool {name} ejecutada correctamente."
    if lower == "contract validation passed.":
        return "Validación de contrato: OK."
    if lower == "graph validation passed.":
        return "Validación del grafo: OK."
    if lower == "contract validation reported issues.":
        return "Validación de contrato: revisar incidencias."
    if lower == "graph validation reported issues.":
        return "Validación del grafo: revisar incidencias."
    return clean


def _evidence_facts(step: "LineageStep") -> dict[str, Any]:
    if not isinstance(step.evidence, dict):
        return {}
    facts = step.evidence.get("facts")
    if isinstance(facts, dict):
        return facts
    tool = step.evidence.get("tool")
    if isinstance(tool, dict):
        return tool
    validation = step.evidence.get("validation")
    if isinstance(validation, dict):
        return validation
    return {}


def _status_label(value: Any) -> str:
    if value is True:
        return "OK"
    if value is False:
        return "REVISAR"
    return str(value) if value not in (None, "") else "registrado"


def _derive_support_reasons(steps: list["LineageStep"], *, ok: bool) -> list[str]:
    """Derive support bullets from structured lineage evidence, not canned prose."""

    reasons: list[str] = []

    tool_steps = [step for step in steps if step.kind == "tool"]
    if tool_steps:
        names = []
        for step in tool_steps:
            name = (
                step.source
                or step.title.replace("Tool:", "").replace("Tool evidence:", "").strip()
            )
            if name and name not in names:
                names.append(name)
        label = ", ".join(names[:4])
        if len(names) > 4:
            label += f", +{len(names) - 4} más"
        reasons.append(f"Salida estructurada disponible: {label}.")

    decision_steps = [step for step in steps if step.kind == "decision"]
    if decision_steps:
        reasons.append("Ruta o plan de ejecución registrado en el lineage.")

    validation_steps = [step for step in steps if step.kind == "validation"]
    for step in validation_steps:
        facts = _evidence_facts(step)
        status = facts.get("ok")
        if status is None and isinstance(facts.get("validation"), dict):
            status = facts["validation"].get("ok")
        if status is None:
            status = "registrado"
        title_lower = step.title.lower()
        label = "Validación"
        if "eval" in title_lower or "score" in title_lower:
            label = "Scoring del eval"
        elif "graph" in title_lower:
            label = "Validación del grafo"
        elif "contract" in title_lower or "contrato" in title_lower:
            label = "Validación de contrato"
        reasons.append(f"{label}: {_status_label(status)}.")

    error_steps = [step for step in steps if step.kind == "error"]
    if not error_steps and ok:
        reasons.append("No hay errores registrados en esta ejecución.")

    if not reasons:
        reasons.append(
            "La respuesta final conserva evidencia asociada en el RunResult o estado del sistema."
        )

    unique: list[str] = []
    for reason in reasons:
        if reason and reason not in unique:
            unique.append(reason)
    return unique


def _evidence_line(step: "LineageStep", *, max_chars: int) -> str:
    label = step.title
    summary = _natural_summary(step.summary)
    facts = _evidence_facts(step)

    if facts:
        compact_facts = {
            key: value for key, value in facts.items() if not _is_missing(value)
        }
        if compact_facts:
            return f"{label}: {_short(summary, max_chars=280)} | {_safe_json(compact_facts, max_chars=max_chars)}"
    return f"{label}: {_short(summary, max_chars=360)}"


def _lineage_path_summary(step: "LineageStep") -> str:
    """Render one public route step without losing execution identity."""

    if step.kind == "execution":
        agent = str(step.evidence.get("agent") or step.title)
        role = "System" if step.evidence.get("depth") == 0 else "Agent"
        return f"{role}: {agent} ({step.source})"
    summary = _natural_summary(step.summary)
    if step.kind == "tool":
        return f"{step.title} — {summary}"
    return f"{step.title} — {summary}" if step.title else summary


def _tool_output_facts(output: dict[str, Any], *, max_rows: int = 3) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    if not isinstance(output, dict):
        return {"value": output}

    for key in (
        "ok",
        "route",
        "query_id",
        "summary",
        "text",
        "message",
        "load_date",
        "resolved_load_date",
        "sql",
        "n_rows",
        "row_count",
    ):
        if key in output:
            facts[key] = output[key]

    rows = output.get("rows")
    if isinstance(rows, list):
        facts["row_count"] = (
            output.get("row_count") or output.get("n_rows") or len(rows)
        )
        facts["sample_rows"] = rows[:max_rows]
    elif isinstance(output.get("data"), dict) and isinstance(
        output["data"].get("rows"), list
    ):
        rows = output["data"]["rows"]
        facts["row_count"] = (
            output["data"].get("row_count") or output["data"].get("n_rows") or len(rows)
        )
        facts["sample_rows"] = rows[:max_rows]

    return facts


def _business_tool_evidence_from_payload(*payloads: Any) -> dict[str, Any]:
    """Extract declarative tool evidence from portable business outputs.

    Some integrations intentionally return a portable ``RunResult`` without
    low-level ``tool_events`` because the external framework owns the loop.
    When the final/data payload still records business evidence such as
    ``tool``, ``route``, ``query``, ``sql`` or ``rows``, Lineage Memory should
    explain that evidence instead of saying that no executable step exists.
    """

    merged: dict[str, Any] = {}
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        merged.update(
            {
                key: value
                for key, value in payload.items()
                if value not in (None, "", [], {})
            }
        )

    if not merged:
        return {}

    tool_name = merged.get("tool") or merged.get("tool_name") or merged.get("name")
    route = merged.get("route")
    query = merged.get("query") if isinstance(merged.get("query"), dict) else {}
    query_id = merged.get("query_id") or query.get("query_id")
    sql = merged.get("sql")
    rows = merged.get("rows") if isinstance(merged.get("rows"), list) else None
    table = merged.get("table") if isinstance(merged.get("table"), dict) else {}
    if rows is None and isinstance(table.get("rows"), list):
        rows = table.get("rows")
    sections = (
        merged.get("sections") if isinstance(merged.get("sections"), list) else []
    )
    if not sql:
        for section in sections:
            if (
                isinstance(section, dict)
                and section.get("kind") == "sql"
                and section.get("content")
            ):
                sql = section.get("content")
                break
    if rows is None:
        for section in sections:
            if (
                isinstance(section, dict)
                and section.get("kind") == "table"
                and isinstance(section.get("rows"), list)
            ):
                rows = section.get("rows")
                break

    has_evidence = any([tool_name, route, query_id, sql, rows])
    if not has_evidence:
        return {}

    summary = merged.get("summary") or merged.get("text") or merged.get("message")
    if not summary:
        pieces = []
        if tool_name:
            pieces.append(f"tool={tool_name}")
        if route:
            pieces.append(f"route={route}")
        if query_id:
            pieces.append(f"query_id={query_id}")
        if rows is not None:
            pieces.append(f"rows={len(rows)}")
        summary = "Portable business output recorded " + ", ".join(pieces) + "."

    return {
        "tool": tool_name or "portable_output",
        "route": route,
        "query_id": query_id,
        "summary": summary,
        "sql": sql,
        "row_count": len(rows)
        if isinstance(rows, list)
        else merged.get("row_count") or merged.get("n_rows"),
        "sample_rows": rows[:3] if isinstance(rows, list) else [],
        "query": query,
    }


class LineageStep(BaseModel):
    """One compact explanation/evidence step."""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    kind: LineageKind
    title: str
    summary: str
    source: str = ""
    why: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("step_id", "title")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        clean = str(value or "").strip()
        if not clean:
            raise ValueError("LineageStep requires non-empty step_id and title")
        return clean

    def compact(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        return {
            key: value
            for key, value in payload.items()
            if value not in (None, "", {}, [])
        }


def _execution_lineage_step(node: Any, *, index: int, depth: int) -> LineageStep:
    normalized = node.normalized()
    runtime = normalized.get("runtime") or {}
    answer = normalized.get("answer") or {}
    text = str(answer.get("text") or getattr(node, "text", "") or "").strip()
    agent_name = str(
        getattr(node, "meta", {}).get("agent_name")
        or getattr(node, "meta", {}).get("system")
        or ("system-entrypoint" if depth == 0 else "delegated-agent")
    )
    provider = str(runtime.get("provider") or getattr(node, "engine", ""))
    framework = str(runtime.get("framework") or "agentic-systems")
    return LineageStep(
        step_id=f"execution_{index}",
        kind="execution",
        title=(
            "System entrypoint" if depth == 0 else f"Delegated execution: {agent_name}"
        ),
        summary=_short(text, max_chars=360)
        or (
            "Execution succeeded."
            if getattr(node, "ok", False)
            else "Execution failed."
        ),
        source=f"{provider} x {framework}",
        why="Este nivel conserva identidad, relación padre/hijo y evidencia pública.",
        evidence={
            "execution_id": getattr(node, "execution_id", None),
            "parent_execution_id": getattr(node, "parent_execution_id", None),
            "depth": depth,
            "agent": agent_name,
            "runtime": runtime,
            "input": normalized.get("input"),
            "answer": answer,
            "usage": normalized.get("usage") or {},
            "ok": bool(getattr(node, "ok", True)),
        },
    )


def _tool_lineage_step(event: Any, *, step_id: str, max_tool_rows: int) -> LineageStep:
    event_dict = (
        event.model_dump(mode="json") if hasattr(event, "model_dump") else dict(event)
    )
    output = event_dict.get("output") or {}
    facts = _tool_output_facts(output, max_rows=max_tool_rows)
    summary = facts.get("summary") or facts.get("message") or facts.get("text")
    if not summary:
        route = facts.get("route") or facts.get("query_id") or "tool call"
        row_count = facts.get("row_count")
        summary = f"{event_dict.get('name')} executed via {route}"
        if row_count is not None:
            summary += f" and returned {row_count} row(s)"
        summary += "."
    return LineageStep(
        step_id=step_id,
        kind="tool",
        title=f"Tool: {event_dict.get('name')}",
        summary=_short(summary, max_chars=360),
        source=event_dict.get("name") or "tool",
        why="La tool dejó salida estructurada para soportar la respuesta.",
        evidence={
            "input": event_dict.get("input") or {},
            "ok": event_dict.get("ok"),
            "facts": facts,
        },
    )


class LineageMemory(BaseModel):
    """Compact, reusable memory for one result lineage.

    It is designed for notebooks, eval/debug payloads and prompt context.  The
    object is deliberately JSON-friendly and independent of any tracing vendor.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = LINEAGE_SCHEMA_VERSION
    name: str = "run"
    question: str = ""
    goal: str = ""
    answer: str = ""
    ok: bool = True
    steps: list[LineageStep] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_run_result(
        cls,
        result: Any,
        *,
        name: str = "run",
        question: str | None = None,
        goal: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        max_tool_rows: int = 3,
    ) -> "LineageMemory":
        """Build compact lineage from a ``RunResult``-like object."""

        if not hasattr(result, "normalized"):
            raise TypeError(
                "LineageMemory.from_run_result expects a RunResult-like object with normalized()."
            )

        normalized = result.normalized()
        runtime = normalized.get("runtime") or {}
        input_payload = normalized.get("input")
        answer_payload = normalized.get("answer") or {}
        final_payload = (
            answer_payload.get("final") or getattr(result, "final", {}) or {}
        )
        text_answer = str(
            answer_payload.get("text") or getattr(result, "text", "") or ""
        ).strip()
        if not text_answer and isinstance(final_payload, dict):
            text_answer = str(
                final_payload.get("summary")
                or final_payload.get("text")
                or final_payload.get("answer")
                or final_payload.get("message")
                or ""
            ).strip()
        if not text_answer:
            text_answer = _safe_json(final_payload, max_chars=320)

        resolved_question = (
            question
            if question is not None
            else _safe_json(input_payload, max_chars=320)
        )
        steps: list[LineageStep] = [
            LineageStep(
                step_id="input",
                kind="input",
                title="Input received",
                summary=_short(resolved_question, max_chars=280)
                or "No input recorded.",
                source="RunResult.meta.input",
                why="Esta es la entrada que inició la ejecución.",
                evidence={"input": input_payload},
            )
        ]

        hierarchy: list[tuple[Any, int]] = []

        def visit(node: Any, depth: int) -> None:
            hierarchy.append((node, depth))
            for child in list(getattr(node, "children", []) or []):
                visit(child, depth + 1)

        root_children = list(getattr(result, "children", []) or [])
        root_tools = list(getattr(result, "tool_events", []) or [])
        root_meta = getattr(result, "meta", {}) or {}
        has_execution_evidence = bool(
            root_children
            or root_tools
            or root_meta.get("agent_name")
            or root_meta.get("system")
        )
        if has_execution_evidence:
            visit(result, 0)
        tools: list[Any] = []
        for node_index, (node, depth) in enumerate(hierarchy, start=1):
            steps.append(_execution_lineage_step(node, index=node_index, depth=depth))
            children = list(getattr(node, "children", []) or [])
            node_tools = (
                []
                if depth == 0 and children
                else list(getattr(node, "tool_events", []) or [])
            )
            tools.extend(node_tools)
            for tool_index, event in enumerate(node_tools, start=1):
                steps.append(
                    _tool_lineage_step(
                        event,
                        step_id=f"execution_{node_index}_tool_{tool_index}",
                        max_tool_rows=max_tool_rows,
                    )
                )

        if not tools:
            business_evidence = _business_tool_evidence_from_payload(
                final_payload, getattr(result, "data", {}) or {}
            )
            if business_evidence:
                tool_name = business_evidence.get("tool") or "portable_output"
                route = (
                    business_evidence.get("route")
                    or business_evidence.get("query_id")
                    or "portable output"
                )
                row_count = business_evidence.get("row_count")
                summary = str(
                    business_evidence.get("summary")
                    or f"{tool_name} produced portable business evidence via {route}."
                )
                if row_count is not None and "row" not in summary.lower():
                    summary = f"{summary.rstrip('.')} ({row_count} row(s))."
                steps.append(
                    LineageStep(
                        step_id="portable_tool_evidence",
                        kind="tool",
                        title=f"Tool evidence: {tool_name}",
                        summary=_short(summary, max_chars=420),
                        source=str(tool_name),
                        why="El output portable conserva qué tool o ruta produjo la evidencia.",
                        evidence={"facts": business_evidence},
                    )
                )

        validation = getattr(result, "validation", None)
        if validation:
            ok = (
                bool(validation.get("ok", True))
                if isinstance(validation, dict)
                else True
            )
            steps.append(
                LineageStep(
                    step_id="validation",
                    kind="validation",
                    title="Contract validation",
                    summary="Contract validation passed."
                    if ok
                    else "Contract validation reported issues.",
                    source="RunResult.validation",
                    why="El contrato o policy deja explícito qué se esperaba de la ejecución.",
                    evidence=validation
                    if isinstance(validation, dict)
                    else {"validation": validation},
                )
            )

        errors = list(getattr(result, "errors", []) or [])
        for index, error in enumerate(errors, start=1):
            steps.append(
                LineageStep(
                    step_id=f"error_{index}",
                    kind="error",
                    title="Error recorded",
                    summary=_short(
                        error.get("message") or error.get("code") or error,
                        max_chars=260,
                    )
                    if isinstance(error, dict)
                    else _short(error, max_chars=260),
                    source="RunResult.errors",
                    why="Los errores se conservan para no ocultar evidencia fallida en explicaciones posteriores.",
                    evidence=error if isinstance(error, dict) else {"error": error},
                )
            )

        steps.append(
            LineageStep(
                step_id="answer",
                kind="answer",
                title="Final answer",
                summary=_short(text_answer, max_chars=420) or "No final text recorded.",
                source="RunResult.final",
                why="Esta es la respuesta final derivada de la evidencia de la ejecución.",
                evidence={
                    "final": final_payload,
                    "data": answer_payload.get("data") or getattr(result, "data", {}),
                },
            )
        )

        metadata_payload = {
            "runtime": runtime,
            "tool_event_count": len(tools),
            "message_count": len(getattr(result, "messages", []) or []),
            **(metadata or {}),
        }
        return cls(
            name=name,
            question=str(resolved_question or ""),
            goal=goal,
            answer=text_answer,
            ok=bool(getattr(result, "ok", True)),
            steps=steps,
            usage=dict(getattr(result, "usage", {}) or {}),
            validation=validation if isinstance(validation, dict) else None,
            tags=list(tags or []),
            metadata=metadata_payload,
        )

    @classmethod
    def from_result(cls, result: Any, **kwargs: Any) -> "LineageMemory":
        """Alias for notebooks that read better as ``from_result``."""

        return cls.from_run_result(result, **kwargs)

    def compact(self, *, max_steps: int | None = None) -> dict[str, Any]:
        steps = self.steps if max_steps is None else self.steps[:max_steps]
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "ok": self.ok,
            "question": self.question,
            "goal": self.goal,
            "answer": self.answer,
            "steps": [step.compact() for step in steps],
            "usage": self.usage,
            "validation": self.validation,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }

    def explain(self) -> dict[str, Any]:
        """Return a notebook-friendly what/how/support explanation.

        The explanation is intentionally runtime-agnostic. Direct tools, Bedrock
        runs, graph nodes and external agent-loop events all become steps, so
        notebooks can explain simple runs and orchestrated systems with the same
        API. The public keys keep backward compatibility with 2.4.5, while the
        human renderer uses the clearer "support" wording introduced in 2.4.9.2.
        """

        tool_steps = [step for step in self.steps if step.kind == "tool"]
        path_steps = []
        for step in self.steps:
            if step.kind not in {"execution", "decision", "tool", "context"}:
                continue
            # Graph-node wrapper summaries are useful evidence, but noisy in the
            # human route when concrete tool steps are available. Keep route
            # focused on the actual plan/tools executed.
            if (
                tool_steps
                and step.kind == "decision"
                and step.title.startswith("Graph node:")
            ):
                continue
            path_steps.append(step)
        evidence_steps = [
            step
            for step in self.steps
            if step.kind in {"decision", "tool", "validation"}
        ]
        error_steps = [step for step in self.steps if step.kind == "error"]
        fallback_steps = [step for step in self.steps if step.kind == "validation"]
        support_reasons = _derive_support_reasons(self.steps, ok=self.ok)
        how_items = [_lineage_path_summary(step) for step in path_steps]
        how_items = [item for item in how_items if item]
        return {
            "what_happened": self.answer or "The run produced no final answer text.",
            "how_it_happened": how_items
            or [_natural_summary(step.summary) for step in fallback_steps]
            or ["No executable step was recorded."],
            "why_this_answer": support_reasons,
            "support": support_reasons,
            "validation": self.validation,
            "risks_or_gaps": [_natural_summary(step.summary) for step in error_steps]
            or [],
            "evidence": [step.compact() for step in evidence_steps],
        }

    def human_text(
        self,
        *,
        include_evidence: bool = True,
        max_evidence_chars: int = 520,
        max_how_items: int = 6,
        max_evidence_items: int = 5,
        render_mode: Literal["compact", "audit", "debug"] = "audit",
    ) -> str:
        """Return a clear Spanish notebook view of the lineage.

        ``to_prompt_context`` remains the compact/token-saving representation.
        ``human_text`` is the explanation view for ``lab.show(memory)`` and
        ``lab.human_result(..., show_lineage=True)``. The 2.4.9.2 renderer avoids
        canned "trust me" prose: support bullets are derived from structured
        evidence such as tool outputs, graph decisions, validations and errors.

        Render modes:
        - ``compact``: shortest demo view.
        - ``audit``: default notebook view with route, support and evidence.
        - ``debug``: audit view plus compact raw lineage payload.
        """

        explanation = self.explain()
        answer = _short(explanation["what_happened"], max_chars=520)
        how_items = list(explanation.get("how_it_happened") or [])
        support_items = list(
            explanation.get("support") or explanation.get("why_this_answer") or []
        )
        risks = list(explanation.get("risks_or_gaps") or [])

        lines: list[str] = [
            f"Lineage Memory · {self.name}",
            f"Estado: {'OK' if self.ok else 'REVISAR'}",
        ]
        if self.question:
            lines.append(f"Pregunta: {_short(self.question, max_chars=280)}")
        if self.goal:
            lines.append(f"Objetivo: {_short(self.goal, max_chars=260)}")

        if render_mode == "compact":
            lines.extend(["", "Respuesta:", f"- {answer}"])
            if how_items:
                route = " → ".join(_short(item, max_chars=80) for item in how_items[:3])
                if len(how_items) > 3:
                    route += f" → +{len(how_items) - 3} paso(s)"
                lines.extend(["", "Ruta:", f"- {route}"])
            if support_items:
                lines.extend(
                    [
                        "",
                        "Soporte:",
                        f"- {' · '.join(_short(item, max_chars=90) for item in support_items[:3])}",
                    ]
                )
            return "\n".join(lines)

        lines.extend(["", "Respuesta:", f"- {answer}"])

        lines.extend(["", "Ruta ejecutada:"])
        if how_items:
            for index, item in enumerate(how_items[:max_how_items], start=1):
                lines.append(
                    f"{index}. {_short(_natural_summary(item), max_chars=360)}"
                )
            remaining_how = len(how_items) - max_how_items
            if remaining_how > 0:
                lines.append(f"- … {remaining_how} paso(s) más en el lineage completo.")
        else:
            lines.append("- No se registraron pasos ejecutables.")

        lines.extend(["", "Soporte de la respuesta:"])
        seen: set[str] = set()
        for item in support_items:
            clean = _short(_natural_summary(item), max_chars=360)
            if clean and clean not in seen:
                lines.append(f"- {clean}")
                seen.add(clean)

        if risks:
            lines.extend(["", "Riesgos o huecos:"])
            for item in risks[:max_evidence_items]:
                lines.append(f"- {_short(_natural_summary(item), max_chars=360)}")
            remaining_risks = len(risks) - max_evidence_items
            if remaining_risks > 0:
                lines.append(f"- … {remaining_risks} riesgo(s) más.")

        if include_evidence:
            evidence_steps = [
                step
                for step in self.steps
                if step.kind in {"decision", "tool", "validation", "answer"}
            ]
            if evidence_steps:
                lines.extend(["", "Evidencia:"])
                for step in evidence_steps[:max_evidence_items]:
                    lines.append(
                        f"- {_evidence_line(step, max_chars=max_evidence_chars)}"
                    )
                remaining_evidence = len(evidence_steps) - max_evidence_items
                if remaining_evidence > 0:
                    lines.append(
                        f"- … {remaining_evidence} evidencia(s) más disponibles en `lineage.steps`."
                    )

        if render_mode == "debug":
            lines.extend(
                [
                    "",
                    "Debug lineage payload:",
                    _safe_json(self.compact(), max_chars=max_evidence_chars * 4),
                ]
            )

        return "\n".join(lines)

    def to_prompt_context(self, *, max_chars: int = 1600) -> str:
        """Return compact text context for a follow-up prompt.

        This is the token-saving use case: pass the distilled lineage instead of
        the full raw trace, SQL payloads, message history and raw responses.
        """

        lines = [
            f"LineageMemory: {self.name}",
            f"ok: {self.ok}",
            f"question: {_short(self.question, max_chars=260)}",
            f"goal: {_short(self.goal, max_chars=220)}" if self.goal else "",
            f"answer: {_short(self.answer, max_chars=320)}",
        ]
        for step in self.steps:
            evidence = (
                step.evidence.get("facts") if isinstance(step.evidence, dict) else None
            )
            evidence_text = (
                f" | evidence={_safe_json(evidence, max_chars=220)}" if evidence else ""
            )
            lines.append(
                f"- {step.kind}:{step.title}: {_short(step.summary, max_chars=240)}{evidence_text}"
            )
        text = "\n".join(line for line in lines if line)
        if len(text) <= max_chars:
            return text
        return text[: max(0, max_chars - 3)] + "..."

    def estimated_context_savings(
        self, raw: Any, *, max_chars: int = 1600
    ) -> dict[str, Any]:
        """Compare raw payload size against compact lineage context.

        This is only a character-based estimate; it intentionally avoids a hard
        tokenizer dependency.
        """

        raw_text = _safe_json(raw, max_chars=200_000)
        compact_text = self.to_prompt_context(max_chars=max_chars)
        raw_chars = len(raw_text)
        compact_chars = len(compact_text)
        saved_chars = max(0, raw_chars - compact_chars)
        ratio = (saved_chars / raw_chars) if raw_chars else 0.0
        return {
            "raw_chars": raw_chars,
            "compact_chars": compact_chars,
            "saved_chars": saved_chars,
            "estimated_savings_ratio": round(ratio, 4),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def lineage_memory(result: Any, **kwargs: Any) -> LineageMemory:
    """Functional helper for ``LineageMemory.from_run_result``."""

    return LineageMemory.from_run_result(result, **kwargs)
