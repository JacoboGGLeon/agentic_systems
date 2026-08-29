"""Validate protected live-run artifacts against one release candidate."""

from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path

from agentic_systems.registry import FRAMEWORK_NAMES, provider_definition
from agentic_systems.schemas.attestation import (
    LIVE_ATTESTATION_SCHEMA_VERSION,
    SEMANTIC_ATTESTATION_SCHEMA_VERSION,
    LiveAttestation,
    SemanticAttestation,
    validate_live_attestation,
    validate_semantic_attestation,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("attestation", type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--provider", default="vllm-runtime")
    parser.add_argument("--providers", nargs="+")
    parser.add_argument("--frameworks", nargs="+", default=list(FRAMEWORK_NAMES))
    args = parser.parse_args()

    payload = json.loads(args.attestation.read_text(encoding="utf-8"))
    schema_version = payload.get("schema_version")
    if schema_version == LIVE_ATTESTATION_SCHEMA_VERSION:
        evidence = LiveAttestation.model_validate(payload)
        provider = provider_definition(args.provider)
        validate_live_attestation(
            evidence,
            expected_commit_sha=args.commit,
            expected_wheel_sha256=args.wheel_sha256,
            required_environment_keys=provider.attestation_environment,
            require_model=provider.requires_model_identity,
            expected_pairs={
                (args.provider, framework) for framework in FRAMEWORK_NAMES
            },
        )
        count = len(evidence.cases)
    elif schema_version == SEMANTIC_ATTESTATION_SCHEMA_VERSION:
        evidence = SemanticAttestation.model_validate(payload)
        if not args.providers:
            raise ValueError(
                "--providers is required for semantic attestations so the required "
                "matrix cannot be inferred from the evidence under validation"
            )
        providers = tuple(args.providers)
        frameworks = tuple(args.frameworks)
        for provider_name in providers:
            provider_definition(provider_name)
        unknown_frameworks = sorted(set(frameworks) - set(FRAMEWORK_NAMES))
        if unknown_frameworks:
            raise ValueError(f"Unknown framework(s): {unknown_frameworks}")
        validate_semantic_attestation(
            evidence,
            expected_commit_sha=args.commit,
            expected_wheel_sha256=args.wheel_sha256,
            expected_pairs=set(product(providers, frameworks)),
        )
        count = len(evidence.cells)
    else:
        raise ValueError(f"Unsupported attestation schema_version {schema_version!r}.")

    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": evidence.schema_version,
                "cases": count,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
