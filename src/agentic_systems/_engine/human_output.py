"""Plain-text, framework-agnostic output helpers for notebooks."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from .contracts import ToolExpectationValue, normalize_tool_expectation, validate_tool_expectation

RUN_SCHEMA_FALLBACK = "agentic_systems.run.v1"


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _as_dict(result: Any) -> dict[str, Any]:
    value = _jsonable(result)
    return value if isinstance(value, dict) else {"value": value}


def _compact(value: Any, max_chars: int = 400) -> str:
    try:
        text = json.dumps(_jsonable(value), ensure_ascii=False, default=str)
    except TypeError:
        text = str(value)
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def _one_line(value: Any, max_chars: int = 120) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def _event_payload(event: dict[str, Any]) -> dict[str, Any]:
    output = event.get("output") or {}
    if isinstance(output, dict) and isinstance(output.get("data"), dict):
        return output["data"]
    return output if isinstance(output, dict) else {"value": output}


def _payload_brief(payload: dict[str, Any]) -> str:
    important = {key: payload[key] for key in ("operation", "result", "text") if key in payload}
    if important:
        return _compact(important)
    if payload:
        return _compact(payload)
    return ""


def _is_normalized_run_schema(value: dict[str, Any]) -> bool:
    """Return True when ``value`` is already Agentic Systems's public run schema.

    LangGraph nodes often keep ``RunResult.normalized()`` inside graph state.
    Treating that payload as a raw result loses tool events, SQL and table
    previews. This check keeps serialized RunResults first-class across agents,
    graphs, notebooks and tests without depending on a business-specific key.
    """

    if value.get("schema_version") == RUN_SCHEMA_FALLBACK:
        return True
    return all(key in value for key in ("runtime", "answer", "tools"))


def _normalized(result: Any) -> dict[str, Any]:
    if hasattr(result, "normalized"):
        return result.normalized()
    result_dict = _as_dict(result)
    if _is_normalized_run_schema(result_dict):
        return result_dict
    normalized = result_dict.get("normalized")
    if isinstance(normalized, dict):
        return normalized
    compact = result_dict.get("compact")
    if isinstance(compact, dict) and isinstance(compact.get("normalized"), dict):
        return compact["normalized"]
    return _fallback_normalized(result_dict)


def _fallback_normalized(result_dict: dict[str, Any]) -> dict[str, Any]:
    events = result_dict.get("tool_events") or []
    meta = result_dict.get("meta") or {}
    return {
        "schema_version": RUN_SCHEMA_FALLBACK,
        "ok": bool(result_dict.get("ok", result_dict.get("run_ok", False))),
        "runtime": {
            "provider": result_dict.get("provider") or result_dict.get("engine"),
            "engine": result_dict.get("engine"),
            "runtime_engine": meta.get("runtime_engine", result_dict.get("engine")),
            "model": result_dict.get("model"),
            "mode": result_dict.get("mode"),
            "framework": meta.get("framework") or result_dict.get("framework"),
        },
        "input": meta.get("input") or result_dict.get("input") or result_dict.get("prompt"),
        "answer": {
            "text": result_dict.get("text") or "",
            "final": result_dict.get("final") or result_dict.get("data") or {},
            "data": result_dict.get("data") or {},
        },
        "final": result_dict.get("final") or result_dict.get("data") or {},
        "tools": [_normalize_event(_as_dict(event)) for event in events],
        "usage": result_dict.get("usage") or {},
        "validation": result_dict.get("validation"),
        "errors": result_dict.get("errors") or [],
    }


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = _event_payload(event)
    table = payload.get("table") if isinstance(payload.get("table"), dict) else {}
    query = payload.get("query") if isinstance(payload.get("query"), dict) else {}
    return {
        "name": event.get("name") or payload.get("tool") or "tool",
        "ok": bool(event.get("ok")),
        "input": event.get("input") or {},
        "output": payload,
        "summary": payload.get("summary") or payload.get("error") or payload.get("text") or _payload_brief(payload),
        "sql": payload.get("sql"),
        "rows": table.get("rows") or [],
        "row_count": table.get("n_rows"),
        "route": payload.get("route"),
        "query_id": query.get("query_id") or payload.get("query_id"),
        "error": event.get("error") or payload.get("error"),
    }


def _format_rows(rows: list[dict[str, Any]], *, max_rows: int = 5, max_cell: int = 32) -> str:
    if not rows:
        return ""
    columns = list(rows[0].keys())
    shown = rows[:max_rows]
    widths: dict[str, int] = {}
    for column in columns:
        values = [_one_line(row.get(column), max_cell) for row in shown]
        widths[column] = min(max(len(column), *(len(value) for value in values)), max_cell)

    header = " | ".join(column[: widths[column]].ljust(widths[column]) for column in columns)
    rule = "-+-".join("-" * widths[column] for column in columns)
    body = [
        " | ".join(_one_line(row.get(column), max_cell).ljust(widths[column]) for column in columns)
        for row in shown
    ]
    extra = "" if len(rows) <= max_rows else f"\n  … {len(rows) - max_rows} fila(s) más"
    return "  " + header + "\n  " + rule + "\n  " + "\n  ".join(body) + extra


def _print_header(title: str) -> None:
    print("=" * 88)
    print(title)
    print("=" * 88)


def _print_block(number: int, title: str) -> None:
    print(f"\n{number}) {title}")
    print("-" * 88)


def _format_usage(usage: dict[str, Any]) -> str:
    if not usage:
        return "no disponible"
    parts = []
    for key in ("requests", "input_tokens", "output_tokens", "total_tokens", "client_duration_ms", "service_latency_ms"):
        value = usage.get(key)
        if value is not None:
            parts.append(f"{key}={value}")
    return " | ".join(parts) if parts else "no disponible"


def _print_payload(
    payload: dict[str, Any],
    *,
    indent: str = "",
    include_summary: bool = True,
    include_sql: bool = False,
    include_table: bool = False,
) -> None:
    if include_summary and payload.get("summary"):
        print(f"{indent}Resultado: {payload['summary']}")
    elif include_summary and payload.get("error"):
        print(f"{indent}Error: {payload['error']}")
    elif include_summary and payload:
        important = {key: payload[key] for key in ("operation", "result", "text") if key in payload}
        print(f"{indent}Resultado: {_compact(important or payload)}")

    if include_sql and payload.get("sql"):
        print(f"{indent}SQL:")
        for line in str(payload["sql"]).splitlines():
            print(f"{indent}  {line}")

    table = payload.get("table") if isinstance(payload, dict) else None
    rows = table.get("rows") if isinstance(table, dict) else None
    if include_table and rows:
        print(f"{indent}Filas devueltas: {table.get('n_rows', len(rows))}")
        print(_format_rows(rows))


def _print_input(prompt: Any) -> None:
    if prompt is None or prompt == "":
        print("(sin entrada registrada)")
    elif isinstance(prompt, str):
        print(prompt)
    else:
        print(_compact(prompt, max_chars=1200))


_TEXT_FINAL_KEYS = ("final_output", "output", "answer", "response", "text", "summary")


def _human_text_from_mapping(payload: dict[str, Any]) -> str | None:
    """Return the user-facing text from a structured final-answer payload.

    This stays provider/framework agnostic: many runtimes normalize a final
    answer as ``{"final_output": "..."}``, ``{"answer": "..."}`` or
    ``{"summary": "..."}``. For human output, that single textual answer is
    clearer than printing the JSON wrapper with escaped newlines.
    """

    for key in _TEXT_FINAL_KEYS:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        # ``final_output`` is the explicit normalized final-answer text channel.
        # Other generic names such as ``answer`` may coexist with scores,
        # citations or debug fields; keep those as JSON unless the textual field
        # is the whole payload. ``summary`` preserves its historical short-payload
        # behavior.
        if key == "final_output":
            return value.strip()
        # Delegated Agent/System executions retain structured public evidence in
        # final while exposing one explicit human answer. The execution marker
        # distinguishes this envelope from arbitrary structured output, so the
        # reusable evidence remains available in normalized JSON.
        if key in {"answer", "text"} and "execution" in payload:
            return value.strip()
        if key == "answer" and set(payload).issubset(
            {"answer", "text", "unsupported_request", "ok", "tool"}
        ):
            return value.strip()
        if key == "summary" and len(payload) <= 3:
            return value.strip()
        if len(payload) == 1:
            return value.strip()
    return None


def _print_answer(answer: dict[str, Any]) -> None:
    final = answer.get("final") if isinstance(answer.get("final"), dict) else {}
    text = str(answer.get("text") or "").strip()
    data = answer.get("data") if isinstance(answer.get("data"), dict) else {}

    # The final-answer dictionary is the user-facing payload.  Prefer it over
    # raw text/data so requested fields are shown first.  Preserve the old text
    # fallback for pure language-model answers that have no structured payload.
    if final:
        final_text = _human_text_from_mapping(final)
        if final_text:
            print(final_text)
        elif final.get("error") and len(final) <= 3:
            print(final["error"])
        else:
            print(_compact(final, max_chars=1600))
        return
    if text:
        print(text)
        return
    if data.get("summary") or data.get("error"):
        print(data.get("summary") or data.get("error"))
        return
    if data:
        print(_compact(data, max_chars=1200))
        return
    print("(sin respuesta final registrada)")




def _answer_final(answer: dict[str, Any]) -> dict[str, Any]:
    final = answer.get("final") if isinstance(answer.get("final"), dict) else {}
    return final


def _iter_final_sections(answer: dict[str, Any], kind: str | None = None) -> list[dict[str, Any]]:
    final = _answer_final(answer)
    sections = final.get("sections")
    if not isinstance(sections, list):
        return []
    selected: list[dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_kind = str(section.get("kind") or "").lower()
        if kind is None or section_kind == kind:
            selected.append(section)
    return selected


def _sql_blocks(answer: dict[str, Any], tools: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return SQL blocks explicitly declared by final answer or tool outputs.

    The default human renderer must stay domain-agnostic. It does not invent a
    SQL block for non-SQL use cases; it only renders SQL when the final answer
    or a tool event actually carries SQL.
    """

    blocks: list[dict[str, str]] = []
    for section in _iter_final_sections(answer, "sql"):
        content = section.get("content") or section.get("sql") or section.get("value")
        if content:
            blocks.append({"title": str(section.get("title") or "SQL ejecutado"), "content": str(content)})
    for index, tool in enumerate(tools, start=1):
        sql = tool.get("sql")
        if sql:
            blocks.append({"title": f"SQL ejecutado · {_tool_label(tool, index)}", "content": str(sql)})
    return blocks


