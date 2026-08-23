"""Enforce Ruff formatting on strict contracts and every changed Python file."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
STRICT_PATHS = (
    ROOT / "src" / "agentic_systems" / "schemas",
    ROOT / "src" / "agentic_systems" / "registry.py",
    ROOT / "src" / "agentic_systems" / "protocols.py",
    ROOT / "src" / "agentic_systems" / "normalization.py",
    ROOT / "scripts" / "check_format.py",
    ROOT / "scripts" / "run_live_matrix.py",
    ROOT / "scripts" / "validate_live_attestation.py",
    ROOT / "tests" / "contracts",
)


def _git_lines(*arguments: str) -> set[Path]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in {0, 1}:
        return set()
    return {
        ROOT / line.strip()
        for line in completed.stdout.splitlines()
        if line.strip().endswith(".py")
    }


def _changed_python_files() -> set[Path]:
    base_ref = os.getenv("GITHUB_BASE_REF")
    if base_ref:
        return _git_lines(
            "diff", "--name-only", "--diff-filter=ACMR", f"origin/{base_ref}...HEAD"
        )
    if os.getenv("GITHUB_ACTIONS"):
        return _git_lines("diff", "--name-only", "--diff-filter=ACMR", "HEAD^", "HEAD")
    return (
        _git_lines("diff", "--name-only", "--diff-filter=ACMR")
        | _git_lines("diff", "--cached", "--name-only", "--diff-filter=ACMR")
        | _git_lines("ls-files", "--others", "--exclude-standard")
    )


def _expand(paths: set[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_dir():
            files.update(path.rglob("*.py"))
        elif path.suffix == ".py" and path.exists():
            files.add(path)
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    files = _expand(set(STRICT_PATHS) | _changed_python_files())
    if not files:
        print("No Python files selected for the formatting gate.")
        return 0
    command = [sys.executable, "-m", "ruff", "format"]
    if not args.write:
        command.append("--check")
    command.extend(str(path.relative_to(ROOT)) for path in files)
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
