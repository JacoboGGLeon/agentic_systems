"""Small, versioned performance ratchet for contract-critical operations."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Callable

from agentic_systems.registry import registry_manifest
from agentic_systems.results import RunResult
from agentic_systems.schemas import ExecutionLimits


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "quality" / "performance-baseline.json"


def _run(operation: Callable[[], object], iterations: int) -> float:
    samples: list[float] = []
    for _ in range(3):
        started = perf_counter()
        for _ in range(iterations):
            operation()
        samples.append((perf_counter() - started) * 1000)
    return median(samples)


def main() -> int:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))["benchmarks"]
    result = RunResult(text="ok", data={"ok": True}, engine="python-runtime")
    operations: dict[str, Callable[[], object]] = {
        "registry_manifest": registry_manifest,
        "execution_limits_validation": lambda: ExecutionLimits(
            max_turns=6, max_tool_calls=0, max_tokens=800, timeout_s=60
        ),
        "run_result_normalized": result.normalized,
    }
    failed: list[str] = []
    for name, operation in operations.items():
        contract = baseline[name]
        elapsed = _run(operation, int(contract["iterations"]))
        budget = float(contract["max_median_ms"])
        print(f"{name}: {elapsed:.3f} ms (budget {budget:.3f} ms)")
        if elapsed > budget:
            failed.append(name)
    if failed:
        print(f"Performance gate failed: {failed}")
        return 1
    print("Performance gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
