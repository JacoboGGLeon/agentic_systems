"""CLI for the single 2.1.3 API. Commands never select a legacy surface."""
import argparse
import importlib.util
import json
from . import __version__, __all__


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agentic-systems")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("version")
    commands.add_parser("api")
    commands.add_parser("doctor")
    project = commands.add_parser("new")
    project.add_argument("destination")
    args = parser.parse_args(argv)
    if args.command == "version":
        print(__version__)
    elif args.command == "api":
        print(json.dumps({"version": __version__, "public_api": __all__}))
    elif args.command == "doctor":
        print(json.dumps({"version": __version__, "optional_dependencies": {
            name: importlib.util.find_spec(module) is not None
            for name, module in {"langgraph": "langgraph", "openai": "openai",
                                 "openai-agents": "agents", "strands": "strands", "bedrock": "boto3"}.items()
        }, "inference_executed": False}))
    else:
        from ._scaffolding import create_project
        print(create_project(args.destination))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
