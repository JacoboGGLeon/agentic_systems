"""Run the bundled semantic matrix from the canonical ADA .env contract."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
MANIFEST_PATH = ROOT / "manifest.json"
RUNNER = Path(__file__).resolve().with_name("run_semantic_matrix.py")
FRAMEWORKS = ("native", "langgraph", "openai-agents", "strands")
PROVIDERS = {
    "python-runtime",
    "openai-runtime",
    "ollama-runtime",
    "bedrock-runtime",
    "vllm-runtime",
}


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing canonical configuration {path}; copy .env.example to .env."
        )
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            os.environ[key] = value.strip().strip('"').strip("'")


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def main() -> int:
    _load_dotenv(ENV_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    provider = os.getenv("AGENTIC_SYSTEMS_PROVIDER", "").strip()
    if provider == "auto" or provider not in PROVIDERS:
        raise ValueError(
            "AGENTIC_SYSTEMS_PROVIDER must select one explicit canonical provider; "
            f"observed {provider!r}."
        )
    if provider != "python-runtime" and not _enabled("RUN_SEMANTIC_MATRIX_LIVE"):
        raise RuntimeError(
            "Set RUN_SEMANTIC_MATRIX_LIVE=1 in the canonical .env to authorize "
            "the live semantic matrix."
        )

    wheel_name = str(manifest["wheel"]["filename"])
    wheel = ROOT / "artifacts" / wheel_name
    certified_commit = str(manifest["provenance"]["certified_commit"])
    output_dir = ROOT / "outputs"
    output_dir.mkdir(exist_ok=True)
    attestation = output_dir / f"{provider}-semantic-attestation.json"
    review = output_dir / f"{provider}-semantic-review.md"

    command = [
        sys.executable,
        str(RUNNER),
        "--wheel",
        str(wheel),
        "--output",
        str(attestation),
        "--review",
        str(review),
        "--commit",
        certified_commit,
        "--env",
        str(ENV_PATH),
        "--providers",
        provider,
        "--frameworks",
        *FRAMEWORKS,
    ]
    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode:
        return completed.returncode

    evidence = json.loads(attestation.read_text(encoding="utf-8"))
    provider_evidence = evidence["environment"]["providers"][provider]
    authentication = provider_evidence.get("authentication") or {}
    if provider == "bedrock-runtime" and (
        authentication.get("authentication_mode") != "aws-credential-chain"
        or not authentication.get("has_credentials")
        or authentication.get("bedrock_api_key_configured")
    ):
        raise RuntimeError(
            "Bedrock semantic execution did not use the AWS credential chain."
        )

    summary = evidence["summary"]
    expected_episodes = 16 if provider != "python-runtime" else 12
    if (
        summary["total"] != 4
        or summary["passed"] != 4
        or summary["failed"] != 0
        or summary["episodes_total"] != expected_episodes
        or summary["episodes_passed"] != expected_episodes
        or summary["episodes_failed"] != 0
    ):
        raise RuntimeError(f"Semantic ADA gate failed: {summary}")
    print(
        json.dumps(
            {
                "ok": True,
                "provider": provider,
                "frameworks": list(FRAMEWORKS),
                "summary": summary,
                "authentication_mode": authentication.get("authentication_mode"),
                "attestation": str(attestation.resolve()),
                "review": str(review.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