def _table_blocks(answer: dict[str, Any], tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return table/row blocks explicitly declared by final answer or tools."""

    blocks: list[dict[str, Any]] = []
    final = _answer_final(answer)
    rows = final.get("rows")
    if isinstance(rows, list) and rows and all(isinstance(row, dict) for row in rows):
        blocks.append({"title": str(final.get("table_title") or "Respuesta final"), "rows": rows})
    for section in _iter_final_sections(answer, "table"):
        section_rows = section.get("rows")
        if isinstance(section_rows, list) and section_rows and all(isinstance(row, dict) for row in section_rows):
            blocks.append({"title": str(section.get("title") or "Tabla"), "rows": section_rows})
    for index, tool in enumerate(tools, start=1):
        tool_rows = tool.get("rows") or []
        if tool_rows:
            blocks.append({"title": f"Preview de datos · {_tool_label(tool, index)}", "rows": tool_rows})
    return blocks


def _should_print_validation(tools: list[dict[str, Any]], expected_tools: ToolExpectationValue, validation: Any) -> bool:
    if expected_tools is not None:
        return True
    if any(not tool.get("ok") for tool in tools):
        return True
    if not validation:
        return False
    if isinstance(validation, dict):
        validation_keys = set(validation)
        # Environment/eval objects already surface passed/failed counts in the
        # answer and Lineage Memory blocks. Avoid a noisy generic validation
        # table that says "Regla esperada: unspecified".
        aggregate_only = validation_keys <= {"ok", "passed", "failed", "passed_steps", "failed_steps"}
        if aggregate_only:
            return False
    return True


def _print_sql_blocks(blocks: list[dict[str, str]]) -> None:
    for block in blocks:
        print(f"{block['title']}:")
        for line in str(block["content"]).splitlines():
            print(f"  {line}")
        print()


def _print_table_blocks(blocks: list[dict[str, Any]]) -> None:
    for block in blocks:
        print(f"{block['title']}:")
        print(_format_rows(block.get("rows") or []))
        print()

def _tool_label(tool: dict[str, Any], index: int) -> str:
    name = tool.get("name") or f"tool_{index}"
    bits = []
    if tool.get("route"):
        bits.append(f"route={tool['route']}")
    if tool.get("query_id"):
        bits.append(f"query_id={tool['query_id']}")
    if tool.get("row_count") is not None:
        bits.append(f"rows={tool['row_count']}")
    suffix = f" ({', '.join(bits)})" if bits else ""
    return f"{name}{suffix}"


def _print_actions(tools: list[dict[str, Any]]) -> None:
    print("Tools ejecutadas:")
    if not tools:
        print("(no se ejecutaron tools)")
        return
    for index, tool in enumerate(tools, start=1):
        status = "OK" if tool.get("ok") else "ERROR"
        print(f"{index}. {_tool_label(tool, index)} — {status}")
        if tool.get("input"):
            print(f"   input: {_compact(tool['input'], max_chars=500)}")
        if tool.get("summary"):
            print(f"   resultado: {tool['summary']}")
        elif tool.get("error"):
            print(f"   error: {tool['error']}")



def _runtime_engine(normalized: dict[str, Any]) -> str:
    runtime = normalized.get("runtime") if isinstance(normalized.get("runtime"), dict) else {}
    engine = runtime.get("runtime_engine") or runtime.get("engine") or runtime.get("execution_engine")
    return str(engine) if engine not in (None, "", "n/a") else ""


def _runtime_framework(normalized: dict[str, Any]) -> str:
    runtime = normalized.get("runtime") if isinstance(normalized.get("runtime"), dict) else {}
    framework = runtime.get("framework")
    if framework not in (None, "", "n/a"):
        return str(framework)
    engine = runtime.get("engine") or runtime.get("runtime_engine") or runtime.get("execution_engine")
    if engine:
        return "agentic-systems"
    return ""


def _eval_cases_from_normalized(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    answer = normalized.get("answer") if isinstance(normalized.get("answer"), dict) else {}
    data = answer.get("data") if isinstance(answer.get("data"), dict) else {}
    cases = data.get("cases") if isinstance(data.get("cases"), list) else []
    return [case for case in cases if isinstance(case, dict)]


def _environment_history_from_normalized(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    answer = normalized.get("answer") if isinstance(normalized.get("answer"), dict) else {}
    data = answer.get("data") if isinstance(answer.get("data"), dict) else {}
    history = data.get("history") if isinstance(data.get("history"), list) else []
    return [event for event in history if isinstance(event, dict)]


def _case_result_preview(case: dict[str, Any]) -> str:
    result = case.get("result") if isinstance(case.get("result"), dict) else {}
    answer = result.get("answer") if isinstance(result.get("answer"), dict) else {}
    data = answer.get("data") if isinstance(answer.get("data"), dict) else result.get("data") or {}
    final = answer.get("final") if isinstance(answer.get("final"), dict) else result.get("final") or {}
    for payload in (data, final):
        if not isinstance(payload, dict):
            continue
        pieces = []
        if payload.get("tool") is not None:
            pieces.append(f"tool={payload.get('tool')}")
        if payload.get("value") is not None:
            pieces.append(f"value={payload.get('value')}")
        elif payload.get("result") is not None:
            pieces.append(f"result={payload.get('result')}")
        if payload.get("ok") is not None:
            pieces.append(f"ok={payload.get('ok')}")
        if pieces:
            return ", ".join(pieces)
    return _compact(result, max_chars=180)


def _print_eval_cases(cases: list[dict[str, Any]], *, max_cases: int = 10) -> None:
    print("Casos evaluados:")
    if not cases:
        print("(sin casos evaluados registrados)")
        return
    for index, case in enumerate(cases[:max_cases], start=1):
        status = "OK" if case.get("ok") else "REVISAR"
        print(f"{index}. {case.get('name') or f'case_{index}'} — {status}")
        print(f"   input: {_compact(case.get('input'), max_chars=220)}")
        print(f"   resultado: {_case_result_preview(case)}")
    remaining = len(cases) - max_cases
    if remaining > 0:
        print(f"... {remaining} caso(s) más disponibles en report.cases")


def _print_environment_steps(history: list[dict[str, Any]], *, max_steps: int = 10) -> None:
    print("Pasos del episodio:")
    if not history:
        print("(sin pasos registrados)")
        return
    for index, event in enumerate(history[:max_steps], start=1):
        reward = event.get("reward")
        row = event.get("row")
        graph_state = event.get("graph_state") if isinstance(event.get("graph_state"), dict) else {}
        route = graph_state.get("selected_agent") or graph_state.get("selected_tool") or graph_state.get("route") or graph_state.get("tool")
        route_text = f" route={route};" if route else ""
        print(f"{index}. step={event.get('step_index')};{route_text} reward={reward}")
        print(f"   row: {_compact(row, max_chars=220)}")
    remaining = len(history) - max_steps
    if remaining > 0:
        print(f"... {remaining} paso(s) más disponibles en env.history")


def _plain_print_execution_block(normalized: dict[str, Any], tools: list[dict[str, Any]]) -> None:
    framework = _runtime_framework(normalized)
    if framework == "agentic-eval" and not tools:
        _print_eval_cases(_eval_cases_from_normalized(normalized))
        return
    if framework == "agentic-environment" and not tools:
        _print_environment_steps(_environment_history_from_normalized(normalized))
        return
    _print_actions(tools)


def _print_sql(tools: list[dict[str, Any]]) -> None:
    """Compatibility helper: print SQL carried by tools, without placeholders."""

    _print_sql_blocks(_sql_blocks({}, tools))


def _print_tables(tools: list[dict[str, Any]]) -> None:
    """Compatibility helper: print rows carried by tools, without placeholders."""

    _print_table_blocks(_table_blocks({}, tools))


def _validation_summary(tools: list[dict[str, Any]], expected_tools: ToolExpectationValue, validation: Any) -> dict[str, Any]:
    actual = [str(tool.get("name")) for tool in tools if tool.get("name")]
    failed = [str(tool.get("name")) for tool in tools if not tool.get("ok")]
    expected = normalize_tool_expectation(expected_tools)
    tool_check = validate_tool_expectation(actual, expected) if expected else {
        "ok": True,
        "rule": "unspecified",
        "expectation": {},
        "actual": actual,
        "missing": [],
        "extra": [],
        "issues": [],
    }
    contract_ok = None
    if isinstance(validation, dict) and validation.get("ok") is not None:
        contract_ok = bool(validation.get("ok"))
    ok = bool(tool_check.get("ok", True)) and not failed and (contract_ok is not False)
    return {
        "expectation": expected,
        "rule": tool_check.get("rule", "unspecified"),
        "actual": actual,
        "missing": tool_check.get("missing", []),
        "extra": tool_check.get("extra", []),
        "failed": failed,
        "contract_ok": contract_ok,
        "ok": ok,
        "issues": tool_check.get("issues", []),
    }


def _format_expectation(expectation: dict[str, Any]) -> str:
    if not expectation:
        return "no especificadas"
    non_empty = {key: value for key, value in expectation.items() if value not in (None, [], {}, "")}
    if set(non_empty) == {"all_of"}:
        return ", ".join(non_empty["all_of"])
    if set(non_empty) == {"exactly"}:
        return ", ".join(non_empty["exactly"])
    parts: list[str] = []
    for key in ("exactly", "all_of", "any_of", "allowed"):
        values = expectation.get(key)
        if values:
            parts.append(f"{key}=[{', '.join(values)}]")
    if expectation.get("min_count") is not None:
        parts.append(f"min_count={expectation['min_count']}")
    return " | ".join(parts) if parts else _compact(expectation)


def _print_validation(tools: list[dict[str, Any]], expected_tools: ToolExpectationValue, validation: Any) -> None:
    summary = _validation_summary(tools, expected_tools, validation)
    print(f"Regla esperada: {summary['rule']}")
    print("Tools esperadas: " + _format_expectation(summary["expectation"]))
    print("Tools ejecutadas: " + (", ".join(summary["actual"]) if summary["actual"] else "ninguna"))
    print("Tools faltantes: " + (", ".join(summary["missing"]) if summary["missing"] else "ninguna"))
    print("Tools extra: " + (", ".join(summary["extra"]) if summary["extra"] else "ninguna"))
    print("Errores de tool: " + (", ".join(summary["failed"]) if summary["failed"] else "ninguno"))
    if summary["contract_ok"] is not None:
        print(f"Contrato: {'OK' if summary['contract_ok'] else 'ERROR'}")
    if summary["issues"]:
        print("Issues:")
        for issue in summary["issues"]:
            print(f"- {issue.get('code')}: {issue.get('message')} ({', '.join(issue.get('tools', []) or [])})")
    print(f"Resultado: {'OK' if summary['ok'] else 'REVISAR'}")



def _build_lineage(result: Any, normalized: dict[str, Any], lineage: Any = None, *, title: str = "", goal: str = "") -> Any:
    if lineage is not None:
        return lineage
    try:
        from .lineage import LineageMemory

        if hasattr(result, "lineage") and callable(result.lineage):
            return result.lineage(name=title or "human_result", question=normalized.get("input"), goal=goal)
        return LineageMemory.from_run_result(_RunResultLike(normalized), name=title or "human_result", question=normalized.get("input"), goal=goal)
    except Exception:
        return None


class _RunResultLike:
    """Tiny adapter so serialized normalized results can build LineageMemory."""

    def __init__(self, normalized: dict[str, Any]):
        self._normalized = normalized
        self.ok = bool(normalized.get("ok"))
        answer = normalized.get("answer") if isinstance(normalized.get("answer"), dict) else {}
        self.text = str(answer.get("text") or "")
        self.final = answer.get("final") if isinstance(answer.get("final"), dict) else {}
        self.data = answer.get("data") if isinstance(answer.get("data"), dict) else {}
        self.usage = normalized.get("usage") or {}
        self.validation = normalized.get("validation")
        self.errors = normalized.get("errors") or []
        self.messages = []
        self.tool_events = normalized.get("tools") or []

    def normalized(self) -> dict[str, Any]:
        return self._normalized


def _print_lineage(result: Any, normalized: dict[str, Any], lineage: Any = None, *, title: str = "", goal: str = "") -> None:
    memory = _build_lineage(result, normalized, lineage=lineage, title=title, goal=goal)
    if memory is None:
        print("(Lineage Memory no disponible para este resultado)")
        return
    if hasattr(memory, "human_text") and callable(memory.human_text):
        print(memory.human_text())
    else:
        print(_compact(memory, max_chars=2200))



def _rich_available() -> bool:
    try:
        import rich  # noqa: F401
    except Exception:
        return False
    return True


def _rich_json(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False, indent=2, default=str)


def _rich_print_human_result(
    result: Any,
    *,
    title: str,
    expected_tools: ToolExpectationValue,
    show_lineage: bool = False,
    lineage: Any = None,
    lineage_goal: str = "",
) -> None:
    """Render a human result with Rich when available.

    Rich is optional at runtime. Callers choose it with ``pretty=True``; when
    Rich is unavailable, the public function falls back to the plain renderer.
    """

    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table

    console = Console()
    normalized = _normalized(result)
    runtime = normalized.get("runtime") or {}
    answer = normalized.get("answer") if isinstance(normalized.get("answer"), dict) else {}
    tools = normalized.get("tools") or []

    console.rule(f"[bold]{title}[/bold]")

    console.print(Panel(_compact(normalized.get("input"), max_chars=1600), title="1) Entrada del usuario", expand=False))

    runtime_table = Table(title="2) Runtime y usage", show_lines=False)
    runtime_table.add_column("Campo", style="bold")
    runtime_table.add_column("Valor")
    runtime_table.add_row("Estado", "OK" if normalized.get("ok") else "ERROR")
    runtime_table.add_row("Provider", _runtime_engine(normalized) or "n/a")
    runtime_table.add_row("Framework", _runtime_framework(normalized) or "agentic-systems")
    runtime_table.add_row("Mode", str(runtime.get("mode") or "n/a"))
    if runtime.get("model"):
        runtime_table.add_row("Model", str(runtime.get("model")))
    runtime_table.add_row("Usage", _format_usage(normalized.get("usage") or {}))
    console.print(runtime_table)

    answer_text = str(answer.get("text") or "").strip()
    answer_final = answer.get("final") if isinstance(answer.get("final"), dict) else {}
    answer_data = answer.get("data") if isinstance(answer.get("data"), dict) else {}
    if answer_final:
        final_text = _human_text_from_mapping(answer_final)
        if final_text:
            answer_body = final_text
        else:
            answer_body = _rich_json(answer_final)
    elif answer_text:
        answer_body = answer_text
    elif answer_data:
        answer_body = answer_data.get("summary") or answer_data.get("error") or _compact(answer_data, max_chars=1600)
    else:
        answer_body = "(sin respuesta final registrada)"
    console.print(Panel(answer_body, title="3) Respuesta final", expand=False))

    framework = _runtime_framework(normalized)
    if framework == "agentic-eval" and not tools:
        cases = _eval_cases_from_normalized(normalized)
        actions_table = Table(title="4) Casos evaluados", show_lines=True)
        actions_table.add_column("#", justify="right")
        actions_table.add_column("Caso")
        actions_table.add_column("Estado")
        actions_table.add_column("Input")
        actions_table.add_column("Resultado")
        if cases:
            for index, case in enumerate(cases[:10], start=1):
                actions_table.add_row(
                    str(index),
                    str(case.get("name") or f"case_{index}"),
                    "OK" if case.get("ok") else "REVISAR",
                    _compact(case.get("input"), max_chars=220),
                    _case_result_preview(case),
                )
            remaining = len(cases) - 10
            if remaining > 0:
                actions_table.add_row("…", f"{remaining} caso(s) más", "", "", "report.cases")
        else:
            actions_table.add_row("-", "(sin casos evaluados registrados)", "-", "-", "-")
        console.print(actions_table)
    elif framework == "agentic-environment" and not tools:
        history = _environment_history_from_normalized(normalized)
        actions_table = Table(title="4) Pasos del episodio", show_lines=True)
        actions_table.add_column("#", justify="right")
        actions_table.add_column("Step")
        actions_table.add_column("Reward")
        actions_table.add_column("Ruta")
        actions_table.add_column("Row")
        if history:
            for index, event in enumerate(history[:10], start=1):
                graph_state = event.get("graph_state") if isinstance(event.get("graph_state"), dict) else {}
                route = graph_state.get("selected_agent") or graph_state.get("selected_tool") or graph_state.get("route") or graph_state.get("tool") or "-"
                actions_table.add_row(
                    str(index),
                    str(event.get("step_index")),
                    str(event.get("reward")),
                    str(route),
                    _compact(event.get("row"), max_chars=220),
                )
            remaining = len(history) - 10
            if remaining > 0:
                actions_table.add_row("…", f"{remaining} paso(s) más", "", "", "env.history")
        else:
            actions_table.add_row("-", "(sin pasos registrados)", "-", "-", "-")
        console.print(actions_table)
    else:
        actions_table = Table(title="4) Acciones ejecutadas", show_lines=True)
        actions_table.add_column("#", justify="right")
        actions_table.add_column("Tool")
        actions_table.add_column("Estado")
        actions_table.add_column("Input")
        actions_table.add_column("Resultado")
        if tools:
            for index, tool in enumerate(tools, start=1):
                actions_table.add_row(
                    str(index),
                    _tool_label(tool, index),
                    "OK" if tool.get("ok") else "ERROR",
                    _compact(tool.get("input") or {}, max_chars=350),
                    str(tool.get("summary") or tool.get("error") or ""),
                )
        else:
            actions_table.add_row("-", "(no se ejecutaron tools)", "-", "-", "-")
        console.print(actions_table)

    section_number = 5
    if show_lineage:
        memory = _build_lineage(result, normalized, lineage=lineage, title=title, goal=lineage_goal)
        body = memory.human_text() if hasattr(memory, "human_text") else _compact(memory, max_chars=2200)
        console.print(Panel(body, title=f"{section_number}) Qué pasó · Lineage Memory", expand=False))
        section_number += 1

    for block in _sql_blocks(answer, tools):
        console.print(Panel(Syntax(str(block["content"]), "sql", word_wrap=True), title=f"{section_number}) {block['title']}", expand=False))
        section_number += 1

    for block in _table_blocks(answer, tools):
        rows = block.get("rows") or []
        if not rows:
            continue
        row_table = Table(title=f"{section_number}) {block['title']}", show_lines=False)
        columns = list(rows[0].keys()) if rows else []
        for column in columns:
            row_table.add_column(str(column))
        for row in rows[:5]:
            row_table.add_row(*[_one_line(row.get(column), 48) for column in columns])
        console.print(row_table)
        section_number += 1

    if not _should_print_validation(tools, expected_tools, normalized.get("validation")):
        return
    validation = _validation_summary(tools, expected_tools, normalized.get("validation"))
    validation_table = Table(title=f"{section_number}) Validación", show_lines=False)
    validation_table.add_column("Campo", style="bold")
    validation_table.add_column("Valor")
    validation_table.add_row("Regla esperada", str(validation["rule"]))
    validation_table.add_row("Tools esperadas", _format_expectation(validation["expectation"]))
    validation_table.add_row("Tools ejecutadas", ", ".join(validation["actual"]) if validation["actual"] else "ninguna")
    validation_table.add_row("Tools faltantes", ", ".join(validation["missing"]) if validation["missing"] else "ninguna")
    validation_table.add_row("Tools extra", ", ".join(validation["extra"]) if validation["extra"] else "ninguna")
    validation_table.add_row("Errores de tool", ", ".join(validation["failed"]) if validation["failed"] else "ninguno")
    if validation["contract_ok"] is not None:
        validation_table.add_row("Contrato", "OK" if validation["contract_ok"] else "ERROR")
    validation_table.add_row("Resultado", "OK" if validation["ok"] else "REVISAR")
    console.print(validation_table)
    if validation["issues"]:
        console.print(Panel(_rich_json(validation["issues"]), title="Issues", expand=False))


def print_human_result(
    result: Any,
    *,
    title: str = "Ejecución",
    expected_tools: ToolExpectationValue = None,
    pretty: bool = False,
    render_mode: str = "compact",
    show_lineage: bool = False,
    lineage: Any = None,
    lineage_goal: str = "",
) -> None:
    """Print one RunResult-like object using stable, framework-agnostic blocks.

    The function accepts ``RunResult`` instances and serialized dictionaries, so
    the same call works for direct tools, Agentic Systems agents, LangGraph state
    outputs and OpenAI Agents SDK runs.
    """

    normalized = _normalized(result)
    if render_mode not in {"compact", "debug", "lineage"}:
        raise ValueError("render_mode must be one of: compact, debug, lineage.")
    if render_mode == "debug":
        _print_header(title)
        print(_rich_json(normalized))
        return
    show_lineage = show_lineage or render_mode == "lineage"

    if pretty and _rich_available():
        _rich_print_human_result(
            result,
            title=title,
            expected_tools=expected_tools,
            show_lineage=show_lineage,
            lineage=lineage,
            lineage_goal=lineage_goal,
        )
        return

    runtime = normalized.get("runtime") or {}
    answer = normalized.get("answer") if isinstance(normalized.get("answer"), dict) else {}
    tools = normalized.get("tools") or []

    _print_header(title)

    _print_block(1, "Entrada del usuario")
    _print_input(normalized.get("input"))

    _print_block(2, "Runtime y usage")
    print(f"Estado: {'OK' if normalized.get('ok') else 'ERROR'}")
    print(f"Provider: {_runtime_engine(normalized) or 'n/a'}")
    print(f"Framework: {_runtime_framework(normalized) or 'agentic-systems'}")
    print(f"Mode: {runtime.get('mode') or 'n/a'}")
    if runtime.get("model"):
        print(f"Model: {runtime.get('model')}")
    print(f"Usage: {_format_usage(normalized.get('usage') or {})}")

    _print_block(3, "Respuesta del agente/sistema")
    print("Respuesta:")
    _print_answer(answer)

    execution_title = "Casos evaluados" if _runtime_framework(normalized) == "agentic-eval" and not tools else ("Pasos del episodio" if _runtime_framework(normalized) == "agentic-environment" and not tools else "Acciones ejecutadas")
    _print_block(4, execution_title)
    _plain_print_execution_block(normalized, tools)

    section_number = 5
    if show_lineage:
        _print_block(section_number, "Qué pasó · Lineage Memory")
        _print_lineage(result, normalized, lineage=lineage, title=title, goal=lineage_goal)
        section_number += 1

    sql_blocks = _sql_blocks(answer, tools)
    if sql_blocks:
        _print_block(section_number, "SQL ejecutado")
        _print_sql_blocks(sql_blocks)
        section_number += 1

    table_blocks = _table_blocks(answer, tools)
    if table_blocks:
        _print_block(section_number, "Preview de datos")
        _print_table_blocks(table_blocks)
        section_number += 1

    if _should_print_validation(tools, expected_tools, normalized.get("validation")):
        _print_block(section_number, "Validación")
        _print_validation(tools, expected_tools, normalized.get("validation"))


def print_human_results(
    results: Iterable[Any],
    *,
    title: str = "Ejecuciones",
    expected_tools: ToolExpectationValue = None,
    pretty: bool = False,
    render_mode: str = "compact",
    show_lineage: bool = False,
    lineage_goal: str = "",
) -> None:
    """Print several RunResult-like objects with stable numbering."""

    for index, result in enumerate(results, start=1):
        print_human_result(
            result,
            title=f"{title} #{index}",
            expected_tools=expected_tools,
            pretty=pretty,
            render_mode=render_mode,
            show_lineage=show_lineage,
            lineage_goal=lineage_goal,
        )
        print()


def _is_result_like(value: Any) -> bool:
    """Return True only for execution-result-like objects.

    Lists and dictionaries are valid final-answer payloads, so batch detection
    must be conservative. A batch is only a batch when every item looks like a
    real execution result.
    """

    if isinstance(value, Mapping):
        return any(key in value for key in ("runtime", "tool_events", "tools", "validation", "schema_version"))
    return hasattr(value, "normalized") or hasattr(value, "tool_events") or hasattr(value, "lineage")


def _result_batch(value: Any) -> list[Any] | None:
    if isinstance(value, (str, bytes, Mapping)):
        return None
    if not isinstance(value, Iterable):
        return None
    items = list(value)
    if not items:
        return None
    return items if all(_is_result_like(item) for item in items) else None


def human_result(
    result: Any,
    *,
    title: str = "Ejecución",
    expected_tools: ToolExpectationValue = None,
    pretty: bool = False,
    render_mode: str = "compact",
    show_lineage: bool = False,
    lineage: Any = None,
    lineage_goal: str = "",
) -> None:
    """Render one RunResult-like object or a batch of RunResult-like objects.

    ``pretty=False`` keeps deterministic plain text. ``pretty=True`` uses Rich
    tables/panels when Rich is installed and falls back to plain text otherwise.
    """

    batch = _result_batch(result)
    if batch is not None:
        batch_title = "Ejecuciones" if title == "Ejecución" else title
        print_human_results(
            batch,
            title=batch_title,
            expected_tools=expected_tools,
            pretty=pretty,
            render_mode=render_mode,
            show_lineage=show_lineage,
            lineage_goal=lineage_goal,
        )
        return

    print_human_result(
        result,
        title=title,
        expected_tools=expected_tools,
        pretty=pretty,
        render_mode=render_mode,
        show_lineage=show_lineage,
        lineage=lineage,
        lineage_goal=lineage_goal,
    )
