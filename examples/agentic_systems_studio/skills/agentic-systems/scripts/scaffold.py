"""Invoke the Agentic Systems Studio reference scaffolder."""

from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("--name", required=True)
    parser.add_argument("--system", default="agentic-systems-creator")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        from agentic_systems_studio import scaffold_application
    except ImportError as exc:
        raise SystemExit(
            "Install the bundled agentic-systems-studio package before using this helper."
        ) from exc
    report = scaffold_application(
        args.target,
        name=args.name,
        system_id=args.system,
        overwrite=args.overwrite,
    )
    payload = report.to_dict()
    print(json.dumps(payload, indent=2))
    return 0 if payload["validation"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
