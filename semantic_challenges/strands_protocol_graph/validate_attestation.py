"""Validate a frozen Strands protocol graph attestation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .run_matrix import challenge_sha256


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("attestation", type=Path)
    parser.add_argument("--providers", nargs="+")
    parser.add_argument(
        "--require-bedrock-auth",
        choices=("bedrock-api-key", "aws-credential-chain"),
    )
    args = parser.parse_args()
    payload = json.loads(args.attestation.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "agentic_systems.semantic-challenge-attestation.v1"
    assert payload["challenge"] == "strands-protocol-graph"
    assert payload["challenge_sha256"] == challenge_sha256()
    cells = payload["cells"]
    assert payload["summary"]["failed"] == 0
    assert all(cell["ok"] and cell["manual_review"]["ok"] for cell in cells)
    observed = [cell["provider"] for cell in cells]
    if args.providers:
        assert observed == args.providers, (observed, args.providers)
    for cell in cells:
        route = cell["manual_review"]["observed"]
        assert route["system_framework"] == "langgraph"
        assert route["candidate_framework"] == "strands"
        assert route["graph_native_type"] == "CompiledStateGraph"
        assert route["tool_path"] == ["fetch_mcp_evidence", "fetch_a2a_evidence"]
        assert route["judge_provider"] == "python-runtime"
        assert route["judge_framework"] == "native"
    if args.require_bedrock_auth:
        bedrock = next(cell for cell in cells if cell["provider"] == "bedrock-runtime")
        assert bedrock["authentication"]["authentication_mode"] == args.require_bedrock_auth
    print(json.dumps({"ok": True, "cells": len(cells), "providers": observed}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
