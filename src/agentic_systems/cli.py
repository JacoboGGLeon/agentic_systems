"""Command line interface for Agentic Systems."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
from typing import Any, Sequence

from . import __version__
from .api import ADVANCED_API, PUBLIC_API, RECOMMENDED_API
from .core.runtime import _load_dotenv
from .factories import runtime
from .engines.names import supported_engine_names


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


def _cmd_doctor(args: argparse.Namespace) -> int:
    payload = _doctor_payload()
    if args.json:
        _write_json(payload)
        return 0

    print(f"Agentic Systems {payload['version']}")
    print(f"Python: {payload['python']}")
    print(f"Engines: {', '.join(payload['supported_engines'])}")
    print(f".env loaded: {payload['dotenv_loaded']}")
    env = payload["environment"]
    print("Environment:")
    print(f"- OPENAI_API_KEY: {'set' if env['has_openai_api_key'] else 'missing'}")
    print(f"- AWS region: {'set' if env['has_aws_region'] else 'missing'}")
    print(f"- AWS profile: {'set' if env['has_aws_profile'] else 'missing'}")
    deps = payload["optional_dependencies"]
    print("Optional dependencies:")
    for name, available in deps.items():
        status = "available" if available else "missing"
        print(f"- {name}: {status}")
    return 0


def _cmd_runtime(args: argparse.Namespace) -> int:
    _load_dotenv()
    config = runtime(provider=args.provider, model=args.model, region=args.region)
    payload = config.describe()
    if args.json:
        _write_json(payload)
        return 0
    for key, value in payload.items():
        print(f"{key}: {value}")
    return 0


def _cmd_public_api(args: argparse.Namespace) -> int:
    names = list(PUBLIC_API if args.all else RECOMMENDED_API)
    if args.json:
        _write_json(names)
        return 0
    for name in names:
        print(name)
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

    print(f"tier: {payload['tier']}")
    print(f"count: {payload['count']}")
    for name in names:
        print(name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentic-systems", description="Agentic Systems diagnostics and package utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    version_parser = subparsers.add_parser("version", help="Print the installed Agentic Systems version.")
    version_parser.set_defaults(func=_cmd_version)

    doctor_parser = subparsers.add_parser("doctor", help="Inspect local package health and optional dependencies.")
    doctor_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    doctor_parser.set_defaults(func=_cmd_doctor)

    runtime_parser = subparsers.add_parser("runtime", help="Describe a RuntimeConfig without executing a model.")
    runtime_parser.add_argument("--provider", default="auto", help="Runtime provider, for example auto, python-direct, bedrock-runtime or openai-runtime.")
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
