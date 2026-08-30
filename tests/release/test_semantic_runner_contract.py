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
        "authentication": {
            "authentication_mode": "aws-credential-chain",
            "credential_method": "container-role",
            "bedrock_api_key_configured": False,
            "has_credentials": True,
            "sts_identity_available": True,
        },
    }

    sanitized = SEMANTIC_MATRIX._safe(payload)

    assert sanitized["usage"] == payload["usage"]
    assert "OPENAI_API_KEY" not in sanitized
    assert "AWS_BEARER_TOKEN_BEDROCK" not in sanitized
    assert "AWS_SESSION_TOKEN" not in sanitized
    assert sanitized["authentication"] == payload["authentication"]


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
    assert module.looks_like_short_poem("A shadow stretches,\n323,\nSoft winds answer.")
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
    assert punctuated["answer"].startswith(
        'The normalized text is "Already complete." It'
    )
    assert '". It' not in punctuated["answer"]
    assert unpunctuated["answer"].startswith(
        'The normalized text is "Needs punctuation". It'
    )


def test_model_judge_uses_typed_evidence_backed_violations(monkeypatch) -> None:
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
    assert set(properties) == {"violations"}
    assert properties["violations"]["type"] == "array"
    violation_schema = schema["$defs"]["SemanticViolation"]
    assert set(violation_schema["properties"]["criterion"]["enum"]) == set(
        module.JudgeCriteria.model_fields
    )
    assert violation_schema["properties"]["evidence"]["minLength"] == 1
    assert violation_schema["properties"]["evidence"]["maxLength"] == 1000

    passed = module.record_semantic_judgment.function(
        module.SemanticJudgmentInput(violations=[])
    )
    failed = module.record_semantic_judgment.function(
        module.SemanticJudgmentInput(
            violations=[
                {"criterion": "clarity", "evidence": "Answer is unreadable."},
                {
                    "criterion": "no_technical_noise",
                    "evidence": "Answer exposed an implementation envelope.",
                },
            ]
        )
    )
    assert passed["score"] == 1.0
    assert set(passed["criteria"].values()) == {1.0}
    assert failed["criteria"]["clarity"] == 0.0
    assert failed["criteria"]["no_technical_noise"] == 0.0
    assert failed["criteria"]["evidence_correctness"] == 1.0
    assert [item["criterion"] for item in failed["findings"]] == [
        "clarity",
        "no_technical_noise",
    ]
    assert "implementation envelope" in failed["rationale"]

    monkeypatch.delenv("AGENTIC_SYSTEMS_SEMANTIC_JUDGE_MAX_TOKENS", raising=False)
    assert module.semantic_judge_max_tokens() == 4096
    monkeypatch.setenv("AGENTIC_SYSTEMS_SEMANTIC_JUDGE_MAX_TOKENS", "900")
    cell = module.build_semantic_cell("openai-runtime", "native", model="gpt-4.1-mini")
    assert cell.judge.agent.policy.max_tool_calls == 1
    assert cell.judge.agent.policy.max_turns == 5
    assert cell.judge.agent.policy.repair is True
    assert cell.judge.agent.policy.max_tokens == 900


def test_attestation_binds_external_gate_assets_by_hash() -> None:
    source = (SCRIPTS / "run_semantic_matrix.py").read_text(encoding="utf-8")

    assert '"gate_assets"' in source
    assert '"runner"' in source
    assert '"application"' in source


def test_bedrock_semantic_environment_records_authentication_mode(
    monkeypatch,
) -> None:
    class Runtime:
        def describe(self):
            return {"selected_provider": "bedrock-runtime", "region": "us-east-2"}

    monkeypatch.setattr(SEMANTIC_MATRIX.toolkit, "runtime", lambda **kwargs: Runtime())
    monkeypatch.setattr(
        SEMANTIC_MATRIX.toolkit,
        "boto3_session_snapshot",
        lambda **kwargs: {
            "authentication_mode": "aws-credential-chain",
            "has_credentials": True,
            "bedrock_api_key_configured": False,
        },
    )
    monkeypatch.setattr(
        SEMANTIC_MATRIX,
        "_model",
        lambda provider: "us.amazon.nova-pro-v1:0",
    )

    environment = SEMANTIC_MATRIX._environment(ROOT / ".env", ("bedrock-runtime",))

    authentication = environment["providers"]["bedrock-runtime"]["authentication"]
    assert authentication["authentication_mode"] == "aws-credential-chain"
    assert authentication["has_credentials"] is True
    assert authentication["bedrock_api_key_configured"] is False


def test_ada_semantic_wrapper_uses_dotenv_and_all_frameworks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "ada_semantic_matrix", SCRIPTS / "run_ada_semantic_matrix.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "AGENTIC_SYSTEMS_PROVIDER=bedrock-runtime\nRUN_SEMANTIC_MATRIX_LIVE=1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTIC_SYSTEMS_PROVIDER", "openai-runtime")

    module._load_dotenv(dotenv)

    providers, frameworks = module._matrix_contract(
        {
            "providers": ["bedrock-runtime"],
            "frameworks": ["native", "langgraph", "openai-agents", "strands"],
        }
    )
    assert providers == {"bedrock-runtime"}
    assert frameworks == ("native", "langgraph", "openai-agents", "strands")
    assert module._enabled("RUN_SEMANTIC_MATRIX_LIVE") is True
    assert module.os.environ["AGENTIC_SYSTEMS_PROVIDER"] == "bedrock-runtime"
