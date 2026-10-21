"""Frozen exact-wheel acceptance: canonical semantics plus failure preservation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter
import zipfile

import agentic_systems as toolkit
from agentic_systems.errors import redact_sensitive_text

from live_release_budget import ReleaseBudget
import run_semantic_matrix as semantic


PROVIDERS = ("python-runtime", "openai-runtime", "bedrock-runtime", "ollama-runtime")
FRAMEWORKS = ("native", "langgraph", "openai-agents", "strands")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def routes_from_environment() -> dict[str, dict]:
    routes = {}
    # Conservative ceilings above published standard prices for the configured
    # models. Unknown models fail before inference rather than inheriting rates.
    allowed = {
        "openai-runtime": {"gpt-4.1-mini": (1, 4)},
        "bedrock-runtime": {"qwen.qwen3-32b-v1:0": (1, 4)},
        "ollama-runtime": {"qwen3.5:397b-cloud": (1, 5)},
    }
    for provider in PROVIDERS[1:]:
        runtime = toolkit.runtime(provider=provider)
        model = str(runtime.model_id)
        if model not in allowed[provider]:
            raise ValueError(
                f"Budget has no reviewed price ceiling for {provider}/{model}"
            )
        endpoint = {
            "openai-runtime": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "bedrock-runtime": f"https://bedrock-runtime.{runtime.region_name}.amazonaws.com",
            "ollama-runtime": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
        }[provider]
        input_rate, output_rate = allowed[provider][model]
        routes[provider] = {
            "model": model,
            "endpoint": endpoint,
            "input_usd_per_million": input_rate,
            "output_usd_per_million": output_rate,
        }
    return routes


def verify_installed_wheel(wheel: Path):
    package = Path(toolkit.__file__).resolve().parent
    if "site-packages" not in package.parts:
        raise ValueError("Acceptance requires a non-editable installed wheel")
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith("agentic_systems/") and not name.endswith("/"):
                if (package.parent / name).read_bytes() != archive.read(name):
                    raise ValueError("Installed runtime differs from candidate wheel")
    if toolkit.__version__ != importlib.metadata.version("agentic-systems"):
        raise ValueError("Installed metadata and runtime versions differ")


def failure_case(provider: str, framework: str) -> dict:
    observed = []

    @toolkit.tool
    def controlled_failure(message: str = "release") -> dict:
        """Raise the controlled release test error."""
        observed.append({"message": message})
        raise RuntimeError("release-controlled-failure")

    runtime = toolkit.runtime(
        provider=provider,
        scheduler=toolkit.scheduler(
            timeout_s=120, max_retries=0, max_turns=3, max_tool_calls=1
        ),
    )
    system = toolkit.system(runtime=runtime)
    agent = system.agent(
        name="failure_control",
        framework=framework,
        tools=[controlled_failure],
        instructions="Call controlled_failure exactly once with message release.",
        policy=toolkit.RunPolicy(
            max_tokens=512,
            max_turns=3,
            max_tool_calls=1,
            repair=False,
            temperature=0,
            tool_choice="controlled_failure",
        ),
        contract=toolkit.AgentContract(
            must_call=["controlled_failure"], completion="when_required_tools_satisfied"
        ),
    )
    system.inspect().raise_if_errors()
    request = (
        {"tool": "controlled_failure", "input": {"message": "release"}}
        if provider == "python-runtime"
        else "Call controlled_failure now."
    )
    result = system.compile(entrypoint=agent).run(request)
    events = [event for node in result.walk() for event in node.tool_events]
    failures = []
    if observed != [{"message": "release"}]:
        failures.append("independent failure Tool observation missing or repeated")
    if result.ok or not any(node.errors for node in result.walk()):
        failures.append("controlled failure was not preserved")
    if not any(event.name == "controlled_failure" and not event.ok for event in events):
        failures.append("failed Tool event missing")
    if (
        toolkit.RunResult.model_validate_json(result.model_dump_json()).normalized()
        != result.normalized()
    ):
        failures.append("result serialization changed evidence")
    return {
        "ok": not failures,
        "failures": failures,
        "observed": observed,
        "candidate": result.normalized(),
        "lineage": result.lineage().model_dump(mode="json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--env", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--provider", choices=PROVIDERS, required=True)
    parser.add_argument("--framework", choices=FRAMEWORKS, required=True)
    parser.add_argument("--phase", choices=("pilot", "acceptance"), required=True)
    parser.add_argument("--repetition", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    semantic._load_canonical_dotenv(args.env.resolve())
    os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["AWS_EC2_METADATA_DISABLED"] = "true"
    verify_installed_wheel(args.wheel)
    routes = routes_from_environment()
    args.directory.mkdir(parents=True, exist_ok=True)
    name = f"{args.phase}-{args.provider}-{args.framework}-{args.repetition}"
    output = args.directory / f"{name}.json"
    # Exclusive claim prevents replacing evidence or overlapping the same cell.
    with (args.directory / f"{name}.claim").open("x", encoding="utf-8") as stream:
        stream.write("claimed\n")
    budget = ReleaseBudget(args.directory / "requests.json", routes, name)
    budget.install()
    started = perf_counter()
    row = {
        "schema_version": "agentic_systems.core-acceptance.v1",
        "phase": args.phase,
        "repetition": args.repetition,
        "provider": args.provider,
        "framework": args.framework,
        "package_version": toolkit.__version__,
        "wheel_sha256": sha256(args.wheel),
        "commit_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
        ).strip(),
        "wheel_runtime_verified": True,
        "routes": routes,
        "gate_assets": {
            p.name: sha256(p)
            for p in (
                Path(__file__),
                Path(semantic.__file__),
                semantic.SEMANTIC_APPLICATION_PATH,
                Path(__file__).with_name("live_release_budget.py"),
            )
        },
    }
    try:
        if args.phase == "pilot":
            runtime = toolkit.runtime(
                provider=args.provider,
                scheduler=toolkit.scheduler(timeout_s=120, max_retries=0, max_turns=2),
            )
            agent = toolkit.agent(
                name="release_pilot",
                instructions="Reply exactly READY.",
                runtime=runtime,
                framework=args.framework,
                policy=toolkit.RunPolicy(max_tokens=512, repair=False),
            )
            result = agent.run("Reply exactly READY.")
            row.update(
                ok=result.ok and result.text.strip() == "READY",
                candidate=result.normalized(),
            )
        else:
            row["semantic"] = semantic._run_cell(args.provider, args.framework)
            row["failure_control"] = failure_case(args.provider, args.framework)
            row["ok"] = row["semantic"]["ok"] and row["failure_control"]["ok"]
    except Exception as exc:
        row.update(
            ok=False,
            error={
                "type": type(exc).__name__,
                "message": redact_sensitive_text(str(exc)),
            },
        )
    row["elapsed_s"] = perf_counter() - started
    with output.open("x", encoding="utf-8") as stream:
        json.dump(semantic._safe(row), stream, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {"output": str(output), "ok": row["ok"], "elapsed_s": row["elapsed_s"]}
        ),
        flush=True,
    )
    return 0 if row["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
