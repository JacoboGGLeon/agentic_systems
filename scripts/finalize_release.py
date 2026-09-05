"""Resume a GitHub release without moving tags or replacing existing assets."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from release_publication import load_manifest, sha256, verify_artifacts


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def remote_tag_commit(tag: str) -> str | None:
    ref = f"refs/tags/{tag}"
    rows = command("git", "ls-remote", "origin", ref, ref + "^{}")
    refs = dict(reversed(line.split()) for line in rows.splitlines())
    return refs.get(ref + "^{}", refs.get(ref))


def find_release(repository: str, tag: str) -> dict | None:
    releases = json.loads(
        command(
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repository}/releases?per_page=100",
        )
    )
    matching = [
        release for page in releases for release in page if release["tag_name"] == tag
    ]
    if len(matching) > 1:
        raise ValueError("Multiple releases claim the same tag")
    return matching[0] if matching else None


def verify_remote_assets(
    repository: str, tag: str, existing: list[dict], expected: dict[str, str]
) -> set[str]:
    names = [asset["name"] for asset in existing]
    if len(names) != len(set(names)) or not set(names) <= set(expected):
        raise ValueError("Unexpected or duplicate existing release assets")
    with tempfile.TemporaryDirectory(prefix="release-assets-") as temporary:
        for asset in existing:
            command(
                "gh",
                "release",
                "download",
                tag,
                "--repo",
                repository,
                "--pattern",
                asset["name"],
                "--dir",
                temporary,
            )
            if sha256(Path(temporary) / asset["name"]) != expected[asset["name"]]:
                raise ValueError(f"Existing asset conflicts: {asset['name']}")
    return set(names)


def finalize(directory: Path, manifest_sha256: str) -> None:
    manifest_path = directory / "release-manifest.json"
    manifest = load_manifest(manifest_path, manifest_sha256)
    verify_artifacts(manifest, directory)
    repository = os.environ["GITHUB_REPOSITORY"]
    tag = f"v{manifest.version}"
    observed_commit = remote_tag_commit(tag)
    if observed_commit is not None and observed_commit != manifest.commit_sha:
        raise ValueError("Existing tag points to a different commit")
    release = find_release(repository, tag)
    if release and observed_commit is None:
        if not release["draft"] or release["target_commitish"] != manifest.commit_sha:
            raise ValueError("Release has no matching immutable target")
    expected = {item.filename: item.sha256 for item in manifest.artifacts}
    expected[manifest_path.name] = manifest_sha256
    names = verify_remote_assets(
        repository, tag, release["assets"] if release else [], expected
    )
    if release and not release["draft"] and not release["prerelease"]:
        if names != set(expected):
            raise ValueError("Published release is incomplete; it will not be modified")
        return
    if not release:
        command(
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            repository,
            "--target",
            manifest.commit_sha,
            "--draft",
            "--title",
            f"Agentic Systems {manifest.version}",
            "--generate-notes",
        )
    for name in sorted(expected.keys() - names):
        command(
            "gh", "release", "upload", tag, str(directory / name), "--repo", repository
        )
    uploaded = find_release(repository, tag)
    if uploaded is None or verify_remote_assets(
        repository, tag, uploaded["assets"], expected
    ) != set(expected):
        raise ValueError("Uploaded release is incomplete; leaving it unpublished")
    observed_commit = remote_tag_commit(tag)
    if observed_commit is not None and observed_commit != manifest.commit_sha:
        raise ValueError("Tag changed during release assembly")
    if observed_commit is None and uploaded["target_commitish"] != manifest.commit_sha:
        raise ValueError("Draft target changed during release assembly")
    command(
        "gh",
        "release",
        "edit",
        tag,
        "--repo",
        repository,
        "--draft=false",
        "--prerelease=false",
        "--latest",
    )
    if remote_tag_commit(tag) != manifest.commit_sha:
        raise ValueError("Published tag does not match the certified commit")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    finalize(args.directory, args.manifest_sha256)
