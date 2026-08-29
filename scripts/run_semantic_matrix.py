"""Run the semantic 2.1 matrix and emit auditable evidence."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from typing import Any

import agentic_systems as toolkit
from agentic_systems.errors import redact_sensitive_text
from agentic_systems.results import RunResult

from semantic_e2e_application import (
    FRAMEWORKS,
    PROVIDERS,
    build_semantic_cell,
    expected_paths,
    looks_like_short_poem,
    semantic_cases,
    supports_model_generation,
    states_verified_product,
)


ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_APPLICATION_PATH = (
    Path(__file__).resolve().with_name("semantic_e2e_application.py")
)
SECRET_KEY_MARKERS = (
    "API_KEY",
    "PASSWORD",
    "SECRET",
    "CREDENTIAL",
    "AUTHORIZATION",
    "ACCESS_KEY",
    "BEARER_TOKEN",
    "SESSION_TOKEN",
    "SECURITY_TOKEN",
    "WEB_IDENTITY_TOKEN",
)
PUBLIC_SECURITY_METADATA_KEYS = {
    "authentication_mode",
    "credential_method",
    "bedrock_api_key_configured",
    "has_credentials",
    "sts_identity_available",
}


def _is_secret_key(key: Any) -> bool:
    normalized = str(key).strip().lower()
    if normalized in PUBLIC_SECURITY_METADATA_KEYS:
        return False
    upper = normalized.upper()
    return upper in {"TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"} or any(
        marker in upper for marker in SECRET_KEY_MARKERS
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


def _load_canonical_dotenv(path: Path) -> bool:
    """Load .env with explicit precedence; process env is fallback only."""

    if not path.exists():
        return False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value
    return True


def _model(provider: str) -> str:
    """Resolve model identity through the same public runtime factory as users."""

    model = str(toolkit.runtime(provider=provider).model_id or "").strip()
    if not model:
        raise ValueError(
            f"The canonical .env did not resolve a model for {provider!r}."
        )
    return model


def _environment(dotenv: Path, providers: tuple[str, ...]) -> dict[str, Any]:
    runtime_descriptions = {
        provider: toolkit.runtime(provider=provider).describe()
        for provider in providers
    }
    provider_rows: dict[str, dict[str, Any]] = {}
    for provider in providers:
        row: dict[str, Any] = {
            "model": _model(provider),
            "runtime": runtime_descriptions[provider],
        }
        if provider == "bedrock-runtime":
            row["authentication"] = toolkit.boto3_session_snapshot(
                region_name=str(runtime_descriptions[provider].get("region") or "")
                or None
            )
        provider_rows[provider] = row
    return {
        "dotenv": str(dotenv.resolve()) if dotenv.exists() else None,
        "dotenv_loaded": dotenv.exists(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "providers": provider_rows,
    }


def _agent_nodes(result: RunResult) -> list[RunResult]:
    return [node for node in result.walk() if node.meta.get("agent_name")]


def _tool_path(result: RunResult) -> list[str]:
    nodes = _agent_nodes(result) or list(result.walk())
    return [event.name for node in nodes for event in node.tool_events]


def _agent_path(result: RunResult) -> list[str]:
    return [str(node.meta["agent_name"]) for node in _agent_nodes(result)]


def _retries(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    return sum(
        item
        if key == "retries" and isinstance(item, int)
        else _retries(item)
        if isinstance(item, dict)
        else 0
        for key, item in value.items()
    )


def _human(result: RunResult, provider: str, framework: str, name: str) -> str:
    stream = StringIO()
    with redirect_stdout(stream):
        toolkit.human_result(
            result,
            title=f"{provider} × {framework} × {name}",
            pretty=False,
            show_lineage=True,
            lineage_goal="Verify routing, evidence, answer, and runtime identity.",
        )
    return redact_sensitive_text(stream.getvalue()).strip()


def _human_answer_block(human: str) -> str:
    """Extract the exact public answer rendered by human_result."""

    marker = "Respuesta:\n"
    start = human.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    end = human.find("\n\n4)", start)
    return human[start : end if end >= 0 else None].strip()


def _review(
    result: RunResult,
    eval_case: Any,
    declared: dict[str, Any],
    provider: str,
    framework: str,
    human: str,
    lineage: Any,
) -> dict[str, Any]:
    failures: list[str] = []
    expected_agents, expected_tools = expected_paths(declared)
    expected = declared.get("expected") or {}
    allowed_tool_paths = expected.get("allowed_tool_paths")
    if allowed_tool_paths is None:
        allowed_tool_paths = [expected_tools]
    allowed_tool_paths = [
        list(path) for path in allowed_tool_paths if isinstance(path, (list, tuple))
    ]
    agents = _agent_path(result)
    tools = _tool_path(result)
    if agents != expected_agents:
        failures.append(f"agent_path expected={expected_agents!r} observed={agents!r}")
    if tools not in allowed_tool_paths:
        failures.append(f"tool_path allowed={allowed_tool_paths!r} observed={tools!r}")

    agent_nodes = _agent_nodes(result)
    identity = agent_nodes[0] if agent_nodes else result
    observed_framework = identity.meta.get("framework_adapter") or identity.meta.get(
        "framework"
    )
    if identity.engine != provider:
        failures.append(f"provider expected={provider!r} observed={identity.engine!r}")
    if observed_framework != framework:
        failures.append(
            f"framework expected={framework!r} observed={observed_framework!r}"
        )
    if any(node.meta.get("fallback_provider") for node in result.walk()):
        failures.append("provider fallback was observed")
    if _retries(eval_case.candidate_usage) or _retries(eval_case.judge_usage):
        failures.append("an unapproved retry was observed")

    for node in result.walk():
        issues = [
            issue.code
            for issue in node.check_invariants().issues
            if issue.severity == "error"
        ]
        if issues:
            failures.append(f"invariants failed: {issues}")
        for child in node.children:
            if child.parent_execution_id != node.execution_id:
                failures.append("parent/child execution identity is inconsistent")

    answer = result.text.strip()
    forbidden = (
        '"kind": "object"',
        "ToolEnvelope",
        "<thinking>",
        "<think>",
        "<reasoning>",
        " -> {",
    )
    if not answer:
        failures.append("public answer is empty")
    if any(marker in answer for marker in forbidden):
        failures.append("public answer exposes technical or private content")

    name = str(declared["name"])
    if name == "calculation" and "323" not in answer:
        failures.append("calculation answer does not state 323")
    elif name == "poetic_calculation":
        if not states_verified_product(answer):
            failures.append("poetic calculation does not state 323")
        if supports_model_generation(provider) and not looks_like_short_poem(answer):
            failures.append(
                "poetic calculation is not a substantive poem of at least three lines"
            )
    elif name == "text_analysis" and not ("4" in answer and "29" in answer):
        failures.append("text answer does not state exact 4/29 metrics")
    elif name == "out_of_scope":
        if any(tool.startswith("delegate_") for tool in tools):
            failures.append("out-of-scope request delegated to a specialist")
        if not any(
            word in answer.lower()
            for word in ("please", "can help", "choose", "provide")
        ):
            failures.append("out-of-scope answer is not a useful clarification")

    judge = eval_case.judge
    if judge is None:
        failures.append("judge evidence is missing")
    else:
        if judge.provider != provider:
            failures.append(
                f"judge provider expected={provider!r} observed={judge.provider!r}"
            )
        if judge.framework != framework:
            failures.append(
                f"judge framework expected={framework!r} observed={judge.framework!r}"
            )
        for criterion, score in judge.criteria.items():
            if score < judge.threshold:
                failures.append(
                    f"judge {criterion}={score:.3f} below {judge.threshold:.3f}"
                )
    if not bool((eval_case.deterministic_validation or {}).get("ok")):
        failures.append("deterministic validation failed")
    if not eval_case.ok:
        failures.append("combined deterministic + judge gate failed")

    lineage_agents = [
        str(step.evidence.get("agent"))
        for step in lineage.steps
        if step.kind == "execution" and step.evidence.get("agent")
    ]
    lineage_tools = [step.source for step in lineage.steps if step.kind == "tool"]
    if lineage_agents != ["system", *expected_agents]:
        failures.append(f"lineage agents are inconsistent: {lineage_agents!r}")
    if lineage_tools not in allowed_tool_paths:
        failures.append(f"lineage tools are not allowed: {lineage_tools!r}")
    if f"Provider: {provider}" not in human:
        failures.append("human_result mislabels provider")
    if f"Framework: {framework}" not in human:
        failures.append("human_result mislabels framework")
    if answer not in human:
        failures.append("human_result omits the public answer")
    rendered_answer = _human_answer_block(human)
    if not rendered_answer:
        failures.append("human_result public answer block is empty")
    elif rendered_answer.startswith(("{", "[")):
        failures.append("human_result exposes structured technical JSON as its answer")
    elif any(marker in rendered_answer for marker in forbidden):
        failures.append("human_result answer exposes technical or private content")

    return {
        "ok": not failures,
        "failures": failures,
        "observed_provider": identity.engine,
        "observed_framework": observed_framework,
        "observed_model": identity.model,
        "agent_path": agents,
        "tool_path": tools,
        "lineage_agents": lineage_agents,
        "lineage_tools": lineage_tools,
    }


def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _safe(item) for key, item in value.items() if not _is_secret_key(key)
        }
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    return redact_sensitive_text(value) if isinstance(value, str) else value


def _run_cell(provider: str, framework: str) -> dict[str, Any]:
    episodes: list[dict[str, Any]] = []
    reports: list[Any] = []
    model = _model(provider)
    for declared in semantic_cases(provider, framework):
        # A fresh System, Orchestrator, specialists, Skill, Judge, and Environment
        # are created for every episode. Stateful framework SDKs cannot leak history.
        cell = build_semantic_cell(provider, framework, model=model)
        certification_tool = (
            "record_semantic_judgment"
            if supports_model_generation(provider)
            else "score_semantics"
        )
        report = toolkit.Evaluator().evaluate(
            cell.executable,
            [declared],
            judge=cell.judge,
            rubric=toolkit.JudgeRubric(
                threshold=0.8,
                certification_tool=certification_tool,
            ),
            mode="eval",
            environment_kwargs={
                "name": f"semantic-{provider}-{framework}-{declared['name']}"
            },
            determinism=(
                "non_deterministic"
                if supports_model_generation(provider)
                else "deterministic"
            ),
            seed=0,
            reproducibility_conditions=[
                "same canonical .env",
                "same provider model",
                "same wheel and commit",
            ],
        )
        reports.append(report)
        eval_case = report.cases[0]
        result = RunResult.model_validate(eval_case.result)
        judge_execution = getattr(cell.judge, "last_result", None)
        name = str(declared["name"])
        lineage = result.lineage(
            name=f"{provider}-{framework}-{name}",
            goal="Verify Environment → System → Orchestrator → Specialist → Skill.",
        )
        human = _human(result, provider, framework, name)
        review = _review(
            result, eval_case, declared, provider, framework, human, lineage
        )
        episodes.append(
            {
                "name": name,
                "ok": bool(eval_case.ok and review["ok"]),
                "environment_episode": {
                    "name": f"semantic-{provider}-{framework}-{name}",
                    "entity": "AgenticEnvironment",
                },
                "candidate": result.normalized(),
                "deterministic_validation": eval_case.deterministic_validation,
                "judge": eval_case.judge.to_dict() if eval_case.judge else None,
                "judge_execution": (
                    judge_execution.normalized()
                    if isinstance(judge_execution, RunResult)
                    else None
                ),
                "candidate_usage": eval_case.candidate_usage,
                "judge_usage": eval_case.judge_usage,
                "usage": eval_case.usage,
                "human_result": human,
                "lineage": lineage.model_dump(mode="json"),
                "semantic_review": review,
            }
        )

    passed = sum(bool(episode["ok"]) for episode in episodes)
    reproducibility = reports[0].reproducibility.model_dump(mode="json")
    return {
        "provider": provider,
        "framework": framework,
        "model": model,
        "control_kind": (
            "live-language-model"
            if supports_model_generation(provider)
            else "deterministic-control"
        ),
        "ok": passed == len(episodes),
        "eval_report": {
            "schema_version": "agentic_systems.eval-report.v2",
            "ok": passed == len(episodes),
            "total": len(episodes),
            "passed": passed,
            "failed": len(episodes) - passed,
            "pass_rate": passed / len(episodes),
            "reproducibility": reproducibility,
        },
        "episodes": episodes,
    }


def _review_markdown(evidence: dict[str, Any]) -> str:
    summary = evidence["summary"]
    lines = [
        "# Agentic Systems 2.1 — Semantic E2E review",
        "",
        f"- Commit: §{evidence['commit_sha']}§",
        f"- Wheel: §{evidence['wheel_filename']}§",
        f"- SHA256: §{evidence['wheel_sha256']}§",
        f"- Cells: {summary['passed']}/{summary['total']} passed",
        f"- Episodes: {summary['episodes_passed']}/{summary['episodes_total']} passed",
        "",
        "Each section contains the actual public human_result, lineage, and both verdicts.",
        "",
    ]
    for cell in evidence["cells"]:
        lines += [
            f"## {cell['provider']} × {cell['framework']}",
            "",
            f"Cell status: **{'PASS' if cell['ok'] else 'FAIL'}**",
            "",
        ]
        for episode in cell.get("episodes", []):
            review = episode["semantic_review"]
            judge = episode.get("judge") or {}
            lines += [
                f"### {episode['name']}",
                "",
                f"Episode status: **{'PASS' if episode['ok'] else 'FAIL'}**",
                "",
                "#### Public human_result",
                "",
                "§§§text",
                episode["human_result"],
                "§§§",
                "",
                "#### Hierarchical lineage",
                "",
            ]
            lines += [
                f"- §{step['kind']}§ {step['title']}: {step['summary']}"
                for step in episode["lineage"]["steps"]
            ]
            lines += [
                "",
                "#### Gate evidence",
                "",
                f"- Agents: §{json.dumps(review['agent_path'], ensure_ascii=False)}§",
                f"- Tools: §{json.dumps(review['tool_path'], ensure_ascii=False)}§",
                f"- Deterministic validation: §{bool((episode.get('deterministic_validation') or {}).get('ok'))}§",
                f"- Judge: §{bool(judge.get('ok'))}§",
                f"- Judge criteria: §{json.dumps(judge.get('criteria', {}), sort_keys=True)}§",
                f"- Candidate usage: §{json.dumps(episode.get('candidate_usage', {}), sort_keys=True)}§",
                f"- Judge usage: §{json.dumps(episode.get('judge_usage', {}), sort_keys=True)}§",
            ]
            if review["failures"]:
                lines += [
                    "- Review failures:",
                    *[f"  - {item}" for item in review["failures"]],
                ]
            lines.append("")
    return "\n".join(lines).replace("§", chr(96)).rstrip() + "\n"


def _run_from_wheel(argv: list[str], wheel: Path) -> int:
    """Re-execute with the exact wheel installed in an isolated import root."""

    with tempfile.TemporaryDirectory(prefix="agentic-systems-semantic-") as temporary:
        target = Path(temporary) / "site-packages"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--force-reinstall",
                "--no-deps",
                "--target",
                str(target),
                str(wheel),
            ],
            check=True,
            cwd=ROOT,
        )
        child_environment = dict(os.environ)
        child_environment["PYTHONPATH"] = str(target)
        child_environment["AGENTIC_SYSTEMS_WHEEL_TARGET"] = str(target)
        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                *argv,
                "--wheel-runtime-ready",
            ],
            cwd=ROOT,
            env=child_environment,
        )
        return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--commit")
    parser.add_argument("--env", type=Path, default=ROOT / ".env")
    parser.add_argument("--providers", nargs="+", choices=PROVIDERS)
    parser.add_argument("--frameworks", nargs="+", choices=FRAMEWORKS)
    parser.add_argument(
        "--wheel-runtime-ready", action="store_true", help=argparse.SUPPRESS
    )
    args = parser.parse_args()

    dotenv = args.env.resolve()
    _load_canonical_dotenv(dotenv)
    providers = tuple(args.providers or PROVIDERS)
    frameworks = tuple(args.frameworks or FRAMEWORKS)
    wheel = args.wheel.resolve()
    if not wheel.exists():
        raise FileNotFoundError(wheel)
    if not args.wheel_runtime_ready:
        return _run_from_wheel(sys.argv[1:], wheel)
    package_file = Path(toolkit.__file__).resolve()
    target_value = os.getenv("AGENTIC_SYSTEMS_WHEEL_TARGET")
    target = Path(target_value).resolve() if target_value else None
    if target is None or target not in package_file.parents:
        raise RuntimeError(
            f"semantic runner did not import the certified wheel: {package_file}"
        )

    cells: list[dict[str, Any]] = []
    for provider in providers:
        for framework in frameworks:
            print(f"[semantic] {provider} × {framework}", flush=True)
            try:
                cell = _run_cell(provider, framework)
            except Exception as exc:  # noqa: BLE001 - boundary failure is evidence.
                cell = {
                    "provider": provider,
                    "framework": framework,
                    "model": _model(provider),
                    "ok": False,
                    "episodes": [],
                    "bootstrap_error": {
                        "type": type(exc).__name__,
                        "message": redact_sensitive_text(str(exc)),
                    },
                }
            cells.append(cell)
            print(
                f"[semantic] ok={cell['ok']} episodes={len(cell['episodes'])}",
                flush=True,
            )
            for episode in cell.get("episodes", []):
                if episode.get("ok"):
                    continue
                failures = episode.get("semantic_review", {}).get("failures", [])
                print(
                    f"[semantic] FAIL {provider} × {framework} × "
                    f"{episode.get('name')}: " + "; ".join(map(str, failures)),
                    flush=True,
                )
            if cell.get("bootstrap_error"):
                error = cell["bootstrap_error"]
                print(
                    f"[semantic] BOOTSTRAP {provider} × {framework}: "
                    f"{error.get('type')}: {error.get('message')}",
                    flush=True,
                )

    episode_rows = [episode for cell in cells for episode in cell.get("episodes", [])]
    passed_cells = sum(bool(cell["ok"]) for cell in cells)
    passed_episodes = sum(bool(episode["ok"]) for episode in episode_rows)
    evidence = _safe(
        {
            "schema_version": "agentic_systems.semantic-attestation.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "commit_sha": args.commit or _commit(),
            "wheel_filename": wheel.name,
            "wheel_sha256": _sha256(wheel),
            "package_version": toolkit.__version__,
            "runtime_package_file": str(package_file),
            "wheel_runtime_verified": True,
            "gate_assets": {
                "runner": {
                    "filename": Path(__file__).name,
                    "sha256": _sha256(Path(__file__).resolve()),
                },
                "application": {
                    "filename": SEMANTIC_APPLICATION_PATH.name,
                    "sha256": _sha256(SEMANTIC_APPLICATION_PATH),
                },
            },
            "environment": _environment(dotenv, providers),
            "matrix": {"providers": list(providers), "frameworks": list(frameworks)},
            "summary": {
                "total": len(cells),
                "passed": passed_cells,
                "failed": len(cells) - passed_cells,
                "episodes_total": len(episode_rows),
                "episodes_passed": passed_episodes,
                "episodes_failed": len(episode_rows) - passed_episodes,
            },
            "cells": cells,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.review.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.review.write_text(_review_markdown(evidence), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "review": str(args.review.resolve()),
                "failed": evidence["summary"]["failed"],
                "episodes_failed": evidence["summary"]["episodes_failed"],
            }
        ),
        flush=True,
    )
    return 0 if not evidence["summary"]["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
