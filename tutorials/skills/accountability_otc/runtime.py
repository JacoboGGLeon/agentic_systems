"""Runtime helpers for the external Accountability OTC skill."""

from __future__ import annotations

from typing import Any

from .athena import Reader, execute_athena, latest_load_date, rows_payload
from .catalog import QUERY_CATALOG, load_catalog, render_semantic_sql, resolve_query_id
from .config import AccountabilitySettings
from .nl2sql_agent import BedrockNL2SQLPlanner, NL2SQLPlanner
from .sql_safety import limit_value, validate_read_only_sql


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    table = result.get("table") or {}
    return {
        "tool": result.get("tool"),
        "ok": result.get("ok"),
        "route": result.get("route"),
        "rows": table.get("n_rows"),
        "summary": result.get("summary") or result.get("error"),
    }


def render_query_sql(
    query_id: str,
    *,
    load_date: str = "",
    limit: int = 20,
    settings: AccountabilitySettings | None = None,
    reader: Reader | None = None,
) -> tuple[str, str, dict[str, str]]:
    settings = settings or AccountabilitySettings()
    resolved_query_id = resolve_query_id(query_id)
    spec = QUERY_CATALOG[resolved_query_id]
    resolved_date = latest_load_date(settings, reader=reader, requested_date=load_date)
    selected_limit = limit_value(limit, settings)
    sql = spec["sql"].format(table=settings.table_ref, load_date=resolved_date, limit=selected_limit)
    return resolved_query_id, validate_read_only_sql(sql, settings), spec


def _summary(title: str, table: dict[str, Any]) -> str:
    rows = table.get("rows") or []
    if not rows:
        return f"{title}: sin filas devueltas."
    preview = ", ".join(f"{key}={value}" for key, value in list(rows[0].items())[:4])
    return f"{title}: {table.get('n_rows', 0)} fila(s). Primer registro: {preview}."


def _ok_result(
    *,
    tool: str,
    route: str,
    title: str,
    sql: str,
    rows: list[dict[str, Any]],
    query_id: str | None = None,
    question: str | None = None,
) -> dict[str, Any]:
    table = rows_payload(rows)
    query = {"query_id": query_id, "title": title, "question": question}
    query = {key: value for key, value in query.items() if value is not None}
    return {
        "schema_version": "agentic_systems.tool_result.v1",
        "ok": True,
        "tool": tool,
        "route": route,
        "query": query,
        "title": title,
        "sql": sql,
        "table": table,
        "summary": _summary(title, table),
    }


def _error_result(
    *,
    tool: str,
    route: str,
    error: Exception | str,
    sql: str | None = None,
    query_id: str | None = None,
    question: str | None = None,
) -> dict[str, Any]:
    query = {"query_id": query_id, "question": question}
    query = {key: value for key, value in query.items() if value is not None}
    return {
        "schema_version": "agentic_systems.tool_result.v1",
        "ok": False,
        "tool": tool,
        "route": route,
        "query": query,
        "sql": sql,
        "error": str(error),
        "summary": str(error),
    }


def run_catalog_query(
    query_id: str,
    *,
    load_date: str = "",
    limit: int = 20,
    settings: AccountabilitySettings | None = None,
    reader: Reader | None = None,
    tool_name: str = "free_sql",
    route: str = "catalog_sql",
) -> dict[str, Any]:
    settings = settings or AccountabilitySettings()
    try:
        resolved_query_id, sql, spec = render_query_sql(query_id, load_date=load_date, limit=limit, settings=settings, reader=reader)
        rows = execute_athena(sql, settings=settings, reader=reader)
        return _ok_result(tool=tool_name, route=route, query_id=resolved_query_id, title=spec["title"], sql=sql, rows=rows)
    except Exception as exc:  # noqa: BLE001 - tutorial failures should stay structured.
        return _error_result(tool=tool_name, route=route, query_id=query_id, error=exc)


def run_named_query(
    query_key: str,
    *,
    load_date: str = "",
    limit: int = 20,
    settings: AccountabilitySettings | None = None,
    reader: Reader | None = None,
) -> dict[str, Any]:
    """Backward-compatible alias for known query execution."""

    return run_catalog_query(query_key, load_date=load_date, limit=limit, settings=settings, reader=reader, tool_name="free_sql", route="catalog_sql")


def run_free_sql(
    sql: str = "",
    *,
    query_id: str = "",
    load_date: str = "",
    limit: int = 50,
    settings: AccountabilitySettings | None = None,
    reader: Reader | None = None,
) -> dict[str, Any]:
    settings = settings or AccountabilitySettings()
    if query_id:
        return run_catalog_query(query_id, load_date=load_date, limit=limit, settings=settings, reader=reader, tool_name="free_sql", route="catalog_sql")
    try:
        safe_sql = validate_read_only_sql(sql, settings, enforce_limit=True, limit=limit)
        rows = execute_athena(safe_sql, settings=settings, reader=reader)
        return _ok_result(tool="free_sql", route="free_sql", title="SQL libre validado", sql=safe_sql, rows=rows)
    except Exception as exc:  # noqa: BLE001
        return _error_result(tool="free_sql", route="free_sql", error=exc, sql=sql)


def run_nl2sql(
    question: str,
    *,
    load_date: str = "",
    limit: int = 20,
    settings: AccountabilitySettings | None = None,
    reader: Reader | None = None,
    planner: NL2SQLPlanner | None = None,
) -> dict[str, Any]:
    """Run the agent-tool NL2SQL path and execute the generated safe SQL.

    ``nl2sql`` is intentionally a tool with an internal planner agent. The
    planner reads the semantic catalog, returns a constrained JSON plan, and
    local code validates that plan before rendering SQL. Raw model SQL is never
    executed.
    """

    settings = settings or AccountabilitySettings()
    catalog = load_catalog()
    route = "nl2sql_agent_tool"
    try:
        resolved_date = latest_load_date(settings, reader=reader, requested_date=load_date)
        selected_limit = limit_value(limit, settings)
        selected_planner = planner or BedrockNL2SQLPlanner(settings=settings)
        planning = selected_planner.plan(
            question,
            catalog=catalog,
            load_date=resolved_date,
            limit=selected_limit,
        )
        sql = render_semantic_sql(planning.plan, table_ref=settings.table_ref, catalog=catalog)
        safe_sql = validate_read_only_sql(sql, settings)
        rows = execute_athena(safe_sql, settings=settings, reader=reader)
        title = "NL2SQL agent-tool OTC"
        result = _ok_result(tool="nl2sql", route=route, title=title, sql=safe_sql, rows=rows, question=question)
        result["nl2sql"] = planning.plan.to_dict()
        result["nl2sql_agent"] = dict(planning.meta)
        return result
    except Exception as exc:  # noqa: BLE001
        return _error_result(tool="nl2sql", route=route, question=question, error=exc)
