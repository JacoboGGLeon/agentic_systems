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

from . import __version__
from .api import ADVANCED_API, PUBLIC_API, RECOMMENDED_API
from .core.runtime import _load_dotenv
from .factories import runtime
from .engines.names import supported_engine_names


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
    return {
        "package": "agentic-systems",
        "version": __version__,
        "python": platform.python_version(),
        "supported_engines": supported_engine_names(),
        "dotenv_loaded": dotenv_loaded,
        "environment": {
            "has_vllm_base_url": bool(os.getenv("VLLM_BASE_URL")),
            "has_openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
            "has_aws_region": bool(os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")),
            "has_aws_profile": bool(os.getenv("AWS_PROFILE")),
        },
        "optional_dependencies": {
            "boto3": _optional_dependency("boto3"),
            "langgraph": _optional_dependency("langgraph"),
            "openai": _optional_dependency("openai"),
        },
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
    env_table.add_row("AWS region", _status(env["has_aws_region"]))
    env_table.add_row("AWS profile", _status(env["has_aws_profile"]))

    deps_table = Table(title="Optional Dependencies", box=None, show_header=False, padding=(0, 1))
    deps_table.add_column("Package", style="bold")
    deps_table.add_column("Status")
    for name, available in deps.items():
        deps_table.add_row(name, _availability(available))

    # Keep plain key/value lines inside the rich output so existing smoke tests
    # and human copy/paste diagnostics stay stable.
    compatibility_lines = "\n".join([
        f"VLLM_BASE_URL: {_status(env['has_vllm_base_url'])}",
        f"OPENAI_API_KEY: {_status(env['has_openai_api_key'])}",
        f"AWS region: {_status(env['has_aws_region'])}",
        f"AWS profile: {_status(env['has_aws_profile'])}",
        *[f"{name}: {_availability(available)}" for name, available in deps.items()],
    ])

    console.print(Columns([env_table, deps_table], equal=True, expand=True))
    console.print(Panel(compatibility_lines, title="Copy/Paste Summary", border_style="green"))
    return 0


def _cmd_runtime(args: argparse.Namespace) -> int:
    _load_dotenv()
    config = runtime(provider=args.provider, model=args.model, region=args.region)
    payload = config.describe()
    if args.json:
        _write_json(payload)
        return 0

    console = _console()
    summary = Table(title="Runtime Resolution", box=None, show_header=False, padding=(0, 1))
    summary.add_column("Field", style="bold")
    summary.add_column("Value")
    for key in ("selected_provider", "mode", "preferred_provider", "fallback_provider", "reason", "model", "region"):
        summary.add_row(key, str(payload.get(key)))

    scheduler_table = Table(title="Scheduler", box=None, show_header=False, padding=(0, 1))
    scheduler_table.add_column("Limit", style="bold")
    scheduler_table.add_column("Value")
    for key, value in (payload.get("scheduler") or {}).items():
        scheduler_table.add_row(str(key), str(value))

    console.print(Panel("agentic-systems runtime", title="Agentic Systems", border_style="cyan"))
    console.print(Columns([summary, scheduler_table], equal=True, expand=True))
    configuration = payload.get("configuration") or {}
    if configuration:
        console.print(Panel(json.dumps(configuration, indent=2, sort_keys=True), title="Safe Configuration", border_style="green"))
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


def _api_symbols(tier: str) -> list[str]:
    tiers = {
        "recommended": RECOMMENDED_API,
        "advanced": ADVANCED_API,
        "public": PUBLIC_API,
    }
    return list(tiers[tier])


def _cmd_api(args: argparse.Namespace) -> int:
    names = _api_symbols(args.tier)
    if args.contains:
        needle = args.contains.lower()
        names = [name for name in names if needle in name.lower()]

    payload = {
        "tier": args.tier,
        "count": len(names),
        "symbols": names,
    }
    if args.json:
        _write_json(payload)
        return 0

    console = _console()
    console.print(Panel(f"tier: {payload['tier']}\ncount: {payload['count']}", title="API Inventory", border_style="magenta"))
    console.print(Columns([Text(name, style="cyan") for name in names], equal=True, expand=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentic-systems", description="Agentic Systems diagnostics and package utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    version_parser = subparsers.add_parser("version", help="Print the installed Agentic Systems version.")
    version_parser.set_defaults(func=_cmd_version)

    contact_parser = subparsers.add_parser("contact", help="Print Agentic Systems author and project contact information.")
    contact_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    contact_parser.set_defaults(func=_cmd_contact)

    doctor_parser = subparsers.add_parser("doctor", help="Inspect local package health and optional dependencies.")
    doctor_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    doctor_parser.set_defaults(func=_cmd_doctor)

    runtime_parser = subparsers.add_parser("runtime", help="Describe a RuntimeConfig without executing a model.")
    runtime_parser.add_argument("--provider", default="auto", help="Runtime provider, for example auto, python-runtime, vllm-runtime, bedrock-runtime or openai-runtime.")
    runtime_parser.add_argument("--model", default=None, help="Optional model identifier.")
    runtime_parser.add_argument("--region", default=None, help="Optional provider region.")
    runtime_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    runtime_parser.set_defaults(func=_cmd_runtime)

    api_parser = subparsers.add_parser("public-api", help="List the documented public API symbols.")
    api_parser.add_argument("--all", action="store_true", help="Include advanced public symbols, not only recommended names.")
    api_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    api_parser.set_defaults(func=_cmd_public_api)

    api_inventory_parser = subparsers.add_parser("api", help="Inspect API tiers and symbols.")
    api_inventory_parser.add_argument(
        "--tier",
        choices=("recommended", "advanced", "public"),
        default="recommended",
        help="API tier to list. Use 'public' for 100 percent of PUBLIC_API.",
    )
    api_inventory_parser.add_argument("--contains", default=None, help="Filter symbols by case-insensitive substring.")
    api_inventory_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    api_inventory_parser.set_defaults(func=_cmd_api)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
