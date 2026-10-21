"""Run and record the mandatory offline release gates without live inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def gate_commands() -> dict[str, list[str]]:
    py = sys.executable
    return {
        "lint": [
            py,
            "-m",
            "ruff",
            "check",
            "src",
            "tests",
            "semantic_challenges",
            "scripts/live_release_budget.py",
            "scripts/run_core_acceptance.py",
            "scripts/core_release_certification.py",
            "scripts/run_release_offline.py",
            "scripts/build_release_certification.py",
            "scripts/build_release_manifest.py",
            "scripts/build_release_assets.py",
        ],
        "format": [py, "scripts/check_format.py"],
        "typing": [py, "-m", "pyright", "--project", "pyrightconfig.json"],
        "typing-ratchet": [py, "scripts/check_pyright_baseline.py"],
        "imports": [
            str(
                Path(py).with_name(
                    "lint-imports.exe" if os.name == "nt" else "lint-imports"
                )
            )
        ],
        "architecture": [py, "scripts/check_architecture.py"],
        "complexity": [py, "scripts/check_complexity.py"],
        "licenses": [py, "scripts/check_licenses.py"],
        "secrets": [py, "scripts/check_secrets.py"],
        "benchmarks": [py, "scripts/check_benchmarks.py"],
        "tests-and-notebooks": [
            py,
            "-m",
            "pytest",
            "--cov=agentic_systems",
            "--cov-config=pyproject.toml",
            "--cov-report=term-missing",
            "-q",
        ],
        "core-branches": [
            py,
            "-m",
            "pytest",
            "--ignore=tests/release/test_tutorial_execution.py",
            "--cov=agentic_systems",
            "--cov-config=.coveragerc-core-branches",
            "-q",
        ],
        "bedrock": [
            py,
            "-m",
            "pytest",
            "tests/providers",
            "--cov=agentic_systems.providers.bedrock_runtime",
            "--cov=agentic_systems.providers.bedrock",
            "--cov-config=.coveragerc-bedrock",
            "-q",
        ],
        "provider-branches": [
            py,
            "-m",
            "pytest",
            "tests/providers",
            "tests/integration_conformance/test_provider_conformance.py",
            "tests/integration_conformance/test_system_runtime.py",
            "tests/frameworks/test_provider_framework_matrix.py",
            "--cov=agentic_systems.providers",
            "--cov-config=.coveragerc-providers-branches",
            "-q",
        ],
        "framework-branches": [
            py,
            "-m",
            "pytest",
            "--ignore=tests/release/test_tutorial_execution.py",
            "--cov=agentic_systems.integrations",
            "--cov-config=.coveragerc-frameworks-branches",
            "-q",
        ],
        "studio": [py, "-m", "pytest", "examples/agentic_systems_studio/tests", "-q"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    report_path = directory / "offline-gates.json"
    if report_path.exists():
        raise ValueError("Use a new directory; prior gate evidence is immutable")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
    environment["OTEL_SDK_DISABLED"] = "true"
    for key in (
        "OPENAI",
        "BEDROCK",
        "OLLAMA",
        "VLLM",
        "LANGGRAPH",
        "OPENAI_AGENTS",
        "STRANDS",
        "MATRIX",
    ):
        environment[f"RUN_{key}_LIVE"] = "0"
    environment["AGENTIC_SYSTEMS_RUN_LIVE_NOTEBOOKS"] = "0"
    report = {
        "commit_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "checks": [],
    }
    for name, command in gate_commands().items():
        log = directory / f"{name}.log"
        print(f"[offline] {name}", flush=True)
        with log.open("wb") as stream:
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
            )
        report["checks"].append(
            {
                "name": name,
                "command": command,
                "exit_code": result.returncode,
                "log": log.name,
                "sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            }
        )
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"[offline] {name}: exit {result.returncode}", flush=True)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
