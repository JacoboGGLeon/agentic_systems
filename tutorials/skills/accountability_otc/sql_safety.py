"""Read-only SQL safety helpers for the Accountability OTC skill."""

from __future__ import annotations

import re

from .config import AccountabilitySettings


def limit_value(value: int | None, settings: AccountabilitySettings, default: int = 20) -> int:
    try:
        limit = int(value if value is not None else default)
    except Exception:
        limit = default
    return max(1, min(limit, settings.max_limit))


def clean_load_date(load_date: str) -> str:
    text = str(load_date or "").strip()
    if not text:
        return ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValueError("load_date must use YYYY-MM-DD")
    return text


def single_statement(sql: str) -> str:
    cleaned = str(sql or "").strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    if ";" in cleaned:
        raise ValueError("Only one SQL statement is allowed.")
    return cleaned


def validate_read_only_sql(
    sql: str,
    settings: AccountabilitySettings | None = None,
    *,
    enforce_limit: bool = False,
    limit: int | None = None,
) -> str:
    """Validate that a SQL statement is read-only and scoped to the OTC table."""

    settings = settings or AccountabilitySettings()
    cleaned = single_statement(sql)
    if not re.match(r"^\s*(select|with)\b", cleaned, flags=re.IGNORECASE):
        raise ValueError("Only SELECT/WITH read-only SQL is allowed.")
    blocked = r"\b(insert|update|delete|drop|alter|create|truncate|merge|grant|revoke|unload)\b"
    if re.search(blocked, cleaned, flags=re.IGNORECASE):
        raise ValueError("DDL/DML statements are blocked.")
    normalized = " ".join(cleaned.lower().replace('"', "").split())
    allowed = f"{settings.database}.{settings.table}".lower()
    if allowed not in normalized:
        raise ValueError(f"SQL must reference only the allowed table: {settings.database}.{settings.table}")
    if enforce_limit and not re.search(r"\blimit\s+\d+\b", cleaned, flags=re.IGNORECASE):
        cleaned = f"{cleaned}\nLIMIT {limit_value(limit, settings, default=settings.max_limit)}"
    return cleaned
