"""Verify immutable release artifacts and reconcile their state on a package index.

This module never uploads or overwrites a distribution. A missing release permits
an upload; an identical release permits resuming post-publication checks. Every
partial, ambiguous or conflicting release stops the workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from enum import Enum
from pathlib import Path
from typing import Callable, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PublicationDecision(str, Enum):
    ABSENT = "absent"
    MATCHING = "matching"
    CONFLICT = "conflict"


class ReleaseArtifactIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    filename: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    kind: Literal["bdist_wheel", "sdist", "asset"]

    @field_validator("filename")
    @classmethod
    def safe_filename(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
            raise ValueError("Artifact must be a plain filename")
        return value

    @model_validator(mode="after")
    def extension_matches_kind(self) -> ReleaseArtifactIdentity:
        expected = (
            "bdist_wheel"
            if self.filename.endswith(".whl")
            else "sdist"
            if self.filename.endswith(".tar.gz")
            else "asset"
        )
        if self.kind != expected:
            raise ValueError("Artifact extension and kind differ")
        if self.filename == "release-manifest.json":
            raise ValueError("Manifest cannot include itself")
        return self


class ReleaseManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["agentic_systems.release-manifest.v1"] = (
        "agentic_systems.release-manifest.v1"
    )
    project: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    commit_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    artifacts: tuple[ReleaseArtifactIdentity, ...]

    @model_validator(mode="after")
    def unique_distributions(self) -> ReleaseManifest:
        names = [item.filename for item in self.artifacts]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate artifact filename")
        stem = f"{self.project.replace('-', '_')}-{self.version}"
        expected = {
            f"{stem}-py3-none-any.whl": "bdist_wheel",
            f"{stem}.tar.gz": "sdist",
        }
        observed = {
            item.filename: item.kind for item in self.artifacts if item.kind != "asset"
        }
        if observed != expected:
            raise ValueError(
                "Manifest must contain the version's exact wheel and sdist"
            )
        return self


class PublishedDistributionState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: PublicationDecision
    reason: str


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path, expected_sha256: str) -> ReleaseManifest:
    if sha256(path) != expected_sha256:
        raise ValueError("Manifest SHA256 mismatch")
    return ReleaseManifest.model_validate_json(path.read_bytes())


def verify_artifacts(manifest: ReleaseManifest, directory: Path) -> None:
    for artifact in manifest.artifacts:
        path = directory / artifact.filename
        if path.is_symlink() or not path.is_file() or sha256(path) != artifact.sha256:
            raise ValueError(
                f"Artifact missing or SHA256 mismatch: {artifact.filename}"
            )


def reconcile(
    manifest: ReleaseManifest, payload: dict | None
) -> PublishedDistributionState:
    if payload is None:
        return PublishedDistributionState(
            decision=PublicationDecision.ABSENT, reason="Version is absent from index"
        )
    conflict = PublishedDistributionState(
        decision=PublicationDecision.CONFLICT,
        reason="Index metadata or complete distribution set differs from manifest",
    )
    info = payload.get("info", {})
    if not isinstance(info, dict):
        return conflict
    name = re.sub(r"[-_.]+", "-", str(info.get("name", ""))).lower()
    if name != manifest.project or info.get("version") != manifest.version:
        return conflict
    urls = payload.get("urls")
    if not isinstance(urls, list):
        return conflict
    expected = {
        item.filename: (item.kind, item.sha256)
        for item in manifest.artifacts
        if item.kind != "asset"
    }
    observed = {}
    for item in urls:
        if not isinstance(item, dict) or not isinstance(item.get("digests"), dict):
            return conflict
        filename = item.get("filename")
        if not isinstance(filename, str) or filename in observed or item.get("yanked"):
            return conflict
        observed[filename] = (item.get("packagetype"), item["digests"].get("sha256"))
    if observed != expected:
        return conflict
    return PublishedDistributionState(
        decision=PublicationDecision.MATCHING,
        reason="Every published distribution matches the certified SHA256",
    )


def fetch_index(url: str, *, timeout_s: float = 15) -> dict | None:
    try:
        with urlopen(url, timeout=timeout_s) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    if not isinstance(payload, dict):
        raise ValueError("Index returned a non-object JSON document")
    return payload


def check_index(
    manifest: ReleaseManifest,
    *,
    index: Literal["pypi", "testpypi"] = "pypi",
    require_present: bool = False,
    attempts: int = 6,
    fetch: Callable = fetch_index,
    sleep: Callable = time.sleep,
) -> PublishedDistributionState:
    if not 1 <= attempts <= 6:
        raise ValueError("attempts must be between 1 and 6")
    if index not in {"pypi", "testpypi"}:
        raise ValueError("Unsupported package index")
    host = "pypi.org" if index == "pypi" else "test.pypi.org"
    url = (
        f"https://{host}/pypi/{quote(manifest.project)}/{quote(manifest.version)}/json"
    )
    for attempt in range(attempts):
        try:
            result = reconcile(manifest, fetch(url, timeout_s=15))
        except HTTPError as exc:
            if exc.code != 429 and not 500 <= exc.code < 600:
                raise
            if attempt == attempts - 1:
                raise
        except (URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
        else:
            if result.decision == PublicationDecision.CONFLICT:
                raise ValueError(result.reason)
            if not require_present or result.decision == PublicationDecision.MATCHING:
                return result
            if attempt == attempts - 1:
                raise TimeoutError("Published version did not become visible")
        sleep(min(2**attempt, 16))
    raise RuntimeError("Unreachable index state")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--index", choices=("pypi", "testpypi"), default="pypi")
    parser.add_argument("--require-present", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest(args.manifest, args.manifest_sha256)
    verify_artifacts(manifest, args.directory)
    outputs = {"version": manifest.version, "commit_sha": manifest.commit_sha}
    if not args.verify_only:
        result = check_index(
            manifest, index=args.index, require_present=args.require_present
        )
        outputs["decision"] = result.decision.value
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write("".join(f"{key}={value}\n" for key, value in outputs.items()))
    print(json.dumps(outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
