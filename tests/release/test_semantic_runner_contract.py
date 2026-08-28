from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


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
    assert module.looks_like_short_poem(
        "Golden sunflowers sway,\n323\nMoonlight on still waters."
    )
    assert module.looks_like_short_poem(
        "A shadow stretches,\n323,\nSoft winds answer."
    )
    assert module.looks_like_short_poem(
        "Moonlight touches water,\n3 2 3\nLeaves whisper softly."
    )
    assert not module.looks_like_short_poem("🌟\n323\n🌙")
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
    assert "Do not use emoji-only lines" in module._case_input(
        "openai-runtime", "poetic_calculation"
    )

    assert module.supports_model_generation("python-runtime") is False
    for provider in (
        "openai-runtime",
        "ollama-runtime",
        "bedrock-runtime",
        "vllm-runtime",
    ):
        assert module.supports_model_generation(provider) is True

    python_cases = module.semantic_cases("python-runtime", "native")
    openai_poem = next(
        case
        for case in module.semantic_cases("openai-runtime", "native")
        if case["name"] == "poetic_calculation"
    )
    assert [case["name"] for case in python_cases] == [
        "calculation",
        "text_analysis",
        "out_of_scope",
    ]
    assert openai_poem["expected"]["output_style"] == "short-poem-exactly-three-lines"

    with pytest.raises(ValueError, match="does not declare model_generation"):
        module._case_input("python-runtime", "poetic_calculation")


def test_deterministic_multiply_exposes_only_public_evidence() -> None:
    spec = importlib.util.spec_from_file_location(
        "semantic_e2e_public_evidence", SCRIPTS / "semantic_e2e_application.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    output = module.multiply.function(a=17, b=19)

    assert output == {"result": 323, "answer": "Verified product: 323."}
    assert "continue" not in output["answer"].lower()

    punctuated = module.analyze_text.function(text="Already complete.")
    unpunctuated = module.analyze_text.function(text="Needs punctuation")
    assert punctuated["answer"].startswith('The normalized text is "Already complete." It')
    assert '". It' not in punctuated["answer"]
    assert unpunctuated["answer"].startswith(
        'The normalized text is "Needs punctuation". It'
    )


def test_model_judge_uses_one_closed_failed_criteria_list(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "semantic_e2e_judge_contract", SCRIPTS / "semantic_e2e_application.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    from agentic_systems.integrations.adapters import strands

    schema = strands._tool_input_json_schema(
        module.record_semantic_judgment,
        module.record_semantic_judgment.function,
    )
    properties = schema["properties"]
    assert set(properties) == {"failed_criteria", "rationale"}
    assert properties["failed_criteria"]["type"] == "array"
    assert set(properties["failed_criteria"]["items"]["enum"]) == set(
        module.JudgeCriteria.model_fields
    )
    assert properties["rationale"]["minLength"] == 1
    assert properties["rationale"]["maxLength"] == 800

    passed = module.record_semantic_judgment.function(
        failed_criteria=[],
        rationale="All declared criteria passed.",
    )
    failed = module.record_semantic_judgment.function(
        failed_criteria=["clarity", "no_technical_noise"],
        rationale="The answer exposed an implementation envelope.",
    )
    assert passed["score"] == 1.0
    assert set(passed["criteria"].values()) == {1.0}
    assert failed["criteria"]["clarity"] == 0.0
    assert failed["criteria"]["no_technical_noise"] == 0.0
    assert failed["criteria"]["evidence_correctness"] == 1.0

    monkeypatch.setenv("AGENTIC_SYSTEMS_SEMANTIC_JUDGE_MAX_TOKENS", "900")
    cell = module.build_semantic_cell(
        "openai-runtime", "native", model="gpt-4.1-mini"
    )
    assert cell.judge.agent.policy.max_tool_calls == 2
    assert cell.judge.agent.policy.max_turns == 3
    assert cell.judge.agent.policy.repair is True
    assert cell.judge.agent.policy.max_tokens == 900


def test_attestation_binds_external_gate_assets_by_hash() -> None:
    source = (SCRIPTS / "run_semantic_matrix.py").read_text(encoding="utf-8")

    assert '"gate_assets"' in source
    assert '"runner"' in source
    assert '"application"' in source
