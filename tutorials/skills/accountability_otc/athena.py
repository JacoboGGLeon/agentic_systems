"""Athena execution helpers for the Accountability OTC skill."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .config import AccountabilitySettings
from .sql_safety import clean_load_date

try:
    import pandas as pd
except Exception:  # pragma: no cover - notebooks normally have pandas.
    pd = None  # type: ignore[assignment]

Reader = Callable[[str, AccountabilitySettings], list[dict[str, Any]]]


def normalize_scalar(value: Any) -> Any:
    if value is None:
        return None
    if pd is not None:
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "item") and callable(value.item):
        try:
            return normalize_scalar(value.item())
        except Exception:
            return str(value)
    return value


def rows_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    clean_rows = [{key: normalize_scalar(value) for key, value in row.items()} for row in rows]
    columns = list(clean_rows[0].keys()) if clean_rows else []
    return {"columns": columns, "rows": clean_rows, "n_rows": len(clean_rows)}


def _df_to_rows(df: Any) -> list[dict[str, Any]]:
    if df is None:
        return []
    return [{key: normalize_scalar(value) for key, value in row.items()} for row in df.to_dict(orient="records")]


def _athena_with_awswrangler(sql: str, settings: AccountabilitySettings) -> list[dict[str, Any]]:
    import awswrangler as wr  # type: ignore

    df = wr.athena.read_sql_query(
        sql=sql,
        database=settings.database,
        workgroup=settings.workgroup,
        ctas_approach=False,
    )
    return _df_to_rows(df)


def _athena_with_boto3(sql: str, settings: AccountabilitySettings) -> list[dict[str, Any]]:
    import boto3  # type: ignore

    client = boto3.client("athena", region_name=settings.region)
    started = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": settings.database},
        WorkGroup=settings.workgroup,
    )
    query_execution_id = started["QueryExecutionId"]

    while True:
        status_response = client.get_query_execution(QueryExecutionId=query_execution_id)
        status = status_response["QueryExecution"]["Status"]["State"]
        if status in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            break
        time.sleep(0.5)

    if status != "SUCCEEDED":
        reason = status_response["QueryExecution"]["Status"].get("StateChangeReason", "unknown")
        raise RuntimeError(f"Athena query {status.lower()}: {reason}")

    paginator = client.get_paginator("get_query_results")
    pages = paginator.paginate(QueryExecutionId=query_execution_id)

    headers: list[str] | None = None
    rows: list[dict[str, Any]] = []
    for page in pages:
        for raw_row in page["ResultSet"]["Rows"]:
            values = [cell.get("VarCharValue") for cell in raw_row.get("Data", [])]
            if headers is None:
                headers = [str(value) for value in values]
                continue
            padded = values + [None] * max(0, len(headers) - len(values))
            rows.append(dict(zip(headers, padded)))
    return rows


def execute_athena(
    sql: str,
    settings: AccountabilitySettings | None = None,
    reader: Reader | None = None,
) -> list[dict[str, Any]]:
    """Execute SQL in Athena with awswrangler first and boto3 fallback."""

    settings = settings or AccountabilitySettings()
    if reader is not None:
        return reader(sql, settings)
    try:
        return _athena_with_awswrangler(sql, settings)
    except ModuleNotFoundError:
        return _athena_with_boto3(sql, settings)


def latest_load_date(settings: AccountabilitySettings, reader: Reader | None = None, requested_date: str = "") -> str:
    requested = clean_load_date(requested_date) or date.today().isoformat()
    sql = f"""
SELECT MAX(CAST(load_date AS DATE)) AS resolved_load_date
FROM {settings.table_ref}
WHERE CAST(load_date AS DATE) <= DATE '{requested}'
""".strip()
    rows = execute_athena(sql, settings=settings, reader=reader)
    value = rows[0].get("resolved_load_date") if rows else None
    if not value:
        raise ValueError(f"No load_date found <= {requested}")
    return str(value)[:10]


class StaticAthenaReader:
    """Tiny fake reader for tests and docs."""

    def __init__(self, rows_by_pattern: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.rows_by_pattern = {str(key).lower(): rows for key, rows in (rows_by_pattern or {}).items()}
        self.executed_sql: list[str] = []

    def __call__(self, sql: str, settings: AccountabilitySettings) -> list[dict[str, Any]]:
        self.executed_sql.append(sql)
        lowered = sql.lower()
        if "max(cast(load_date" in lowered:
            return [{"resolved_load_date": "2026-05-11"}]
        for pattern, rows in self.rows_by_pattern.items():
            if pattern in lowered:
                return rows
        return []
