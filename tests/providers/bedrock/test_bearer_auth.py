from __future__ import annotations

import boto3
import pytest

from agentic_systems.providers.bedrock_runtime import BedrockRuntime


class _RequestCaptured(Exception):
    pass


def test_boto3_bedrock_runtime_uses_native_api_key_as_bearer_without_network(
    monkeypatch,
):
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-bedrock-api-key")
    session = boto3.Session()
    client = session.client("bedrock-runtime", region_name="us-east-1")
    captured: dict[str, str] = {}

    def capture(request, **_kwargs):
        authorization = request.headers.get("Authorization", b"")
        if isinstance(authorization, bytes):
            authorization = authorization.decode()
        captured["authorization"] = str(authorization)
        captured["host"] = request.url.split("/", 3)[2]
        raise _RequestCaptured

    client.meta.events.register(
        "before-send.bedrock-runtime.Converse",
        capture,
    )
    with pytest.raises(_RequestCaptured):
        client.converse(
            modelId="amazon.nova-micro-v1:0",
            messages=[{"role": "user", "content": [{"text": "probe"}]}],
        )

    assert captured["authorization"] == "Bearer test-bedrock-api-key"
    assert captured["host"] == "bedrock-runtime.us-east-1.amazonaws.com"


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, False), ("0", False), ("false", False), ("1", True), ("yes", True)],
)
def test_bedrock_streaming_is_selected_by_environment(monkeypatch, value, expected):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "")
    if value is None:
        monkeypatch.delenv("BEDROCK_STREAMING", raising=False)
    else:
        monkeypatch.setenv("BEDROCK_STREAMING", value)

    runtime = BedrockRuntime(
        model_id="amazon.nova-micro-v1:0",
        region_name="us-east-1",
    )

    assert runtime.streaming is expected


def test_bedrock_streaming_rejects_ambiguous_values(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "")
    monkeypatch.setenv("BEDROCK_STREAMING", "sometimes")

    with pytest.raises(ValueError, match="BEDROCK_STREAMING"):
        BedrockRuntime(
            model_id="amazon.nova-micro-v1:0",
            region_name="us-east-1",
        )


def test_blank_bedrock_api_key_uses_sigv4_credential_chain(monkeypatch):
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)

    runtime = BedrockRuntime(
        model_id="amazon.nova-micro-v1:0",
        region_name="us-east-1",
    )
    captured: dict[str, str] = {}

    def capture(request, **_kwargs):
        authorization = request.headers.get("Authorization", b"")
        if isinstance(authorization, bytes):
            authorization = authorization.decode()
        captured["authorization"] = str(authorization)
        raise _RequestCaptured

    runtime.runtime.meta.events.register(
        "before-send.bedrock-runtime.Converse",
        capture,
    )
    with pytest.raises(_RequestCaptured):
        runtime.runtime.converse(
            modelId=runtime.model_id,
            messages=[{"role": "user", "content": [{"text": "probe"}]}],
        )

    assert runtime.auth_mode == "aws-credential-chain"
    assert runtime.runtime.meta.config.signature_version == "v4"
    assert captured["authorization"].startswith("AWS4-HMAC-SHA256 ")
    assert "Bearer" not in captured["authorization"]
