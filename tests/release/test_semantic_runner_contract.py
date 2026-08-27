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


def test_semantic_matrix_includes_vllm_and_uses_public_runtime_model_resolution(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VLLM_MODEL", "unsloth/Qwen3-0.6B")

    assert "vllm-runtime" in SEMANTIC_MATRIX.PROVIDERS
    assert SEMANTIC_MATRIX._model("vllm-runtime") == "unsloth/Qwen3-0.6B"


def test_poetic_case_requires_tool_evidence_and_textual_synthesis() -> None:
    application = (SCRIPTS / "semantic_e2e_application.py").read_text(encoding="utf-8")

    assert '"name": "poetic_calculation"' in application
    assert '"tool_path": ["delegate_calculator", "multiply"]' in application
    assert 'tool_choice="record_semantic_judgment"' in application
    assert 'completion="when_required_tools_satisfied"' in application
    assert "looks_like_short_poem" in application


def test_poem_shape_is_semantic_not_exact_text() -> None:
    spec = importlib.util.spec_from_file_location(
        "semantic_e2e_poem_contract", SCRIPTS / "semantic_e2e_application.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.looks_like_short_poem(
        "Measured paths meet beneath moonlight,\n323\nA verified product blooms in rhyme."
    )
    assert not module.looks_like_short_poem(
        "Seventeen meets nineteen,\nTheir measured paths combine,\nThree hundred twenty-three shines."
    )
    assert not module.looks_like_short_poem("The verified result is 323.")
    assert not module.looks_like_short_poem(
        "Thirty-two-three appears,\nBut arithmetic disagrees,\nThe wording lost the product."
    )
    assert not module.looks_like_short_poem(
        "Thirty-two-three stands tall,\nA product enters the light,\nVerified: 323."
    )
    assert not module.looks_like_short_poem(
        "The factors meet in light,\nTheir answer is 323,\nA final echo: 323."
    )

    assert module.supports_model_generation("python-runtime") is False
    for provider in (
        "openai-runtime",
        "ollama-runtime",
        "bedrock-runtime",
        "vllm-runtime",
    ):
        assert module.supports_model_generation(provider) is True

    python_poem = next(
        case
        for case in module.semantic_cases("python-runtime", "native")
        if case["name"] == "poetic_calculation"
    )
    openai_poem = next(
        case
        for case in module.semantic_cases("openai-runtime", "native")
        if case["name"] == "poetic_calculation"
    )
    assert python_poem["expected"]["output_style"] == "deterministic-evidence-control"
    assert openai_poem["expected"]["output_style"] == "short-poem-exactly-three-lines"


def test_attestation_binds_external_gate_assets_by_hash() -> None:
    source = (SCRIPTS / "run_semantic_matrix.py").read_text(encoding="utf-8")

    assert '"gate_assets"' in source
    assert '"runner"' in source
    assert '"application"' in source
