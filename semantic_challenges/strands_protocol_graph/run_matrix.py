"""Run the focused semantic challenge and emit reviewable evidence."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
from pathlib import Path
import platform
import subprocess
from typing import Any

import agentic_systems as toolkit
from agentic_systems.errors import redact_sensitive_text
from agentic_systems.registry import PROVIDERS as CANONICAL_PROVIDERS

from .application import (
    ProtocolChallenge,
    challenge_case,
    judge_rubric,
    live_enabled,
    load_canonical_dotenv,
    new_evidence_tokens,
)


ROOT = Path(__file__).resolve().parents[2]
CHALLENGE_ROOT = Path(__file__).resolve().parent
DEFAULT_PROVIDERS = tuple(
    item.name
    for item in CANONICAL_PROVIDERS
    if item.live_flag and not item.attestation_environment
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def challenge_sha256() -> str:
    """Hash the complete challenge contract independently from the library wheel."""

    digest = hashlib.sha256()
    files = sorted(
        path
        for path in CHALLENGE_ROOT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix in {".py", ".json", ".md", ".txt", ".example"}
    )
    for path in files:
        relative = path.relative_to(CHALLENGE_ROOT).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _human(result: toolkit.RunResult, provider: str) -> str:
    stream = StringIO()
    with redirect_stdout(stream):
        toolkit.human_result(
            result,
            title=f"{provider} · Strands MCP+A2A · LangGraph",
            pretty=False,
            show_lineage=True,
            lineage_goal="Verify both protocol boundaries and the natural answer.",
        )
    return redact_sensitive_text(stream.getvalue()).strip()


def _retry_count(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    return sum(
        item
        if key == "retries" and isinstance(item, int)
        else _retry_count(item)
        if isinstance(item, dict)
        else 0
        for key, item in value.items()
    )


def _manual_review(
    result: toolkit.RunResult,
    report: Any,
    *,
    provider: str,
    model: str,
    human: str,
    case: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    nodes = list(result.walk())
    child = nodes[1] if len(nodes) == 2 else None
    names = [event.name for event in child.tool_events] if child is not None else []
    outputs = {event.name: event.output for event in child.tool_events} if child else {}
    if not report.ok:
        failures.append("Evaluator report failed.")
    if len(nodes) != 2:
        failures.append(f"Lineage expected 2 RunResults; observed {len(nodes)}.")
    if result.engine != provider or result.model != model:
        failures.append("Root provider/model identity differs from the declared cell.")
    if result.meta.get("framework_adapter") != "langgraph":
        failures.append("System root was not orchestrated by LangGraph.")
    if result.meta.get("graph_native_type") != "CompiledStateGraph":
        failures.append("Native graph is not CompiledStateGraph.")
    if child is None or child.meta.get("framework_adapter") != "strands":
        failures.append("The only child execution is not the Strands candidate.")
    if child is not None and child.engine != provider:
        failures.append("Strands candidate used a different provider.")
    expected = case["expected"]
    expected_tools = list(expected["tool_path"])
    if names != expected_tools:
        failures.append(f"Expected exact protocol Tool path; observed {names!r}.")
    for tool_name, subset in expected["tool_output_contains"].items():
        serialized = json.dumps(outputs.get(tool_name), ensure_ascii=False, default=str)
        for required in subset.values():
            if str(required) not in serialized:
                failures.append(f"Tool {tool_name!r} evidence is missing {required!r}.")
    public = result.text.strip()
    for required in expected["text_contains"]:
        if str(required).lower() not in public.lower():
            failures.append(f"Public answer is missing {required!r}.")
    if public.startswith(("{", "[")) or any(
        marker in public.lower()
        for marker in ("toolenvelope", "<thinking>", "<reasoning>")
    ):
        failures.append("Public answer exposes technical or private content.")
    if provider not in human or "LangGraph" not in human or "Strands" not in human:
        failures.append("human_result does not render the declared execution identity.")
    if result.meta.get("fallback_provider"):
        failures.append("A fallback provider was recorded.")
    if _retry_count(result.usage) != 0:
        failures.append("An undeclared retry occurred.")
    for node in nodes:
        invariants = node.check_invariants()
        if not invariants.ok:
            failures.append(
                f"Invariant failure for {node.meta.get('agent_name') or 'system'}: "
                f"{invariants.to_dict()}"
            )
    case = report.cases[0]
    judge = case.judge
    if judge is None or not judge.ok:
        failures.append("Native deterministic judge did not approve the episode.")
    elif judge.provider != "python-runtime" or judge.framework != "native":
        failures.append("Judge identity is not python-runtime × native.")
    elif judge.certification_tool != "certify_protocol_episode":
        failures.append("Judge did not record the required certification Tool.")
    return {
        "ok": not failures,
        "failures": failures,
        "observed": {
            "provider": result.engine,
            "model": result.model,
            "system_framework": result.meta.get("framework_adapter"),
            "candidate_framework": child.meta.get("framework_adapter")
            if child
            else None,
            "graph_native_type": result.meta.get("graph_native_type"),
            "tool_path": names,
            "execution_count": len(nodes),
            "judge_provider": judge.provider if judge else None,
            "judge_framework": judge.framework if judge else None,
        },
    }


def _bedrock_auth(provider: str, runtime: Any) -> dict[str, Any] | None:
    if provider != "bedrock-runtime":
        return None
    return toolkit.boto3_session_snapshot(
        region_name=str(runtime.region_name or "") or None
    )


def run_cell(provider: str) -> dict[str, Any]:
    if not live_enabled(provider):
        raise RuntimeError(
            f"{provider} is not authorized by its canonical RUN_*_LIVE flag."
        )
    runtime = toolkit.runtime(provider=provider)
    model = str(runtime.model_id or "").strip()
    mcp_token, a2a_token = new_evidence_tokens()
    case = challenge_case(
        provider,
        model,
        mcp_token=mcp_token,
        a2a_token=a2a_token,
    )
    with ProtocolChallenge(provider, model=model) as challenge:
        report = toolkit.Evaluator().evaluate(
            challenge,
            [case],
            judge=challenge.judge,
            rubric=judge_rubric(),
            mode="eval",
            environment_kwargs={"name": f"{provider}_strands_protocol_environment"},
            determinism="non_deterministic",
            reproducibility_conditions=[
                "same exact wheel and challenge manifest",
                "reachable local MCP and A2A loopback transports",
                "same provider model and canonical .env",
            ],
        )
        result = challenge.last_result
        if result is None:
            raise RuntimeError("Challenge execution produced no RunResult evidence.")
        human = _human(result, provider)
        review = _manual_review(
            result,
            report,
            provider=provider,
            model=model,
            human=human,
            case=case,
        )
        return {
            "provider": provider,
            "model": model,
            "ok": bool(report.ok and review["ok"]),
            "authentication": _bedrock_auth(provider, runtime),
            "eval_report": report.to_dict(),
            "eval_lineage": report.lineage(
                name=f"{provider}_strands_protocol_eval"
            ).to_dict(),
            "result": result.normalized(),
            "human_result": human,
            "result_lineage": result.lineage().to_dict(),
            "manual_review": review,
        }


def _review_markdown(attestation: dict[str, Any]) -> str:
    lines = [
        "# Strands protocol graph · semantic review",
        "",
        f"- Created: `{attestation['created_at']}`",
        f"- Commit: `{attestation['commit']}`",
        f"- Wheel SHA256: `{attestation.get('wheel_sha256') or 'source-run'}`",
        f"- Passed: `{attestation['summary']['passed']}`",
        f"- Failed: `{attestation['summary']['failed']}`",
        "",
    ]
    for cell in attestation["cells"]:
        observed = cell["manual_review"]["observed"]
        lines.extend(
            [
                f"## {cell['provider']}",
                "",
                f"- Verdict: `{'PASS' if cell['ok'] else 'FAIL'}`",
                f"- Model: `{cell['model']}`",
                f"- Route: `{observed['system_framework']} → {observed['candidate_framework']}`",
                f"- Tools: `{observed['tool_path']}`",
                f"- Judge: `{observed['judge_provider']} × {observed['judge_framework']}`",
                "",
                cell["human_result"],
                "",
            ]
        )
        if cell["manual_review"]["failures"]:
            lines.append("Failures:")
            lines.extend(f"- {item}" for item in cell["manual_review"]["failures"])
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dotenv", type=Path, default=ROOT / ".env")
    parser.add_argument("--providers", nargs="+", default=list(DEFAULT_PROVIDERS))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--wheel", type=Path)
    args = parser.parse_args()
    load_canonical_dotenv(args.dotenv)
    wheel_sha = _sha256(args.wheel) if args.wheel else None
    cells: list[dict[str, Any]] = []
    for provider in args.providers:
        print(f"[challenge] {provider} × langgraph(system) × strands(MCP+A2A)")
        try:
            cell = run_cell(provider)
        except Exception as exc:  # noqa: BLE001 - retain a structured failed cell.
            cell = {
                "provider": provider,
                "model": None,
                "ok": False,
                "error": f"{type(exc).__name__}: {redact_sensitive_text(str(exc))}",
                "manual_review": {"ok": False, "failures": [str(exc)], "observed": {}},
            }
        cells.append(cell)
        print(f"[challenge] ok={cell['ok']}")
    failed = len([cell for cell in cells if not cell["ok"]])
    attestation = {
        "schema_version": "agentic_systems.semantic-challenge-attestation.v1",
        "challenge": "strands-protocol-graph",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "commit": _commit(),
        "wheel": args.wheel.name if args.wheel else None,
        "wheel_sha256": wheel_sha,
        "challenge_sha256": challenge_sha256(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "dotenv": str(args.dotenv.resolve()) if args.dotenv.exists() else None,
        },
        "cells": cells,
        "summary": {
            "total": len(cells),
            "passed": len(cells) - failed,
            "failed": failed,
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "strands-protocol-graph-attestation.json"
    review = args.output_dir / "strands-protocol-graph-review.md"
    output.write_text(
        json.dumps(attestation, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    review.write_text(_review_markdown(attestation), encoding="utf-8")
    print(json.dumps({"output": str(output), "review": str(review), "failed": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
