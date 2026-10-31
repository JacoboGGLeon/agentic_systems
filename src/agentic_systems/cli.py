"""Inspect the current SDK and scaffold explicit Graph applications."""
import argparse
import importlib.util
import json
from . import __version__, __all__


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agentic-systems")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("version", help="Print the installed SDK version")
    commands.add_parser("api", help="List the installed public names as JSON")
    commands.add_parser("doctor", help="Inspect installed dependencies without calling services")
    project = commands.add_parser("new", help="Create an offline Graph application in a new directory")
    project.add_argument("destination", help="New project directory; existing paths are never overwritten")
    args = parser.parse_args(argv)
    if args.command == "version":
        print(__version__)
    elif args.command == "api":
        print(json.dumps({"version": __version__, "public_api": __all__}))
    elif args.command == "doctor":
        print(json.dumps({"version": __version__, "scope": "installed-dependencies-only", "services_checked": False, "optional_dependencies": {
            name: importlib.util.find_spec(module) is not None
            for name, module in {"langgraph": "langgraph", "openai": "openai",
                                 "openai-agents": "agents", "strands": "strands", "bedrock": "boto3"}.items()
        }, "inference_executed": False}))
    else:
        from ._scaffolding import create_project
        try:
            print(create_project(args.destination))
        except (OSError, ValueError) as exc:
            parser.exit(2, f"agentic-systems: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
