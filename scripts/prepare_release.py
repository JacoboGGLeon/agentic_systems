"""Promote an explicitly reviewed stable delivery without rebuilding its bytes."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess

from release_publication import load_manifest, sha256, verify_artifacts

try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def prepare(approved, output, manifest_sha256):
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    manifest = load_manifest(approved / "release-manifest.json", manifest_sha256)
    if manifest.version != version:
        raise ValueError("Approved release does not match the current source version")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if manifest.commit_sha != commit:
        raise ValueError("Approved release does not match this commit")
    verify_artifacts(manifest, approved)
    identities = {item.filename: item.sha256 for item in manifest.artifacts}
    if "acceptance.json" not in identities:
        raise ValueError("A reviewed acceptance record is required")
    acceptance = json.loads((approved / "acceptance.json").read_text(encoding="utf-8"))
    wheel = next(item for item in manifest.artifacts if item.kind == "bdist_wheel")
    if not (acceptance.get("offline_passed") is True and acceptance.get("live_passed") is True
            and acceptance.get("wheel_sha256") == wheel.sha256 and acceptance.get("commit_sha") == commit
            and set(acceptance.get("python_versions", ())) == {"3.10", "3.11", "3.12", "3.13", "3.14"}):
        raise ValueError("Reviewed offline/live acceptance is incomplete or bound to other bytes")
    sources = acceptance.get("source_sha256", {})
    required = {"pyproject.toml", "README.md", *[p.relative_to(ROOT).as_posix() for p in (ROOT / "src").rglob("*.py")]}
    if not required <= set(sources):
        raise ValueError("Acceptance must cover the current SDK source")
    for name, expected in sources.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or sha256(path) != expected:
            raise ValueError("Reviewed source changed or is outside the repository")
    if output.exists():
        raise FileExistsError("Choose a new delivery directory")
    output.mkdir(parents=True)
    for item in manifest.artifacts:
        shutil.copyfile(approved / item.filename, output / item.filename)
    shutil.copyfile(approved / "release-manifest.json", output / "release-manifest.json")
    verify_artifacts(manifest, output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    print(prepare(args.approved_directory.resolve(), args.output.resolve(), args.manifest_sha256))
