from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "semantic_matrix_contract", SCRIPTS / "run_semantic_matrix.py"
)
assert SPEC is not None and SPEC.loader is not None
SEMANTIC_MATRIX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SEMANTIC_MATRIX)


def test_attestation_redaction_preserves_usage_tokens_and_removes_credentials() -> None:
    payload = {
        "usage": {
            "input_tokens": 10,
            "output_tokens": 3,
            "total_tokens": 13,
            "completion_tokens": 3,
            "prompt_tokens": 10,
        },
        "OPENAI_API_KEY": "not-a-real-secret",
        "AWS_BEARER_TOKEN_BEDROCK": "not-a-real-token",
        "AWS_SESSION_TOKEN": "not-a-real-session",
    }

    sanitized = SEMANTIC_MATRIX._safe(payload)

    assert sanitized["usage"] == payload["usage"]
    assert "OPENAI_API_KEY" not in sanitized
    assert "AWS_BEARER_TOKEN_BEDROCK" not in sanitized
    assert "AWS_SESSION_TOKEN" not in sanitized
