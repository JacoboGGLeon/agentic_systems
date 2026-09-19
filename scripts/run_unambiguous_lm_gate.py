"""Reproducible CLI for one live unambiguous LM gate route."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.unambiguous_lm_gate import run_gate


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "unambiguous_lm_gate_v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True)
    parser.add_argument("--framework", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    fixture = args.fixture.resolve()
    output = args.output.resolve()
    markdown = args.markdown.resolve()
    if output.exists() or markdown.exists():
        raise RuntimeError("Evidence outputs are immutable and must not be overwritten")
    raw_case = json.loads(fixture.read_text(encoding="utf-8"))
    report = run_gate(raw_case, args.provider, args.framework, args.model)
    application = Path(__file__).with_name("unambiguous_lm_gate.py")
    envelope = {
        "schema_version": "agentic_systems.unambiguous_lm_gate.evidence.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "commit": args.commit,
        "provider": args.provider,
        "framework": args.framework,
        "model": args.model,
        "source_hashes": {
            str(application.relative_to(ROOT)): _sha256(application),
            str(fixture.relative_to(ROOT)): _sha256(fixture),
        },
        "report": report,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown.write_text(report["evaluation_markdown"], encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "execution_passed": report["execution_passed"],
                "decision_passed": report["decision_passed"],
                "output": str(output),
                "markdown": str(markdown),
            },
            indent=2,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
