"""Run protected provider/framework contracts and emit release evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib import metadata
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
from typing import Any

from agentic_systems.contracts import AgentContract, RunPolicy
from agentic_systems.factories import (
    runtime as build_runtime,
    scheduler as build_scheduler,
    system as build_system,
)
from agentic_systems.errors import redact_sensitive_text
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
from agentic_systems.schemas.base import JsonValue
from agentic_systems.results import RunResult
from agentic_systems.tools.decorators import tool


ROOT = Path(__file__).resolve().parents[1]
LIVE_PROFILES = ROOT / "quality" / "live-profiles.json"


@tool(name="multiply", description="Multiply two integers.")
def quality_multiply(a: int, b: int) -> dict[str, int]:
    return {"result": a * b}


@tool(name="fail", description="Raise a controlled test error.")
def quality_fail(message: str = "controlled") -> dict[str, str]:
    raise RuntimeError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _live_environment() -> dict[str, JsonValue]:
    """Collect non-secret runtime identity directly from the live process."""

    cuda_version = os.getenv("CUDA_VERSION")
    gpu_name = os.getenv("GPU_NAME")
    try:
        import torch

        if not cuda_version:
            cuda_version = str(torch.version.cuda or "") or None
        if not gpu_name and torch.cuda.is_available():
            gpu_name = str(torch.cuda.get_device_name(0)) or None
    except Exception:  # noqa: BLE001 - optional environment evidence only.
        pass

    vllm_version = os.getenv("VLLM_VERSION")
    if not vllm_version:
        try:
            vllm_version = metadata.version("vllm")
        except metadata.PackageNotFoundError:
            vllm_version = None

    return {
        "platform": platform.platform(),
        "cuda": cuda_version,
        "gpu": gpu_name,
        "vllm": vllm_version,
    }


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


def _safe_errors(result: RunResult) -> tuple[dict[str, Any], ...]:
    safe: list[dict[str, Any]] = []
    for error in result.errors:
        safe.append(
            {
                "code": str(error.get("code") or "execution_error"),
                "category": str(error.get("category") or "execution"),
                "retryable": bool(error.get("retryable", False)),
                "validation_code": error.get("validation_code"),
                "path": error.get("path"),
                "message": redact_sensitive_text(error.get("message") or "")[:1000],
            }
        )
    return tuple(safe)


def _evidence(
    name: str,
    result: RunResult,
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
            "framework_adapter": result.meta.get("framework_adapter"),
            "fallback_provider": result.meta.get("fallback_provider"),
            "tool_names": [event.name for event in result.tool_events],
            "error_codes": [
                str(error.get("code") or "execution_error") for error in result.errors
            ],
            "tool_event_count": len(result.tool_events),
            "round_trip": RunResult.model_validate_json(
                result.model_dump_json()
            ).normalized()
            == result.normalized(),
        },
    )


def _run_case(provider: str, framework: str) -> LiveMatrixCase:
    contract = matrix_contract(provider, framework)
    model_generation = provider_capability(provider, "model_generation")
    expects_model_generation = model_generation.status != "unsupported"
    live_temperature = float(os.getenv("AGENTIC_SYSTEMS_LIVE_TEMPERATURE", "0.0"))
    runtime_config = build_runtime(
        provider=provider,
        model=_model(provider),
        scheduler=build_scheduler(
            timeout_s=90,
            max_retries=1,
            max_turns=4,
            max_tool_calls=2,
        ),
    )
    # Keep the release gate 1:1 with the public provider tutorial: one explicit
    # system owns the runtime and creates every agent. The framework is the
    # only variable across matrix cases.
    agentic_system = build_system(runtime=runtime_config)
    completion_agent = agentic_system.agent(
        name=f"quality-completion-{provider}-{framework}",
        instructions="Return a concise public answer. Do not call tools.",
        framework=framework,
    )
    tool_agent = agentic_system.agent(
        name=f"quality-tool-{provider}-{framework}",
        instructions="Use multiply to calculate 17 times 19. Return only the result.",
        tools=[quality_multiply],
        framework=framework,
        contract=AgentContract(
            must_call=["multiply"],
            completion="when_required_tools_satisfied",
        ),
        policy=RunPolicy(
            tool_choice="multiply", max_tokens=512, temperature=live_temperature
        ),
    )
    failure_agent = agentic_system.agent(
        name=f"quality-error-{provider}-{framework}",
        instructions=(
            "Call fail exactly once. Its arguments must be the JSON object "
            '{"message": "controlled"}. Do not write text before the tool call.'
        ),
        tools=[quality_fail],
        framework=framework,
        contract=AgentContract(
            must_call=["fail"],
            completion="when_required_tools_satisfied",
        ),
        policy=RunPolicy(
            tool_choice="fail",
            max_tokens=512,
            temperature=live_temperature,
            repair=False,
        ),
    )

    inspection = agentic_system.inspect().to_dict()
    inspect_ok = bool(inspection.get("ok", True))
    if provider == "python-runtime":
        completion_input: Any = {"value": "LIVE_COMPLETION_OK"}
        tool_input: Any = {
            "tool": "multiply",
            "input": {"a": 17, "b": 19},
        }
        failure_input: Any = {
            "tool": "fail",
            "input": {"message": "controlled"},
        }
    else:
        completion_input = (
            "Reply with a concise confirmation containing LIVE_COMPLETION_OK."
        )
        tool_input = "How much is 17 times 19? Use multiply and return only the result."
        failure_input = (
            'Invoke fail now with {"message": "controlled"}. Return no text '
            "before the tool call."
        )

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
            ok=(
                not failure.ok
                and bool(failure.errors)
                and any(event.name == "fail" for event in failure.tool_events)
            ),
            invariant_issues=tuple(
                issue.code for issue in failure.check_invariants().issues
            ),
            details={
                "error_count": len(failure.errors),
                "engine": failure.engine,
                "model": failure.model,
                "framework_adapter": failure.meta.get("framework_adapter"),
                "fallback_provider": failure.meta.get("fallback_provider"),
                "tool_names": [event.name for event in failure.tool_events],
                "error_codes": [
                    str(error.get("code") or "execution_error")
                    for error in failure.errors
                ],
            },
        ),
        LiveScenarioEvidence(
            name="run_result_round_trip",
            ok=all(
                RunResult.model_validate_json(item.model_dump_json()).normalized()
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
            if not case.ok:
                print(
                    "[live] failed-case=" + case.model_dump_json(exclude_none=True),
                    flush=True,
                )

    evidence = LiveAttestation(
        created_at=datetime.now(timezone.utc),
        commit_sha=args.commit or _commit(),
        wheel_sha256=_sha256(wheel),
        wheel_filename=wheel.name,
        python_version=platform.python_version(),
        environment=_live_environment(),
        cases=tuple(cases),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(evidence.model_dump_json(indent=2), encoding="utf-8")
    failed = [case for case in cases if not case.ok]
    print(json.dumps({"output": str(args.output.resolve()), "failed": len(failed)}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
