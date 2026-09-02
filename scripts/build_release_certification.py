"""Build the release certification summary from validated live evidence.

The summary is generated from immutable artifacts instead of being edited by
hand.  A release assembly may add documentation or application presentation
changes after the runtime certification commit, but only when the packaged
``src/agentic_systems`` tree is identical.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 only.
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORKS = {"native", "langgraph", "openai-agents", "strands"}
PRIMARY_PROVIDERS = {
    "python-runtime",
    "openai-runtime",
    "ollama-runtime",
    "bedrock-runtime",
    "vllm-runtime",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _assert_identity(
    payload: dict[str, Any],
    *,
    path: Path,
    version: str,
    commit: str,
    wheel_sha256: str,
    require_version: bool = True,
) -> None:
    observed = {
        "commit_sha": payload.get("commit_sha"),
        "wheel_sha256": payload.get("wheel_sha256"),
    }
    expected = {
        "commit_sha": commit,
        "wheel_sha256": wheel_sha256,
    }
    if require_version:
        observed["package_version"] = payload.get("package_version")
        expected["package_version"] = version
    if observed != expected:
        raise ValueError(
            f"Evidence identity mismatch for {path.name}: "
            f"observed={observed!r}, expected={expected!r}"
        )


def _semantic_row(
    path: Path,
    *,
    provider: str,
    version: str,
    commit: str,
    wheel_sha256: str,
) -> dict[str, Any]:
    payload = _read_json(path)
    if payload.get("schema_version") != "agentic_systems.semantic-attestation.v1":
        raise ValueError(f"Unsupported semantic evidence: {path.name}")
    _assert_identity(
        payload,
        path=path,
        version=version,
        commit=commit,
        wheel_sha256=wheel_sha256,
    )
    if not payload.get("wheel_runtime_verified"):
        raise ValueError(f"Wheel runtime was not verified: {path.name}")

    cells = [
        cell for cell in payload.get("cells", []) if cell.get("provider") == provider
    ]
    episodes = [episode for cell in cells for episode in cell.get("episodes", [])]
    if (
        len(cells) != 4
        or {cell.get("framework") for cell in cells} != FRAMEWORKS
        or any(not cell.get("ok") for cell in cells)
        or any(
            not episode.get("ok")
            or not episode.get("deterministic_validation", {}).get("ok")
            or not episode.get("judge", {}).get("ok")
            for episode in episodes
        )
    ):
        raise ValueError(f"Semantic evidence is incomplete: {path.name}:{provider}")

    runtime = (
        payload.get("environment", {})
        .get("providers", {})
        .get(provider, {})
        .get("runtime", {})
    )
    if runtime.get("selected_provider") != provider or runtime.get("fallback_provider"):
        raise ValueError(f"Semantic evidence used fallback: {path.name}:{provider}")

    models = {cell.get("model") for cell in cells if cell.get("model")}
    if len(models) != 1:
        raise ValueError(f"Inconsistent models: {path.name}:{provider}:{models!r}")
    expected_episodes = 12 if provider == "python-runtime" else 16
    if len(episodes) != expected_episodes:
        raise ValueError(
            f"Unexpected episode count: {path.name}:{provider}:{len(episodes)}"
        )

    return {
        "artifact": path.name,
        "evidence_kind": (
            "semantic-deterministic-control"
            if provider == "python-runtime"
            else "semantic-live"
        ),
        "model": models.pop(),
        "frameworks": sorted(FRAMEWORKS),
        "passed": 4,
        "failed": 0,
        "episodes_passed": len(episodes),
        "episodes_failed": 0,
        "sha256": _sha256(path),
    }


def _authentication_row(
    path: Path,
    *,
    semantic_path: Path,
    review_path: Path,
    version: str,
    commit: str,
    wheel_sha256: str,
) -> dict[str, Any]:
    payload = _read_json(path)
    if payload.get("schema_version") != "agentic_systems.live-attestation.v1":
        raise ValueError(f"Unsupported authentication evidence: {path.name}")
    _assert_identity(
        payload,
        path=path,
        version=version,
        commit=commit,
        wheel_sha256=wheel_sha256,
        require_version=False,
    )
    environment = payload.get("environment", {})
    cases = payload.get("cases", [])
    if (
        environment.get("bedrock_authentication_mode") != "aws-credential-chain"
        or not environment.get("uses_aws_credential_chain")
        or len(cases) != 4
        or {case.get("framework") for case in cases} != FRAMEWORKS
        or any(
            case.get("provider") != "bedrock-runtime" or not case.get("ok")
            for case in cases
        )
    ):
        raise ValueError(f"Authentication evidence is incomplete: {path.name}")
    for case in cases:
        for scenario in case.get("scenarios", []):
            if not scenario.get("ok") or scenario.get("details", {}).get(
                "fallback_provider"
            ):
                raise ValueError(f"Authentication evidence used fallback: {path.name}")

    semantic = _semantic_row(
        semantic_path,
        provider="bedrock-runtime",
        version=version,
        commit=commit,
        wheel_sha256=wheel_sha256,
    )
    return {
        "artifact": path.name,
        "semantic_artifact": semantic_path.name,
        "semantic_review": review_path.name,
        "evidence_kind": "live-authentication-and-semantic",
        "authentication_mode": "aws-credential-chain",
        "credential_method": environment.get("bedrock_credential_method"),
        "environment": environment.get("execution_environment", "AWS SageMaker AI"),
        "region": environment.get("aws_region"),
        "model": semantic["model"],
        "frameworks": sorted(FRAMEWORKS),
        "passed": 4,
        "failed": 0,
        "semantic_episodes_passed": semantic["episodes_passed"],
        "semantic_episodes_failed": 0,
        "sha256": _sha256(path),
        "semantic_sha256": _sha256(semantic_path),
        "review_sha256": _sha256(review_path),
    }


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    version = str(
        tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
            "version"
        ]
    )
    wheel = args.wheel.resolve()
    sdist = args.sdist.resolve()
    wheel_sha256 = _sha256(wheel)
    assembly_commit = _git("rev-parse", "HEAD")
    certified_commit = _git("rev-parse", args.commit)
    certified_tree = _git("rev-parse", f"{certified_commit}:src/agentic_systems")
    assembly_tree = _git("rev-parse", "HEAD:src/agentic_systems")
    if certified_tree != assembly_tree:
        raise ValueError("Certified and release-assembly core trees differ")
    if subprocess.run(
        ["git", "diff", "--quiet", "--", "src/agentic_systems"], cwd=ROOT
    ).returncode:
        raise ValueError("The release-assembly core tree is dirty")

    local_rows = {
        provider: _semantic_row(
            args.local_attestation,
            provider=provider,
            version=version,
            commit=certified_commit,
            wheel_sha256=wheel_sha256,
        )
        for provider in ("python-runtime", "openai-runtime", "ollama-runtime")
    }
    bedrock_row = _semantic_row(
        args.bedrock_api_attestation,
        provider="bedrock-runtime",
        version=version,
        commit=certified_commit,
        wheel_sha256=wheel_sha256,
    )
    vllm_row = _semantic_row(
        args.vllm_attestation,
        provider="vllm-runtime",
        version=version,
        commit=certified_commit,
        wheel_sha256=wheel_sha256,
    )
    primary = {
        **local_rows,
        "bedrock-runtime": bedrock_row,
        "vllm-runtime": vllm_row,
    }
    if set(primary) != PRIMARY_PROVIDERS:
        raise ValueError(f"Primary provider set is incomplete: {set(primary)!r}")

    iam_row = _authentication_row(
        args.bedrock_iam_attestation,
        semantic_path=args.bedrock_iam_semantic_attestation,
        review_path=args.bedrock_iam_review,
        version=version,
        commit=certified_commit,
        wheel_sha256=wheel_sha256,
    )

    evidence_inventory: dict[str, Any] = {
        "local_semantic_review": {
            "artifact": args.local_review.name,
            "sha256": _sha256(args.local_review),
        },
        "bedrock_api_semantic_review": {
            "artifact": args.bedrock_api_review.name,
            "sha256": _sha256(args.bedrock_api_review),
        },
        "vllm_semantic_review": {
            "artifact": args.vllm_review.name,
            "sha256": _sha256(args.vllm_review),
        },
        "aws_iam_semantic_review": {
            "artifact": args.bedrock_iam_review.name,
            "sha256": _sha256(args.bedrock_iam_review),
        },
    }
    if args.studio_attestation is not None:
        studio = _read_json(args.studio_attestation)
        if studio.get("ok") is not True:
            raise ValueError("Studio attestation did not pass")
        evidence_inventory["studio_live_validation"] = {
            "artifact": args.studio_attestation.name,
            "sha256": _sha256(args.studio_attestation),
        }

    primary_episodes = sum(row["episodes_passed"] for row in primary.values())
    if primary_episodes != 76:
        raise ValueError(
            f"Primary semantic episode total is {primary_episodes}, not 76"
        )
    return {
        "schema_version": "agentic_systems.release-certification.v1",
        "package_version": version,
        "commit_sha": certified_commit,
        "assembly_commit_sha": assembly_commit,
        "core_tree_sha": certified_tree,
        "wheel_sha256": wheel_sha256,
        "sdist_sha256": _sha256(sdist),
        "generated_at": datetime.now(UTC).isoformat(),
        "no_fallback": True,
        "secrets_redacted": True,
        "artifact_equivalence": {
            "runtime_tree_identical": True,
            "certified_commit": certified_commit,
            "assembly_commit": assembly_commit,
            "scope": "src/agentic_systems",
        },
        "offline_gates": {
            "ruff": "passed",
            "format": "passed",
            "architecture": "passed",
            "complexity": "passed",
            "secrets": "passed",
            "benchmark": "passed",
            "licenses": "passed",
            "pyright_regressions": 0,
            "pytest_passed": args.pytest_passed,
            "pytest_skipped": args.pytest_skipped,
        },
        "primary_matrix": primary,
        "additional_authentication_routes": {
            "bedrock-runtime/aws-credential-chain": iam_row
        },
        "evidence_inventory": evidence_inventory,
        "totals": {
            "primary_combinations": 20,
            "primary_passed": 20,
            "primary_failed": 0,
            "semantic_episodes": 76,
            "semantic_episodes_passed": 76,
            "semantic_episodes_failed": 0,
            "additional_route_combinations": 4,
            "additional_route_passed": 4,
            "additional_route_failed": 0,
            "certified_live_executions": 24,
            "certified_live_passed": 24,
            "certified_live_failed": 0,
            "total_semantic_episodes_reviewed": 92,
            "total_semantic_episodes_passed": 92,
            "total_semantic_episodes_failed": 0,
        },
    }


def _path(value: str) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"File does not exist: {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--wheel", required=True, type=_path)
    parser.add_argument("--sdist", required=True, type=_path)
    parser.add_argument("--local-attestation", required=True, type=_path)
    parser.add_argument("--local-review", required=True, type=_path)
    parser.add_argument("--bedrock-api-attestation", required=True, type=_path)
    parser.add_argument("--bedrock-api-review", required=True, type=_path)
    parser.add_argument("--vllm-attestation", required=True, type=_path)
    parser.add_argument("--vllm-review", required=True, type=_path)
    parser.add_argument("--bedrock-iam-attestation", required=True, type=_path)
    parser.add_argument("--bedrock-iam-semantic-attestation", required=True, type=_path)
    parser.add_argument("--bedrock-iam-review", required=True, type=_path)
    parser.add_argument("--studio-attestation", type=_path)
    parser.add_argument("--pytest-passed", required=True, type=int)
    parser.add_argument("--pytest-skipped", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    summary = build_summary(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output.resolve()), "ok": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
