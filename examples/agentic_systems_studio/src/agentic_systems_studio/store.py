"""SQLite persistence for the local Studio catalog and execution evidence."""

from __future__ import annotations

import json
from contextlib import contextmanager
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .catalog import SYSTEM_SPECS


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS systems (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    size TEXT NOT NULL,
    summary TEXT NOT NULL,
    runtime_skill TEXT NOT NULL,
    manifest_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stages (
    system_id TEXT NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    capability TEXT NOT NULL,
    tool_key TEXT NOT NULL,
    PRIMARY KEY (system_id, position)
);
CREATE TABLE IF NOT EXISTS assets (
    system_id TEXT NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    PRIMARY KEY (system_id, path)
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    system_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    framework TEXT NOT NULL,
    ok INTEGER NOT NULL,
    input_json TEXT NOT NULL,
    result_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS compositions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    system_ids_json TEXT NOT NULL,
    result_json TEXT
);
"""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _result_payload(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if hasattr(result, "to_dict"):
        return result.to_dict()
    return {"value": result}


class StudioStore:
    """Small local evidence store; never persists provider credentials."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> Path:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            for spec in SYSTEM_SPECS:
                connection.execute(
                    """
                    INSERT INTO systems(id, name, size, summary, runtime_skill, manifest_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      name=excluded.name,
                      size=excluded.size,
                      summary=excluded.summary,
                      runtime_skill=excluded.runtime_skill,
                      manifest_json=excluded.manifest_json
                    """,
                    (
                        spec.id,
                        spec.name,
                        spec.size,
                        spec.summary,
                        spec.runtime_skill,
                        _json(spec.to_dict()),
                    ),
                )
                connection.execute("DELETE FROM stages WHERE system_id = ?", (spec.id,))
                connection.execute("DELETE FROM assets WHERE system_id = ?", (spec.id,))
                connection.executemany(
                    """
                    INSERT INTO stages(system_id, position, id, name, kind, capability, tool_key)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            spec.id,
                            position,
                            stage.id,
                            stage.name,
                            stage.kind,
                            stage.capability,
                            stage.tool_key,
                        )
                        for position, stage in enumerate(spec.stages)
                    ],
                )
                connection.executemany(
                    "INSERT INTO assets(system_id, path) VALUES (?, ?)",
                    [(spec.id, asset) for asset in spec.assets],
                )
        return self.path

    def record_run(
        self,
        *,
        system_id: str,
        provider: str,
        framework: str,
        input: Any,
        result: Any,
    ) -> int:
        self.initialize()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO runs(created_at, system_id, provider, framework, ok, input_json, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    system_id,
                    provider,
                    framework,
                    int(bool(getattr(result, "ok", False))),
                    _json(input),
                    _json(_result_payload(result)),
                ),
            )
            return int(cursor.lastrowid)

    def record_composition(
        self,
        *,
        mode: str,
        system_ids: tuple[str, ...],
        result: Any | None = None,
    ) -> int:
        self.initialize()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO compositions(created_at, mode, system_ids_json, result_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    mode,
                    _json(system_ids),
                    None if result is None else _json(_result_payload(result)),
                ),
            )
            return int(cursor.lastrowid)

    def inventory(self) -> dict[str, int]:
        self.initialize()
        with self.connect() as connection:
            return {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("systems", "stages", "assets", "runs", "compositions")
            }

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]


__all__ = ["SCHEMA", "StudioStore"]
