"""Fail when critical contract code reaches Radon grade C or worse."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CRITICAL_PATHS = (
    "src/agentic_systems/schemas",
    "src/agentic_systems/registry.py",
    "src/agentic_systems/protocols.py",
    "src/agentic_systems/normalization.py",
    "src/agentic_systems/integrations/adapters/tools.py",
)


def main() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "radon", "cc", *CRITICAL_PATHS, "-s", "-n", "C"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    report = completed.stdout.strip()
    if completed.returncode:
        print(completed.stderr.strip() or report)
        return completed.returncode
    if report:
        print("Critical code exceeds complexity grade B:\n" + report)
        return 1
    print("Complexity gate passed: all critical contracts are grade A/B.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
