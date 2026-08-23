"""Render a GitHub Actions matrix from validated external live profiles."""

from __future__ import annotations

import argparse
import json

from run_live_matrix import _load_profile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    providers, frameworks = _load_profile(args.profile)
    print(
        json.dumps(
            {
                "include": [
                    {"provider": provider, "framework": framework}
                    for provider in providers
                    for framework in frameworks
                ]
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
