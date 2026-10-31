"""Borrowed authentication survives every adapter without live AWS calls."""

import json
import os
import threading

import boto3
from botocore.client import BaseClient
import pytest

import agentic_systems as toolkit
from agentic_systems._session import _leases, session_scope


class Session:
    region_name = "us-east-2"

    def __init__(self):
        self.created = []
        self.closed = False
        self.raw = boto3.Session(region_name=self.region_name,
                                 aws_access_key_id="offline-fixture-key",
                                 aws_secret_access_key="offline-fixture-secret")

    def client(self, service_name, **options):
        client = self.raw.client(service_name, **options)
        self.created.append((service_name, options, client))
        return client

    def get_credentials(self):
        raise AssertionError("Toolkit must not extract credentials from a borrowed session")

    def close(self):
        self.closed = True


def test_configuration_does_not_resolve_or_serialize_borrowed_resources():
    session = Session()
    config = toolkit.runtime(provider="bedrock-runtime", model="qwen-fixture", session=session)
    assert config.region == "us-east-2" and not session.created
    assert config._to_engine().session is session
    assert "session" not in config.model_dump()
    assert "offline-fixture" not in repr(config) + config.model_dump_json() + json.dumps(config.inspect())
    assert config.inspect()["session_configured"]
    assert "session" not in config._to_engine().to_dict()


@pytest.mark.parametrize("options", [
    {"provider": "python-runtime"},
    {"provider": "bedrock-runtime", "api_key": "explicit-key"},
    {"provider": "bedrock-runtime", "endpoint": "https://example.invalid"},
    {"provider": "bedrock-runtime", "region": "us-west-2"},
])
def test_session_connection_conflicts_fail_before_client_creation(options):
    session = Session()
    with pytest.raises(ValueError):
        toolkit.runtime(session=session, **options)
    assert not session.created


def test_invalid_session_and_region_are_rejected():
    with pytest.raises(ValueError, match="client interface"):
        toolkit.runtime(provider="bedrock-runtime", session=object())
    session = Session()
    session.region_name = 3
    with pytest.raises(ValueError, match="region_name"):
        toolkit.runtime(provider="bedrock-runtime", session=session)


@pytest.mark.parametrize("framework", ["native", "openai-agents", "strands"])
def test_real_sdk_adapters_use_borrowed_session_with_explicit_iam(monkeypatch, framework):
    monkeypatch.delenv("AWS_EC2_METADATA_DISABLED", raising=False)
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "offline-env-bearer")
    monkeypatch.setenv("OPENAI_AGENTS_DISABLE_TRACING", "1")
    from agents import set_tracing_disabled
    set_tracing_disabled(True)
    calls = []

    def converse(client, operation, arguments):
        assert operation == "Converse"
        assert client._request_signer._signature_version == "v4"
        calls.append(arguments)
        return {
            "output": {"message": {"role": "assistant", "content": [{"text": '{"value":7}'}]}},
            "stopReason": "end_turn", "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
            "metrics": {"latencyMs": 0},
            "ResponseMetadata": {"RequestId": "offline-session", "HTTPStatusCode": 200},
        }

    monkeypatch.setattr(BaseClient, "_make_api_call", converse)
    session = Session()
    config = toolkit.runtime(provider="bedrock-runtime", model="qwen-fixture", session=session,
                             max_tool_calls=0, max_turns=2, max_tokens=32)
    result = toolkit.Agent("session-test", runtime=config, framework=toolkit.framework(framework)).run("Return value 7")
    assert result.ok and "7" in result.text, result.to_dict()
    assert calls and all(call["modelId"] == "qwen-fixture" for call in calls)
    assert {name for name, _, _ in session.created} >= {"bedrock-runtime", "bedrock", "sts"}
    assert all(options["region_name"] == "us-east-2" for _, options, _ in session.created)
    assert not session.closed
    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "offline-env-bearer"
    assert "AWS_EC2_METADATA_DISABLED" not in os.environ
    assert "offline-fixture" not in json.dumps(result.to_dict())


def test_same_session_is_serialized_but_other_sessions_are_independent():
    session, other = object(), object()
    ready, release = threading.Event(), threading.Event()

    def hold():
        with session_scope(session, 1):
            ready.set()
            assert release.wait(2)

    worker = threading.Thread(target=hold)
    worker.start()
    assert ready.wait(1)
    try:
        with pytest.raises(TimeoutError):
            with session_scope(session, 0):
                pytest.fail("Concurrent session was not protected")
        with session_scope(other, 0):
            pass
    finally:
        release.set()
        worker.join(2)
    assert not worker.is_alive() and not _leases
    with session_scope(session, 0):
        with session_scope(session, 0):
            pass
    with pytest.raises(RuntimeError, match="cross processes"):
        with session_scope(session, 0, owner_pid=os.getpid() + 1):
            pytest.fail("Cross-process resource accepted")
    assert not _leases
