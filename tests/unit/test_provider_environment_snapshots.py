from __future__ import annotations

import os

import agentic_systems as toolkit


def test_provider_snapshots_load_nearest_dotenv_without_exposing_secrets(
    monkeypatch, tmp_path, request
) -> None:
    values = {
        "OPENAI_API_KEY": "openai-secret",
        "OPENAI_BASE_URL": "https://openai.example/v1",
        "OPENAI_MODEL": "openai-model",
        "OLLAMA_API_KEY": "ollama-secret",
        "OLLAMA_BASE_URL": "http://127.0.0.1:11434/v1",
        "OLLAMA_MODEL": "qwen3:4b",
        "VLLM_API_KEY": "vllm-secret",
        "VLLM_BASE_URL": "http://127.0.0.1:8000/v1",
        "VLLM_MODEL": "vllm-model",
        "AWS_BEARER_TOKEN_BEDROCK": "bedrock-secret",
        "AWS_REGION": "us-east-1",
    }

    def cleanup() -> None:
        for key in values:
            os.environ.pop(key, None)

    request.addfinalizer(cleanup)
    for key in values:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()),
        encoding="utf-8",
    )

    openai = toolkit.openai_environment_snapshot()
    ollama = toolkit.ollama_environment_snapshot()
    vllm = toolkit.vllm_environment_snapshot()
    aws = toolkit.aws_environment_snapshot()

    assert openai["api_key_configured"] is True
    assert openai["model"] == "openai-model"
    assert ollama["model"] == "qwen3:4b"
    assert vllm["model"] == "vllm-model"
    assert aws["AWS_BEARER_TOKEN_BEDROCK"] == "SET"
    assert toolkit.boto3_session_snapshot()["authentication_mode"] == (
        "bedrock-api-key"
    )

    rendered = repr((openai, ollama, vllm, aws))
    for secret in (
        "openai-secret",
        "ollama-secret",
        "vllm-secret",
        "bedrock-secret",
    ):
        assert secret not in rendered
