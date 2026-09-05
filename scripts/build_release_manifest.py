"""Bind the audited release files to one typed, hash-addressed manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from release_publication import (
    ReleaseArtifactIdentity,
    ReleaseManifest,
    sha256,
    verify_artifacts,
)


def build(directory: Path) -> Path:
    summary_path = directory / "final-certification-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("schema_version") != "agentic_systems.release-certification.v1":
        raise ValueError("Unsupported certification schema")
    if (
        summary.get("secrets_redacted") is not True
        or summary.get("no_fallback") is not True
    ):
        raise ValueError("Certification safety gates are incomplete")
    version = summary["package_version"]
    checksums = directory / f"SHA256SUMS-{version}.txt"
    artifacts = []
    for line in checksums.read_text(encoding="utf-8").splitlines():
        digest, filename = line.split("  ", 1)
        kind = (
            "bdist_wheel"
            if filename.endswith(".whl")
            else "sdist"
            if filename.endswith(".tar.gz")
            else "asset"
        )
        artifacts.append(
            ReleaseArtifactIdentity(filename=filename, sha256=digest, kind=kind)
        )
    artifacts.append(
        ReleaseArtifactIdentity(
            filename=checksums.name, sha256=sha256(checksums), kind="asset"
        )
    )
    manifest = ReleaseManifest(
        project="agentic-systems",
        version=version,
        commit_sha=summary["assembly_commit_sha"],
        artifacts=artifacts,
    )
    required = {
        "final-certification-summary.json",
        f"agentic-systems-{version}-ada-offline.zip",
        f"agentic-systems-{version}-strands-protocol-challenge.zip",
        f"agentic-systems-studio-{version}.zip",
        f"agentic-systems-skill-{version}.zip",
    }
    if not required <= {item.filename for item in manifest.artifacts}:
        raise ValueError("Missing required release deliveries")
    verify_artifacts(manifest, directory)
    identities = {
        item.kind: item.sha256 for item in manifest.artifacts if item.kind != "asset"
    }
    if identities != {
        "bdist_wheel": summary["wheel_sha256"],
        "sdist": summary["sdist_sha256"],
    }:
        raise ValueError("Certification artifact identity differs")
    totals = summary["totals"]
    if (
        totals["certified_live_failed"] != 0
        or totals["total_semantic_episodes_failed"] != 0
    ):
        raise ValueError("Semantic certification contains failures")
    reviewed = totals["total_semantic_episodes_reviewed"]
    if type(reviewed) is not int or reviewed <= 0:
        raise ValueError("Semantic certification is incomplete")
    output = directory / "release-manifest.json"
    output.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("dist"))
    result = build(parser.parse_args().directory)
    print(json.dumps({"manifest": str(result), "sha256": sha256(result)}))
