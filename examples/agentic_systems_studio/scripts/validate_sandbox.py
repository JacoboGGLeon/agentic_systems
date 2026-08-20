"""Run the complete Studio validation matrix in ADA, Colab or another sandbox."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from agentic_systems_studio import StudioConfig, validate_catalog
from agentic_systems_studio.validation import write_validation_report

DEFAULT_FRAMEWORKS = ("agentic-systems", "langgraph", "openai-agents", "strands")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--framework", action="append", dest="frameworks")
    parser.add_argument("--system", action="append", dest="systems")
    parser.add_argument("--output", type=Path, default=Path("evidence/sandbox"))
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args(argv)

    frameworks = tuple(args.frameworks or DEFAULT_FRAMEWORKS)
    args.output.mkdir(parents=True, exist_ok=True)
    reports = []
    for framework in frameworks:
        report = validate_catalog(
            StudioConfig(
                provider=args.provider,
                framework=framework,
                model=args.model,
                timeout_s=args.timeout,
                max_tokens=args.max_tokens,
            ),
            args.systems,
            fail_fast=args.fail_fast,
        )
        destination = args.output / f"{args.provider}-{framework}.json"
        write_validation_report(report, destination)
        reports.append(
            {
                "framework": framework,
                "ok": report["ok"],
                "passed": report["passed"],
                "failed": report["failed"],
                "total_stages": report["total_stages"],
                "total_tokens": report["total_tokens"],
                "report": destination.name,
            }
        )
        if args.fail_fast and not report["ok"]:
            break

    matrix = {
        "schema_version": "agentic-systems.studio-sandbox-matrix/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": args.provider,
        "model": args.model,
        "frameworks": reports,
        "ok": len(reports) == len(frameworks)
        and all(report["ok"] for report in reports),
    }
    matrix_path = args.output / f"{args.provider}-matrix.json"
    matrix_path.write_text(
        json.dumps(matrix, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(matrix, indent=2, ensure_ascii=False))
    return 0 if matrix["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
