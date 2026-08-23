"""Reject new Pyright debt while legacy diagnostics are removed gradually."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "quality" / "pyright-baseline.json"


def _relative(path: str) -> str:
    return Path(path).resolve().relative_to(ROOT).as_posix()


def _run_pyright() -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyright",
            "--project",
            "quality/pyright-legacy.json",
            "--outputjson",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if not completed.stdout.strip():
        raise RuntimeError(f"Pyright did not emit JSON: {completed.stderr.strip()}")
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("Pyright JSON output must be an object.")
    return payload


def main() -> int:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    report = _run_pyright()
    diagnostics = report.get("generalDiagnostics") or []
    errors = Counter(
        _relative(str(item["file"]))
        for item in diagnostics
        if item.get("severity") == "error"
    )
    warnings = sum(item.get("severity") == "warning" for item in diagnostics)
    allowed = baseline["errors_by_file"]
    regressions = {
        path: {"actual": count, "baseline": int(allowed.get(path, 0))}
        for path, count in sorted(errors.items())
        if count > int(allowed.get(path, 0))
    }
    error_count = sum(errors.values())
    if error_count > int(baseline["error_count"]):
        regressions["__total_errors__"] = {
            "actual": error_count,
            "baseline": int(baseline["error_count"]),
        }
    if warnings > int(baseline["warning_count"]):
        regressions["__total_warnings__"] = {
            "actual": warnings,
            "baseline": int(baseline["warning_count"]),
        }
    print(
        json.dumps(
            {
                "errors": error_count,
                "warnings": warnings,
                "regressions": regressions,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())
