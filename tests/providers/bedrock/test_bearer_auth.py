from __future__ import annotations

import boto3
import pytest


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
