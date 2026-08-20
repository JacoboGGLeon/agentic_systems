"""Rich command-line interface for Agentic Systems Studio."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .catalog import SYSTEM_SPECS, composition_mermaid, get_system_spec
from .creator import create_application
from .scaffolder import scaffold_application
from .server import DEFAULT_HOST, DEFAULT_PORT, serve_studio
from .store import StudioStore
from .systems import StudioConfig, build_system, compose_systems
from .validation import validate_catalog, write_validation_report


def _dump(value: Any) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _config(args: argparse.Namespace) -> StudioConfig:
    return StudioConfig(
        provider=args.provider,
        framework=args.framework,
        model=args.model,
        timeout_s=args.timeout,
        max_tokens=args.max_tokens,
    )


def _list() -> None:
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        for spec in SYSTEM_SPECS:
            print(
                f"{spec.id:28} {spec.size:6} {len(spec.stages)} agents  {spec.summary}"
            )
        return
    table = Table(title="Agentic Systems Studio")
    table.add_column("System")
    table.add_column("Size")
    table.add_column("Agents", justify="right")
    table.add_column("Capabilities")
    for spec in SYSTEM_SPECS:
        table.add_row(
            spec.id, spec.size, str(len(spec.stages)), ", ".join(spec.capabilities)
        )
    Console().print(table)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentic-studio")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List reusable systems.")

    describe = sub.add_parser("describe", help="Show one manifest.")
    describe.add_argument("system_id")

    diagram = sub.add_parser(
        "diagram", help="Print Mermaid from the executable catalog."
    )
    diagram.add_argument("system_ids", nargs="+")
    diagram.add_argument(
        "--mode", choices=("sequential", "parallel"), default="sequential"
    )

    init = sub.add_parser("init", help="Scaffold a complete agentic application.")
    init.add_argument("target", type=Path)
    init.add_argument("--name", required=True)
    init.add_argument("--system", default="agentic-systems-creator")
    init.add_argument("--overwrite", action="store_true")

    create = sub.add_parser(
        "create",
        help="Reason, generate and validate a complete agentic application.",
    )
    create.add_argument("target", type=Path)
    create.add_argument("--name", required=True)
    create.add_argument("--template", default="incident-response")
    create.add_argument("--input")
    create.add_argument("--provider", default="openai-runtime")
    create.add_argument("--framework", default="agentic-systems")
    create.add_argument("--model")
    create.add_argument("--timeout", type=float, default=120.0)
    create.add_argument("--max-tokens", type=int, default=1024)
    create.add_argument("--overwrite", action="store_true")
    create.add_argument("--db", type=Path, default=Path(".agentic-studio/studio.db"))

    for name in ("run", "compose"):
        command = sub.add_parser(name)
        command.add_argument("system_ids", nargs="+" if name == "compose" else 1)
        command.add_argument("--input")
        command.add_argument("--provider", default="openai-runtime")
        command.add_argument("--framework", default="agentic-systems")
        command.add_argument("--model")
        command.add_argument("--timeout", type=float, default=120.0)
        command.add_argument("--max-tokens", type=int, default=1024)
        command.add_argument(
            "--db", type=Path, default=Path(".agentic-studio/studio.db")
        )
        if name == "compose":
            command.add_argument(
                "--mode", choices=("sequential", "parallel"), default="sequential"
            )

    validate = sub.add_parser(
        "validate", help="Execute catalog systems and write non-secret live evidence."
    )
    validate.add_argument("system_ids", nargs="*")
    validate.add_argument("--provider", default="openai-runtime")
    validate.add_argument("--framework", default="agentic-systems")
    validate.add_argument("--model")
    validate.add_argument("--timeout", type=float, default=120.0)
    validate.add_argument("--max-tokens", type=int, default=1024)
    validate.add_argument("--output", type=Path)
    validate.add_argument("--fail-fast", action="store_true")

    database = sub.add_parser(
        "db", help="Initialize and inspect the local catalog database."
    )
    database.add_argument(
        "--path", type=Path, default=Path(".agentic-studio/studio.db")
    )

    serve = sub.add_parser("serve", help="Launch the Streamlit Studio.")
    serve.add_argument("--app", type=Path)
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--log-dir", type=Path)
    serve.add_argument("--proxy-prefix")
    serve.add_argument("--timeout", type=float, default=60.0)
    serve.add_argument("--detach", action="store_true")
    serve.add_argument("--open-browser", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "list":
        _list()
        return 0
    if args.command == "describe":
        _dump(get_system_spec(args.system_id).to_dict())
        return 0
    if args.command == "diagram":
        ids = tuple(args.system_ids)
        print(
            get_system_spec(ids[0]).mermaid()
            if len(ids) == 1
            else composition_mermaid(ids, mode=args.mode)
        )
        return 0
    if args.command == "init":
        report = scaffold_application(
            args.target,
            name=args.name,
            system_id=args.system,
            overwrite=args.overwrite,
        )
        _dump(report.to_dict())
        return 0
    if args.command == "create":
        request = args.input or get_system_spec("agentic-systems-creator").sample_input
        result = create_application(
            request,
            args.target,
            name=args.name,
            template_system_id=args.template,
            config=_config(args),
            overwrite=args.overwrite,
        )
        StudioStore(args.db).record_run(
            system_id="agentic-systems-creator",
            provider=args.provider,
            framework=args.framework,
            input=request,
            result=result,
        )
        _dump(result)
        return 0 if result.ok else 1
    if args.command == "db":
        store = StudioStore(args.path)
        store.initialize()
        _dump({"path": str(store.path.resolve()), "inventory": store.inventory()})
        return 0
    if args.command == "validate":
        report = validate_catalog(
            _config(args),
            args.system_ids or None,
            fail_fast=args.fail_fast,
        )
        if args.output is not None:
            write_validation_report(report, args.output)
        _dump(report)
        return 0 if report["ok"] else 1
    if args.command == "serve":
        return serve_studio(
            app_path=args.app,
            host=args.host,
            port=args.port,
            log_dir=args.log_dir,
            proxy_prefix=args.proxy_prefix,
            timeout_s=args.timeout,
            detach=args.detach,
            open_browser=args.open_browser,
        )
    if args.command == "run":
        system_id = args.system_ids[0]
        system = build_system(system_id, _config(args))
        input_value = args.input or system.spec.sample_input
        result = system.run(input_value)
        StudioStore(args.db).record_run(
            system_id=system_id,
            provider=args.provider,
            framework=args.framework,
            input=input_value,
            result=result,
        )
        _dump(result)
        return 0 if result.ok else 1
    if args.command == "compose":
        composition = compose_systems(
            tuple(args.system_ids),
            _config(args),
            mode=args.mode,
        )
        input_value = args.input or composition.systems[0].spec.sample_input
        result = composition.run(input_value)
        StudioStore(args.db).record_composition(
            mode=args.mode,
            system_ids=composition.ids,
            result=result,
        )
        _dump(result)
        return 0 if result.ok else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
