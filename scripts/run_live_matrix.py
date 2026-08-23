"""Run protected provider/framework contracts and emit release evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
from typing import Any

import agentic_systems as toolkit
from agentic_systems.registry import (
    FRAMEWORK_NAMES,
    PROVIDER_NAMES,
    matrix_contract,
    provider_capability,
)
from agentic_systems.schemas.attestation import (
    LiveAttestation,
    LiveMatrixCase,
    LiveScenarioEvidence,
)
from agentic_systems.tools.decorators import tool


ROOT = Path(__file__).resolve().parents[1]
LIVE_PROFILES = ROOT / "quality" / "live-profiles.json"


@tool(name="quality.echo", description="Return a value unchanged.")
def quality_echo(value: str) -> dict[str, str]:
    return {"value": value}


@tool(name="quality.fail", description="Raise a controlled test error.")
def quality_fail(message: str = "controlled") -> dict[str, str]:
    raise RuntimeError(message)


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


def _model(provider: str) -> str | None:
    variable = {
        "bedrock-runtime": "BEDROCK_MODEL_ID",
        "openai-runtime": "OPENAI_MODEL",
        "ollama-runtime": "OLLAMA_MODEL",
        "vllm-runtime": "VLLM_MODEL",
    }.get(provider)
    return os.getenv(variable) if variable else None


def _safe_errors(result: toolkit.RunResult) -> tuple[dict[str, Any], ...]:
    safe: list[dict[str, Any]] = []
    for error in result.errors:
        safe.append(
            {
                "code": str(error.get("code") or "execution_error"),
                "category": str(error.get("category") or "execution"),
                "retryable": bool(error.get("retryable", False)),
            }
        )
    return tuple(safe)


def _evidence(
    name: str,
    result: toolkit.RunResult,
    *,
    expected_ok: bool = True,
) -> LiveScenarioEvidence:
    invariant_issues = tuple(
        issue.code
        for issue in result.check_invariants().issues
        if issue.severity == "error"
    )
    outcome_ok = result.ok if expected_ok else (not result.ok and bool(result.errors))
    return LiveScenarioEvidence(
        name=name,
        ok=outcome_ok and not invariant_issues,
        invariant_issues=invariant_issues,
        details={
            "execution_ok": result.ok,
            "expected_ok": expected_ok,
            "engine": result.engine,
            "model": result.model,
            "tool_event_count": len(result.tool_events),
            "round_trip": toolkit.RunResult.model_validate_json(
                result.model_dump_json()
            ).normalized()
            == result.normalized(),
        },
    )


def _run_case(provider: str, framework: str) -> LiveMatrixCase:
    contract = matrix_contract(provider, framework)
    model_generation = provider_capability(provider, "model_generation")
    expects_model_generation = model_generation.status != "unsupported"
    runtime = toolkit.runtime(
        provider=provider,
        model=_model(provider),
        scheduler=toolkit.scheduler(
            timeout_s=90,
            max_retries=1,
            max_turns=4,
            max_tool_calls=2,
        ),
    )
    completion_agent = toolkit.agent(
        name=f"quality-completion-{provider}-{framework}",
        instructions="Return a concise public answer. Do not call tools.",
        runtime=runtime,
        framework=framework,
    )
    tool_agent = toolkit.agent(
        name=f"quality-tool-{provider}-{framework}",
        instructions=(
            "Call quality.echo exactly once with value='LIVE_TOOL_OK', then answer briefly."
        ),
        tools=[quality_echo],
        runtime=runtime,
        framework=framework,
        contract=toolkit.AgentContract(must_call=["quality.echo"]),
    )
    failure_agent = toolkit.agent(
        name=f"quality-error-{provider}-{framework}",
        instructions="Call quality.fail exactly once with message='controlled'.",
        tools=[quality_fail],
        runtime=runtime,
        framework=framework,
        contract=toolkit.AgentContract(must_call=["quality.fail"]),
    )

    inspection = tool_agent.system.inspect() if tool_agent.system is not None else None
    inspect_ok = bool(inspection and inspection.get("ok", True))
    if provider == "python-runtime":
        completion_input: Any = {"value": "LIVE_COMPLETION_OK"}
        tool_input: Any = {
            "tool": "quality.echo",
            "input": {"value": "LIVE_TOOL_OK"},
        }
        failure_input: Any = {
            "tool": "quality.fail",
            "input": {"message": "controlled"},
        }
    else:
        completion_input = (
            "Reply with a concise confirmation containing LIVE_COMPLETION_OK."
        )
        tool_input = "Use the required tool now."
        failure_input = "Use the required failing tool now."

    completion = completion_agent.run(completion_input, mode="eval")
    tool_result = tool_agent.run(tool_input, mode="eval")
    failure = failure_agent.run(failure_input, mode="eval")
    scenarios = (
        LiveScenarioEvidence(
            name="inspect",
            ok=inspect_ok,
            details={"declared_provider": provider, "declared_framework": framework},
        ),
        _evidence("completion", completion, expected_ok=expects_model_generation),
        _evidence("agent", completion, expected_ok=expects_model_generation),
        _evidence("tool_calling", tool_result),
        LiveScenarioEvidence(
            name="structured_error",
            ok=(not failure.ok and bool(failure.errors)),
            invariant_issues=tuple(
                issue.code for issue in failure.check_invariants().issues
            ),
            details={"error_count": len(failure.errors)},
        ),
        LiveScenarioEvidence(
            name="run_result_round_trip",
            ok=all(
                toolkit.RunResult.model_validate_json(
                    item.model_dump_json()
                ).normalized()
                == item.normalized()
                for item in (completion, tool_result, failure)
            ),
        ),
    )
    results = (completion, tool_result, failure)
    identity_ok = all(
        item.engine == provider and item.meta.get("framework_adapter") == framework
        for item in results
    )
    model_identity_ok = not expects_model_generation or all(
        item.model for item in results
    )
    scenario_contract_ok = tuple(item.name for item in scenarios) == contract.scenarios
    no_fallback = all(not item.meta.get("fallback_provider") for item in results)
    errors = tuple(error for result in results for error in _safe_errors(result))
    return LiveMatrixCase(
        provider=provider,
        framework=framework,
        model=completion.model or tool_result.model,
        ok=(
            identity_ok
            and model_identity_ok
            and scenario_contract_ok
            and no_fallback
            and all(item.ok for item in scenarios)
        ),
        scenarios=scenarios,
        usage={
            "completion": completion.usage,
            "tool_calling": tool_result.usage,
            "structured_error": failure.usage,
        },
        errors=errors,
    )


def _load_profile(name: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    payload = json.loads(LIVE_PROFILES.read_text(encoding="utf-8"))
    profiles = payload.get("profiles", {})
    if name not in profiles:
        raise ValueError(f"Unknown live profile {name!r}; expected {tuple(profiles)}.")
    profile = profiles[name]
    providers = tuple(profile.get("providers", ()))
    frameworks = tuple(profile.get("frameworks", ()))
    unknown_providers = sorted(set(providers) - set(PROVIDER_NAMES))
    unknown_frameworks = sorted(set(frameworks) - set(FRAMEWORK_NAMES))
    if unknown_providers or unknown_frameworks:
        raise ValueError(
            "Live profile contains values outside the canonical registry: "
            f"providers={unknown_providers}, frameworks={unknown_frameworks}."
        )
    expected_pairs = {
        (item.provider, item.framework)
        for item in (
            matrix_contract(provider, framework)
            for provider in providers
            for framework in frameworks
        )
    }
    if len(expected_pairs) != len(providers) * len(frameworks):
        raise ValueError(f"Live profile {name!r} contains duplicate pairs.")
    return providers, frameworks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit")
    parser.add_argument("--providers", nargs="+", choices=PROVIDER_NAMES)
    parser.add_argument("--frameworks", nargs="+", choices=FRAMEWORK_NAMES)
    parser.add_argument("--profile")
    args = parser.parse_args()

    wheel = args.wheel.resolve()
    if args.profile and (args.providers or args.frameworks):
        parser.error("--profile cannot be combined with --providers/--frameworks")
    if args.profile:
        providers, frameworks = _load_profile(args.profile)
    else:
        providers = tuple(args.providers or PROVIDER_NAMES)
        frameworks = tuple(args.frameworks or FRAMEWORK_NAMES)
    cases: list[LiveMatrixCase] = []
    for provider in providers:
        for framework in frameworks:
            print(f"[live] {provider} × {framework}", flush=True)
            try:
                case = _run_case(provider, framework)
            except Exception as exc:  # noqa: BLE001 - evidence must capture boundary failure.
                case = LiveMatrixCase(
                    provider=provider,
                    framework=framework,
                    ok=False,
                    scenarios=(
                        LiveScenarioEvidence(
                            name="bootstrap",
                            ok=False,
                            invariant_issues=(type(exc).__name__,),
                        ),
                    ),
                    errors=({"code": type(exc).__name__},),
                )
            cases.append(case)
            print(f"[live] ok={case.ok} model={case.model or '-'}", flush=True)

    evidence = LiveAttestation(
        created_at=datetime.now(timezone.utc),
        commit_sha=args.commit or _commit(),
        wheel_sha256=_sha256(wheel),
        wheel_filename=wheel.name,
        python_version=platform.python_version(),
        environment={
            "platform": platform.platform(),
            "cuda": os.getenv("CUDA_VERSION"),
            "gpu": os.getenv("GPU_NAME"),
            "vllm": os.getenv("VLLM_VERSION"),
        },
        cases=tuple(cases),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(evidence.model_dump_json(indent=2), encoding="utf-8")
    failed = [case for case in cases if not case.ok]
    print(json.dumps({"output": str(args.output.resolve()), "failed": len(failed)}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
