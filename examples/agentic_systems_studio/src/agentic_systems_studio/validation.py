"""Portable live validation for every executable Studio system."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
from time import perf_counter
from typing import Any, Iterable

from .catalog import SYSTEM_SPECS
from .systems import StudioConfig, build_system


def _usage_summary(value: Any) -> dict[str, int]:
    usage = dict(value or {})
    return {
        key: int(usage[key])
        for key in ("input_tokens", "output_tokens", "total_tokens")
        if isinstance(usage.get(key), (int, float))
    }


def validate_catalog(
    config: StudioConfig,
    system_ids: Iterable[str] | None = None,
    *,
    fail_fast: bool = False,
) -> dict[str, Any]:
    """Execute real catalog systems and retain non-secret contract evidence."""

    requested = tuple(system_ids or (spec.id for spec in SYSTEM_SPECS))
    rows: list[dict[str, Any]] = []
    for system_id in requested:
        started = perf_counter()
        try:
            studio_system = build_system(system_id, config)
            result = studio_system.run()
            children = list(result.children)
            expected_engines = [
                "python-runtime" if stage.kind == "operator" else config.provider
                for stage in studio_system.spec.stages
            ]
            child_engines = [child.engine for child in children]
            engine_alignment = (
                True if config.provider == "auto" else child_engines == expected_engines
            )
            invariants = result.check_invariants()
            ok = bool(
                result.ok
                and invariants.ok
                and len(children) == len(studio_system.spec.stages)
                and engine_alignment
            )
            row = {
                "id": system_id,
                "name": studio_system.spec.name,
                "ok": ok,
                "seconds": round(perf_counter() - started, 3),
                "stage_count": len(studio_system.spec.stages),
                "child_count": len(children),
                "child_engines": child_engines,
                "engine_alignment": engine_alignment,
                "invariants_ok": invariants.ok,
                "invariant_issues": [
                    {
                        "code": issue.code,
                        "severity": issue.severity,
                        "path": issue.path,
                        "meta": issue.meta,
                    }
                    for issue in invariants.issues
                ],
                "tool_event_count": sum(len(child.tool_events) for child in children),
                "usage": _usage_summary(result.usage),
                "error_codes": [
                    str(error.get("code", "unknown")) for error in result.errors
                ],
            }
        except Exception as exc:  # noqa: BLE001 - evidence must retain failed rows.
            row = {
                "id": system_id,
                "ok": False,
                "seconds": round(perf_counter() - started, 3),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        rows.append(row)
        if fail_fast and not row["ok"]:
            break

    passed = sum(bool(row["ok"]) for row in rows)
    total_seconds = round(sum(float(row.get("seconds", 0.0)) for row in rows), 3)
    total_tokens = sum(
        int((row.get("usage") or {}).get("total_tokens", 0)) for row in rows
    )
    total_stages = sum(int(row.get("stage_count", 0)) for row in rows)
    return {
        "schema_version": "agentic-systems.studio-live-validation/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": config.provider,
        "framework": config.framework,
        "model": config.model,
        "requested": len(requested),
        "executed": len(rows),
        "passed": passed,
        "failed": len(rows) - passed,
        "ok": passed == len(requested),
        "total_seconds": total_seconds,
        "total_tokens": total_tokens,
        "total_stages": total_stages,
        "systems": rows,
    }


def write_validation_report(report: dict[str, Any], path: str | Path) -> Path:
    """Write one credential-free validation report."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destination


__all__ = ["validate_catalog", "write_validation_report"]
