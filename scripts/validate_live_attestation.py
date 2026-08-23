"""Validate a protected live-run artifact against one release candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic_systems.registry import FRAMEWORK_NAMES, provider_definition
from agentic_systems.schemas.attestation import (
    LiveAttestation,
    validate_live_attestation,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("attestation", type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--provider", default="vllm-runtime")
    args = parser.parse_args()

    provider = provider_definition(args.provider)
    payload = json.loads(args.attestation.read_text(encoding="utf-8"))
    evidence = LiveAttestation.model_validate(payload)
    validate_live_attestation(
        evidence,
        expected_commit_sha=args.commit,
        expected_wheel_sha256=args.wheel_sha256,
        required_environment_keys=provider.attestation_environment,
        require_model=provider.requires_model_identity,
        expected_pairs={(args.provider, framework) for framework in FRAMEWORK_NAMES},
    )
    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": evidence.schema_version,
                "cases": len(evidence.cases),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
