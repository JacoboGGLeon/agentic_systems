"""Inspect the SDK and distribute its bundled authoring skill."""
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
    authoring = commands.add_parser("skill", help="Inspect, install or export the bundled authoring skill (offline)")
    skill_commands = authoring.add_subparsers(dest="skill_command", required=True)
    skill_commands.add_parser("info", help="Print bundled file hashes and SDK identity as JSON")
    install = skill_commands.add_parser("install", help="Copy the skill to a new directory; never overwrite")
    install.add_argument("destination", nargs="?", default=".agents/skills/agentic-systems")
    export = skill_commands.add_parser("export", help="Create an importable ZIP; never overwrite")
    export.add_argument("destination", help="New .zip file")
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
    elif args.command == "skill":
        from ._skill_distribution import export_skill, install_skill, skill_info
        try:
            if args.skill_command == "info":
                print(json.dumps(skill_info()))
            elif args.skill_command == "install":
                print(install_skill(args.destination))
            else:
                print(export_skill(args.destination))
        except (OSError, ValueError) as exc:
            parser.exit(2, f"agentic-systems: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
