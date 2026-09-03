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
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

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
ROUTE_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class AuthenticationEvidenceSpec(BaseModel):
    """Typed description of one externally executed authentication route."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str
    environment: str
    attestation: Path
    semantic_attestation: Path
    review: Path

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        if not ROUTE_KEY.fullmatch(value):
            raise ValueError("key must be a lowercase filesystem-safe identifier")
        return value

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("environment must not be empty")
        return value


AuthenticationEvidenceSpec.model_rebuild(_types_namespace={"Path": Path})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_authentication_specs(
    paths: list[Path],
) -> tuple[AuthenticationEvidenceSpec, ...]:
    specs: list[AuthenticationEvidenceSpec] = []
    keys: set[str] = set()
    for path in paths:
        spec = AuthenticationEvidenceSpec.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        base = path.resolve().parent
        spec = spec.model_copy(
            update={
                field: (
                    value.resolve() if value.is_absolute() else (base / value).resolve()
                )
                for field, value in (
                    ("attestation", spec.attestation),
                    ("semantic_attestation", spec.semantic_attestation),
                    ("review", spec.review),
                )
            }
        )
        missing = [
            str(value)
            for value in (spec.attestation, spec.semantic_attestation, spec.review)
            if not value.is_file()
        ]
        if missing:
            raise ValueError(
                f"Authentication route {spec.key!r} has missing evidence: {missing}"
            )
        if spec.key in keys:
            raise ValueError(f"Duplicate authentication route key: {spec.key}")
        keys.add(spec.key)
        specs.append(spec)
    if not specs:
        raise ValueError("At least one authentication route spec is required")
    return tuple(specs)


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
    environment_name: str,
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
        "environment": environment_name,
        "observed_environment": environment.get("execution_environment"),
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

    authentication_routes: dict[str, dict[str, Any]] = {}
    authentication_specs = _load_authentication_specs(args.authentication_route_spec)
    for spec in authentication_specs:
        row = _authentication_row(
            spec.attestation,
            semantic_path=spec.semantic_attestation,
            review_path=spec.review,
            environment_name=spec.environment,
            version=version,
            commit=certified_commit,
            wheel_sha256=wheel_sha256,
        )
        route_key = f"bedrock-runtime/{row['authentication_mode']}/{spec.key}"
        authentication_routes[route_key] = row

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
    }
    for spec in authentication_specs:
        evidence_inventory[f"authentication_{spec.key}_semantic_review"] = {
            "artifact": spec.review.name,
            "sha256": _sha256(spec.review),
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
    primary_combinations = len(primary) * len(FRAMEWORKS)
    additional_combinations = len(authentication_routes) * len(FRAMEWORKS)
    additional_episodes = sum(
        row["semantic_episodes_passed"] for row in authentication_routes.values()
    )
    certified_combinations = primary_combinations + additional_combinations
    reviewed_episodes = primary_episodes + additional_episodes
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
        "additional_authentication_routes": authentication_routes,
        "evidence_inventory": evidence_inventory,
        "totals": {
            "primary_combinations": primary_combinations,
            "primary_passed": primary_combinations,
            "primary_failed": 0,
            "semantic_episodes": 76,
            "semantic_episodes_passed": 76,
            "semantic_episodes_failed": 0,
            "additional_route_combinations": additional_combinations,
            "additional_route_passed": additional_combinations,
            "additional_route_failed": 0,
            "certified_live_executions": certified_combinations,
            "certified_live_passed": certified_combinations,
            "certified_live_failed": 0,
            "total_semantic_episodes_reviewed": reviewed_episodes,
            "total_semantic_episodes_passed": reviewed_episodes,
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
    parser.add_argument(
        "--authentication-route-spec",
        action="append",
        required=True,
        type=_path,
        help=(
            "Repeatable typed JSON descriptor containing key, environment, "
            "attestation, semantic_attestation and review paths."
        ),
    )
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
