"""Command line interface for Agentic Systems."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
from typing import Any, Sequence

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .api_contract import api_contract, exercise_api
from . import __version__
from .api import PUBLIC_API, RECOMMENDED_API
from .compatibility import FRAMEWORK_NAMES, PROVIDER_NAMES
from .core.runtime import (
    _bedrock_signal_present,
    _load_dotenv,
    _ollama_signal_present,
    _openai_signal_present,
    _vllm_signal_present,
)
from .factories import model_server, runtime
from .engines.names import supported_engine_names
from .registry import FRAMEWORKS, PROVIDERS, registry_manifest


CONTACT_INFO = {
    "author": "Jacobo Gerardo González León",
    "email_1": "jacobogerardo.gonzalez@bbva.com",
    "email_2": "jacoboggleon@gmail..com",
    "linkedin": "https://www.linkedin.com/in/jacoboggleon/",
    "github_repo": "https://www.github.com/JacoboGGLeon/agentic_systems",
}


def _console() -> Console:
    return Console(highlight=False)


def _status(value: bool) -> str:
    return "set" if value else "missing"


def _availability(value: bool) -> str:
    return "available" if value else "missing"


def _optional_dependency(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _write_json(payload: dict[str, Any] | list[Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _doctor_payload() -> dict[str, Any]:
    dotenv_loaded = _load_dotenv()
    environment = {
        "has_vllm_base_url": bool(os.getenv("VLLM_BASE_URL")),
        "has_ollama_base_url": bool(os.getenv("OLLAMA_BASE_URL")),
        "has_ollama_model": bool(os.getenv("OLLAMA_MODEL")),
        "has_openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
        "has_openai_base_url": bool(os.getenv("OPENAI_BASE_URL")),
        "has_aws_region": bool(
            os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        ),
        "has_aws_profile": bool(os.getenv("AWS_PROFILE")),
        "has_aws_static_credentials": bool(
            os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")
        ),
        "has_aws_session_token": bool(os.getenv("AWS_SESSION_TOKEN")),
        "has_bedrock_api_key": bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK")),
    }
    optional_dependencies: dict[str, bool] = {
        "boto3": _optional_dependency("boto3"),
        "langgraph": _optional_dependency("langgraph"),
        "openai": _optional_dependency("openai"),
        "openai-agents": _optional_dependency("agents"),
        "strands-agents": _optional_dependency("strands"),
    }
    frameworks = [
        {
            "name": definition.name,
            "module": definition.dependency,
            "installed": definition.dependency is None
            or _optional_dependency(definition.dependency),
        }
        for definition in FRAMEWORKS
    ]
    bedrock_auth = (
        "bedrock-api-key"
        if environment["has_bedrock_api_key"]
        else "aws-credential-chain"
        if _bedrock_signal_present(None)
        else None
    )
    configured = {
        "python-runtime": True,
        "openai-runtime": _openai_signal_present(),
        "vllm-runtime": _vllm_signal_present(),
        "ollama-runtime": _ollama_signal_present(),
        "bedrock-runtime": _bedrock_signal_present(None),
    }
    authentication = {
        "python-runtime": "local",
        "openai-runtime": "api-key"
        if environment["has_openai_api_key"]
        else "custom-endpoint"
        if environment["has_openai_base_url"]
        else None,
        "vllm-runtime": "openai-compatible-endpoint",
        "ollama-runtime": "local-openai-compatible-endpoint",
        "bedrock-runtime": bedrock_auth,
    }
    providers = [
        {
            "name": definition.name,
            "configured": configured[definition.name],
            "dependency_installed": definition.dependency is None
            or _optional_dependency(definition.dependency),
            "authentication": authentication[definition.name],
        }
        for definition in PROVIDERS
    ]
    for provider in providers:
        provider["ready"] = bool(
            provider["configured"] and provider["dependency_installed"]
        )
        provider["status"] = (
            "ready-to-attempt"
            if provider["ready"]
            else "missing-dependency"
            if not provider["dependency_installed"]
            else "needs-configuration"
        )
    return {
        "package": "agentic-systems",
        "version": __version__,
        "python": platform.python_version(),
        "supported_engines": supported_engine_names(),
        "dotenv_loaded": dotenv_loaded,
        "readiness_semantics": (
            "ready means configuration signals plus dependencies are present; "
            "only a live command verifies credentials, permissions, endpoint and model"
        ),
        "environment": environment,
        "optional_dependencies": optional_dependencies,
        "providers": providers,
        "frameworks": frameworks,
        "contract_registry": registry_manifest(),
    }


def _cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return 0


def _cmd_contact(args: argparse.Namespace) -> int:
    payload = dict(CONTACT_INFO)
    if args.json:
        _write_json(payload)
        return 0

    console = _console()
    table = Table(title="Contact", box=None, show_header=False, padding=(0, 1))
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Author", payload["author"])
    table.add_row("E-Mail 1", payload["email_1"])
    table.add_row("E-Mail 2", payload["email_2"])
    table.add_row("LinkedIn", payload["linkedin"])
    table.add_row("Github Repo", payload["github_repo"])
    console.print(Panel(table, title="Agentic Systems", border_style="cyan"))
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    payload = _doctor_payload()
    if args.json:
        _write_json(payload)
        return 0

    console = _console()
    env = payload["environment"]
    deps = payload["optional_dependencies"]
    providers = payload["providers"]
    frameworks = payload["frameworks"]

    summary = Text()
    summary.append(f"Agentic Systems {payload['version']}\n", style="bold cyan")
    summary.append(f"Python: {payload['python']}\n")
    summary.append(f"Engines: {', '.join(payload['supported_engines'])}\n")
    summary.append(f".env loaded: {payload['dotenv_loaded']}")
    console.print(Panel(summary, title="Agentic Systems Doctor", border_style="cyan"))

    env_table = Table(title="Environment", box=None, show_header=False, padding=(0, 1))
    env_table.add_column("Signal", style="bold")
    env_table.add_column("Status")
    env_table.add_row("VLLM_BASE_URL", _status(env["has_vllm_base_url"]))
    env_table.add_row("OPENAI_API_KEY", _status(env["has_openai_api_key"]))
    env_table.add_row("OLLAMA_BASE_URL", _status(env["has_ollama_base_url"]))
    env_table.add_row("OLLAMA_MODEL", _status(env["has_ollama_model"]))
    env_table.add_row("AWS region", _status(env["has_aws_region"]))
    env_table.add_row("AWS profile", _status(env["has_aws_profile"]))
    env_table.add_row("Bedrock API key", _status(env["has_bedrock_api_key"]))

    deps_table = Table(
        title="Optional Dependencies", box=None, show_header=False, padding=(0, 1)
    )
    deps_table.add_column("Package", style="bold")
    deps_table.add_column("Status")
    for name, available in deps.items():
        deps_table.add_row(name, _availability(available))

    providers_table = Table(title="Providers", box=None, padding=(0, 1))
    providers_table.add_column("Provider", style="bold")
    providers_table.add_column("Config")
    providers_table.add_column("Dependency")
    providers_table.add_column("Ready")
    providers_table.add_column("Authentication")
    for provider in providers:
        providers_table.add_row(
            provider["name"],
            _status(provider["configured"]),
            _availability(provider["dependency_installed"]),
            "yes" if provider["ready"] else "no",
            provider["authentication"] or "-",
        )

    frameworks_table = Table(title="Frameworks", box=None, padding=(0, 1))
    frameworks_table.add_column("Framework", style="bold")
    frameworks_table.add_column("Module")
    frameworks_table.add_column("Installed")
    for framework in frameworks:
        frameworks_table.add_row(
            framework["name"],
            framework["module"] or "built-in",
            "yes" if framework["installed"] else "no",
        )

    # Keep plain key/value lines inside the rich output so existing smoke tests
    # and human copy/paste diagnostics stay stable.
    compatibility_lines = "\n".join(
        [
            f"VLLM_BASE_URL: {_status(env['has_vllm_base_url'])}",
            f"OPENAI_API_KEY: {_status(env['has_openai_api_key'])}",
            f"OLLAMA_BASE_URL: {_status(env['has_ollama_base_url'])}",
            f"OLLAMA_MODEL: {_status(env['has_ollama_model'])}",
            f"AWS region: {_status(env['has_aws_region'])}",
            f"AWS profile: {_status(env['has_aws_profile'])}",
            f"Bedrock auth: {next(row['authentication'] or 'missing' for row in providers if row['name'] == 'bedrock-runtime')}",
            *[
                f"{name}: {_availability(available)}"
                for name, available in deps.items()
            ],
            *[f"{row['name']}: {row['status']}" for row in providers],
            *[
                f"{row['name']}: {'installed' if row['installed'] else 'missing'}"
                for row in frameworks
            ],
        ]
    )

    console.print(Columns([env_table, deps_table], equal=True, expand=True))
    console.print(Columns([providers_table, frameworks_table], equal=True, expand=True))
    console.print(
        Panel(compatibility_lines, title="Copy/Paste Summary", border_style="green")
    )
    return 0


def _cmd_runtime(args: argparse.Namespace) -> int:
    _load_dotenv()
    config = runtime(
        provider=args.provider,
        model=args.model,
        region=args.region,
        provider_priority=args.provider_priority,
        allow_python_fallback=args.allow_python_fallback,
    )
    payload = config.describe()
    if args.json:
        _write_json(payload)
        return 0

    console = _console()
    summary = Table(
        title="Runtime Resolution", box=None, show_header=False, padding=(0, 1)
    )
    summary.add_column("Field", style="bold")
    summary.add_column("Value")
    for key in (
        "selected_provider",
        "mode",
        "preferred_provider",
        "fallback_provider",
        "provider_priority",
        "reason",
        "model",
        "region",
    ):
        summary.add_row(key, str(payload.get(key)))

    scheduler_table = Table(
        title="Scheduler", box=None, show_header=False, padding=(0, 1)
    )
    scheduler_table.add_column("Limit", style="bold")
    scheduler_table.add_column("Value")
    for key, value in (payload.get("scheduler") or {}).items():
        scheduler_table.add_row(str(key), str(value))

    console.print(
        Panel("agentic-systems runtime", title="Agentic Systems", border_style="cyan")
    )
    console.print(Columns([summary, scheduler_table], equal=True, expand=True))
    configuration = payload.get("configuration") or {}
    if configuration:
        console.print(
            Panel(
                json.dumps(configuration, indent=2, sort_keys=True),
                title="Safe Configuration",
                border_style="green",
            )
        )
    return 0


def _cmd_model_server(args: argparse.Namespace) -> int:
    server = model_server(
        args.model,
        backend="vllm",
        profile=args.profile,
        served_model_name=args.served_model_name,
        host=args.host,
        port=args.port,
        tool_call_parser=args.tool_call_parser,
        reasoning_parser=args.reasoning_parser,
        enable_auto_tool_choice=not args.disable_tool_calling,
        startup_timeout_s=args.startup_timeout,
        log_path=args.log_path,
    )
    payload = server.inspect()
    if args.json:
        _write_json(payload)
        return 0
    _console().print(
        Panel(
            json.dumps(payload, indent=2, sort_keys=True),
            title="Model Server",
            border_style="cyan",
        )
    )
    return 0


def _cmd_public_api(args: argparse.Namespace) -> int:
    names = list(PUBLIC_API if args.all else RECOMMENDED_API)
    if args.json:
        _write_json(names)
        return 0
    console = _console()
    title = "Public API" if args.all else "Recommended API"
    console.print(Panel(f"count: {len(names)}", title=title, border_style="blue"))
    for name in names:
        console.print(Text(name, style="cyan"))
    return 0


def _api_ids(tier: str) -> list[str]:
    manifest = api_contract()
    if tier == "public":
        return list(manifest["ids"])

    return [entry["id"] for entry in manifest["entries"] if entry["tier"] == tier]


def _cmd_api(args: argparse.Namespace) -> int:
    if args.api_action == "describe":
        if not args.identifier:
            raise ValueError("api describe requires an export or member id.")
        manifest = api_contract()
        entries = [
            entry for entry in manifest["entries"] if entry["id"] == args.identifier
        ]
        if not entries:
            raise KeyError(f"Unknown public API contract id {args.identifier!r}.")
        payload: dict[str, Any] = entries[0]
        title = "API Contract"
    elif args.api_action == "exercise":
        if not args.identifier and not args.all_entries:
            raise ValueError("api exercise requires an id or --all.")
        payload = exercise_api(None if args.all_entries else args.identifier)
        title = "API Exercise"
    else:
        names = _api_ids(args.tier)
        if args.contains:
            needle = args.contains.lower()
            names = [name for name in names if needle in name.lower()]
        payload = {
            "tier": args.tier,
            "count": len(names),
            "ids": names,
        }
        title = "API Inventory"

    if args.json:
        _write_json(payload)
        return 0

    console = _console()
    if args.api_action == "list":
        console.print(
            Panel(
                f"tier: {payload['tier']}\ncount: {payload['count']}",
                title=title,
                border_style="magenta",
            )
        )
        console.print(
            Columns(
                [Text(name, style="cyan") for name in payload["ids"]],
                equal=True,
                expand=True,
            )
        )
    else:
        console.print(
            Panel(
                json.dumps(payload, indent=2, sort_keys=True),
                title=title,
                border_style="magenta",
            )
        )
    return 0


def _emit_workflow(payload: dict[str, Any], *, title: str, as_json: bool) -> int:
    if as_json:
        _write_json(payload)
    else:
        _console().print(
            Panel(
                json.dumps(payload, indent=2, sort_keys=True),
                title=title,
                border_style="green",
            )
        )
    return 0


def _cli_echo(value: str) -> dict:
    """Return a deterministic CLI workflow marker."""

    return {"value": value}


def _cli_agent(
    toolkit: Any,
    *,
    provider_name: str = "python-runtime",
    framework_name: str = "native",
):
    echo = toolkit.tool(_cli_echo, name="cli_echo")
    runtime_config = toolkit.runtime(provider=provider_name)
    agent = toolkit.agent(
        name=f"cli_{provider_name}_{framework_name}",
        instructions="Execute cli_echo with the requested value.",
        tools=[echo],
        runtime=runtime_config,
        framework=toolkit.framework(framework_name),
        contract=toolkit.AgentContract(must_call=["cli_echo"]),
        policy=toolkit.RunPolicy(
            max_turns=2,
            max_tool_calls=1,
            temperature=0.0,
            strict=True,
        ),
    )
    return echo, agent


def _matrix_workflow(
    toolkit: Any,
    *,
    live: bool,
    provider: str | None = None,
    framework: str | None = None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for case in toolkit.compatibility_matrix():
        if provider is not None and case.provider != provider:
            continue
        if framework is not None and case.framework != framework:
            continue
        if case.provider != "python-runtime" and not live:
            results.append(
                {
                    **case.to_dict(),
                    "execution": "not-run",
                    "execution_reason": "Pass --live to cross an external provider boundary.",
                }
            )
            continue
        if not case.ready:
            results.append(
                {
                    **case.to_dict(),
                    "execution": "not-run",
                    "execution_reason": case.reason,
                }
            )
            continue
        try:
            _echo, agent = _cli_agent(
                toolkit,
                provider_name=case.provider,
                framework_name=case.framework,
            )
            result = agent.run(
                {"tool": "cli_echo", "input": {"value": "ok"}},
                mode="eval",
            )
            results.append(
                {
                    **case.to_dict(),
                    "execution": "passed" if result.ok else "failed",
                    "result": toolkit.run_result_output(result),
                }
            )
        except Exception as exc:
            results.append(
                {
                    **case.to_dict(),
                    "execution": "failed",
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                }
            )
    return {
        "workflow": "matrix",
        "live": live,
        "combination_count": len(results),
        "provider_filter": provider,
        "framework_filter": framework,
        "passed": sum(item["execution"] == "passed" for item in results),
        "failed": sum(item["execution"] == "failed" for item in results),
        "not_run": sum(item["execution"] == "not-run" for item in results),
        "results": results,
    }


def _workflow_payload(name: str, args: argparse.Namespace) -> dict[str, Any]:
    import agentic_systems as toolkit

    value = getattr(args, "value", "ok")
    if name == "tool":
        echo = toolkit.tool(_cli_echo, name="cli_echo")
        return {
            "workflow": name,
            "result": toolkit.run_result_output(echo.run({"value": value})),
        }
    if name == "skill":
        echo = toolkit.tool(_cli_echo, name="cli_echo")
        capability = toolkit.skill(
            name="cli_echo_skill",
            description="Deterministic CLI skill.",
            tools=[echo],
        )
        return {"workflow": name, "skill": capability.describe()}
    if name == "agent":
        _echo, agent = _cli_agent(toolkit)
        result = agent.run(
            {"tool": "cli_echo", "input": {"value": value}},
            mode="eval",
        )
        return {"workflow": name, "result": toolkit.run_result_output(result)}
    if name == "system":
        echo = toolkit.tool(_cli_echo, name="cli_echo")
        runtime_config = toolkit.runtime(provider="python-runtime")
        current = toolkit.system(runtime=runtime_config)
        current.agent(
            name="cli_system_agent",
            instructions="Execute cli_echo with the requested value.",
            tools=[echo],
            runtime=runtime_config,
            contract=toolkit.AgentContract(must_call=["cli_echo"]),
            policy=toolkit.RunPolicy(max_turns=2, max_tool_calls=1, temperature=0.0),
        )
        result = current.run({"tool": "cli_echo", "input": {"value": value}})
        return {"workflow": name, "result": toolkit.run_result_output(result)}
    if name == "graph":

        def mark(state: dict) -> dict:
            return {**state, "visited": True}

        app = toolkit.graph(
            name="cli_graph",
            engine="portable",
            state=dict,
            nodes={"mark": mark},
            edges=[("START", "mark"), ("mark", "END")],
        )
        return {"workflow": name, "state": app.run({"value": value})}
    if name == "environment":

        def transition(row: dict, action: Any, _info: dict) -> dict:
            return {"output": {"row": row, "action": action}}

        current = toolkit.environment(
            [{"value": value}],
            name="cli_environment",
            transition_fn=transition,
            reward_fn=lambda *_args: 1.0,
        )
        observation, reset_info = current.reset(seed=0)
        _next, reward, terminated, truncated, step_info = current.step(value)
        return {
            "workflow": name,
            "observation": observation,
            "reset": reset_info,
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
            "step": step_info,
            "summary": toolkit.environment_summary(current),
        }
    if name == "eval":
        _echo, agent = _cli_agent(toolkit)
        report = toolkit.eval().run(
            agent,
            [
                {
                    "name": "cli_echo",
                    "input": {"tool": "cli_echo", "input": {"value": value}},
                    "expected": {
                        "must_call": ["cli_echo"],
                        "data_contains": {"value": value},
                    },
                }
            ],
            determinism="deterministic",
            seed=0,
        )
        return {"workflow": name, "report": report.to_dict()}
    if name == "matrix":
        return _matrix_workflow(
            toolkit,
            live=bool(args.live),
            provider=args.provider,
            framework=args.framework,
        )
    raise ValueError(f"Unknown workflow {name!r}.")


def _cmd_workflow(args: argparse.Namespace) -> int:
    payload = _workflow_payload(args.workflow, args)
    scenario = next(
        item for item in api_contract()["scenarios"] if item["id"] == args.workflow
    )
    payload["scenario"] = scenario["id"]
    payload["scenario_api_ids"] = scenario["api_ids"]
    exit_code = 0
    if (
        args.workflow == "matrix"
        and getattr(args, "require_pass", False)
        and (payload["failed"] or payload["not_run"])
    ):
        exit_code = 1
    _emit_workflow(
        payload,
        title=f"{args.workflow.title()} Workflow",
        as_json=args.json,
    )
    return exit_code


def _add_workflow_parsers(subparsers: Any) -> None:
    definitions = (
        ("tool", "run", "Execute a deterministic Tool."),
        ("skill", "inspect", "Construct and inspect a Skill."),
        ("agent", "run", "Execute an Agent on python-runtime."),
        ("system", "run", "Compile and execute a System."),
        ("environment", "run", "Execute one Environment episode."),
        ("graph", "run", "Build and execute a portable Graph."),
        ("eval", "run", "Evaluate an Agent with one deterministic case."),
        ("matrix", "check", "Check or execute the Provider x Framework matrix."),
    )
    for name, action, help_text in definitions:
        current = subparsers.add_parser(name, help=help_text)
        current.add_argument("action", choices=(action,))
        if name not in {"skill", "matrix"}:
            current.add_argument("--value", default="ok")
        if name == "matrix":
            current.add_argument(
                "--live",
                action="store_true",
                help="Execute configured external Provider combinations.",
            )
            current.add_argument(
                "--require-pass",
                action="store_true",
                help="Exit non-zero unless every selected matrix row passes.",
            )
            current.add_argument(
                "--provider",
                choices=PROVIDER_NAMES,
                default=None,
                help="Filter the matrix to one Provider.",
            )
            current.add_argument(
                "--framework",
                choices=FRAMEWORK_NAMES,
                default=None,
                help="Filter the matrix to one Framework.",
            )
        current.add_argument("--json", action="store_true")
        current.set_defaults(func=_cmd_workflow, workflow=name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-systems",
        description="Agentic Systems diagnostics and package utilities.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    version_parser = subparsers.add_parser(
        "version", help="Print the installed Agentic Systems version."
    )
    version_parser.set_defaults(func=_cmd_version)

    contact_parser = subparsers.add_parser(
        "contact", help="Print Agentic Systems author and project contact information."
    )
    contact_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON."
    )
    contact_parser.set_defaults(func=_cmd_contact)

    doctor_parser = subparsers.add_parser(
        "doctor", help="Inspect local package health and optional dependencies."
    )
    doctor_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON."
    )
    doctor_parser.set_defaults(func=_cmd_doctor)

    runtime_parser = subparsers.add_parser(
        "runtime", help="Describe a RuntimeConfig without executing a model."
    )
    runtime_parser.add_argument(
        "--provider",
        default="auto",
        help="Runtime provider, for example auto, python-runtime, vllm-runtime, bedrock-runtime or openai-runtime.",
    )
    runtime_parser.add_argument(
        "--model", default=None, help="Optional model identifier."
    )
    runtime_parser.add_argument(
        "--region", default=None, help="Optional provider region."
    )
    runtime_parser.add_argument(
        "--provider-priority",
        default=None,
        help="Comma-separated auto priority, for example bedrock-runtime,openai-runtime,vllm-runtime,ollama-runtime.",
    )
    runtime_parser.add_argument(
        "--allow-python-fallback",
        action="store_true",
        help="Append python-runtime as deterministic fallback for provider=auto.",
    )
    runtime_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON."
    )
    runtime_parser.set_defaults(func=_cmd_runtime)

    server_parser = subparsers.add_parser(
        "model-server", help="Inspect an explicit local model-server declaration."
    )
    server_parser.add_argument("action", choices=("inspect",))
    server_parser.add_argument("--model", required=True)
    server_parser.add_argument(
        "--profile", choices=("fast", "medium", "power", "custom"), default="fast"
    )
    server_parser.add_argument("--served-model-name", default=None)
    server_parser.add_argument("--host", default="127.0.0.1")
    server_parser.add_argument("--port", type=int, default=8000)
    server_parser.add_argument("--tool-call-parser", default="hermes")
    server_parser.add_argument("--reasoning-parser", default=None)
    server_parser.add_argument("--disable-tool-calling", action="store_true")
    server_parser.add_argument("--startup-timeout", type=float, default=600.0)
    server_parser.add_argument("--log-path", default="vllm-server.log")
    server_parser.add_argument("--json", action="store_true")
    server_parser.set_defaults(func=_cmd_model_server)
    api_parser = subparsers.add_parser(
        "public-api", help="List the documented public API symbols."
    )
    api_parser.add_argument(
        "--all",
        action="store_true",
        help="Include advanced public symbols, not only recommended names.",
    )
    api_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON."
    )
    api_parser.set_defaults(func=_cmd_public_api)

    api_inventory_parser = subparsers.add_parser(
        "api", help="Inspect API tiers and contract IDs."
    )
    api_inventory_parser.add_argument(
        "api_action",
        nargs="?",
        choices=("list", "describe", "exercise"),
        default="list",
    )
    api_inventory_parser.add_argument("identifier", nargs="?", default=None)
    api_inventory_parser.add_argument(
        "--all",
        dest="all_entries",
        action="store_true",
        help="Exercise every public export and member.",
    )
    api_inventory_parser.add_argument(
        "--tier",
        choices=("recommended", "advanced", "public"),
        default="recommended",
        help="API tier to list. Use 'public' for all exports and public members.",
    )
    api_inventory_parser.add_argument(
        "--contains",
        default=None,
        help="Filter contract IDs by case-insensitive substring.",
    )
    api_inventory_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON."
    )
    api_inventory_parser.set_defaults(func=_cmd_api)

    _add_workflow_parsers(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
