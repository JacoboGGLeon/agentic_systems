"""Install the exact built SDK and optional application wheels without editable mode."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--extras", default="dev,bedrock,openai,openai-agents,strands")
    parser.add_argument("--target", type=Path)
    args = parser.parse_args()
    wheels = sorted(args.directory.glob("*.whl"))
    sdk = [wheel for wheel in wheels if wheel.name.startswith("agentic_systems-")]
    if len(sdk) != 1:
        raise ValueError("Candidate directory must contain exactly one SDK wheel")
    target = ["--target", str(args.target.resolve())] if args.target else []
    subprocess.run([sys.executable, "-m", "pip", "install", *target,
                    str(sdk[0].resolve()) + (f"[{args.extras}]" if args.extras else "")], check=True)
    applications = [wheel for wheel in wheels if wheel not in sdk]
    if applications:
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", *target,
                        *[str(wheel.resolve()) for wheel in applications]], check=True)
    print(json.dumps({"sdk": sdk[0].name, "applications": [wheel.name for wheel in applications]}))


if __name__ == "__main__":
    main()
