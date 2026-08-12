from __future__ import annotations

import json
import pytest

import agentic_systems.bedrock_runtime_client as brc
import agentic_systems.providers.bedrock_runtime as bedrock_provider


class Body:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeRuntimeAPI:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {"embedding": [1.0, 2.0]}
        self.error = error
        self.calls = []

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return {"body": Body(self.payload)}


class FakeBedrockRuntime:
    def __init__(
        self,
        *,
        model_id,
        region_name,
        max_tokens_default,
        temperature_default,
        disable_openai_runtime_tracing,
    ):
        self.model_id = model_id
        self.region_name = region_name or "us-test-1"
        self.max_tokens_default = max_tokens_default
        self.temperature_default = temperature_default
        self.disable_openai_runtime_tracing = disable_openai_runtime_tracing
        self.runtime = FakeRuntimeAPI()
        self.raise_whoami = False
        self.raise_model_availability = False

    def whoami(self, *, mask=True):
        if self.raise_whoami:
            raise RuntimeError("identity denied")
        return {"ok": True, "mask": mask, "account": "123"}

    def model_availability(self, model_id, *, full_metadata):
        if self.raise_model_availability:
            raise RuntimeError("metadata denied")
        return {"ok": True, "model_id": model_id, "full_metadata": full_metadata}

    def run_direct(self, prompt, **kwargs):
        self.last_prompt = prompt
        self.last_kwargs = kwargs
        return {
            "final_text": f"answer: {prompt}",
            "raw_responses": [],
            "tool_calls": [],
        }


class AwsLikeError(Exception):
    response = {"Error": {"Code": "Denied", "Message": "No access"}}


def test_bedrock_runtime_client_with_fake_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(brc, "_import_bedrock_runtime", lambda: FakeBedrockRuntime)

    client = brc.BedrockRuntimeClient(
        model="model-a",
        region="us-east-1",
        defaults={"max_tokens": 10, "temperature": 0.25},
        disable_framework_tracing=False,
    )

    assert client.runtime.model_id == "model-a"
    assert client.profile()["defaults"]["max_tokens"] == 10
    assert (
        client.whoami(check_language_model=True, check_embedding_model=True)["ok"]
        is True
    )

    client.runtime.raise_whoami = True
    client.runtime.raise_model_availability = True
    failed = client.whoami(check_language_model=True, check_embedding_model=True)
    assert failed["ok"] is False
    assert failed["identity"]["error_type"] == "RuntimeError"
    assert failed["language_model_availability"]["ok"] is False
    assert failed["embedding_model_availability"]["ok"] is False

    result = client.complete(
        "hola",
        instructions="inst",
        model="model-b",
        max_tokens=5,
        temperature=0.1,
        mode="eval",
    )
    assert result.text == "answer: hola"
    assert result.engine == "bedrock-runtime"
    assert result.model == "model-b"
    assert client.runtime.last_kwargs["max_tool_calls"] == 0

    markdown = tmp_path / "doc.md"
    markdown.write_text("# Titulo\nDato: 42", encoding="utf-8")
    read = client.read_markdown(markdown)
    assert read["lines"] == 2
    answer = client.answer_from_markdown(path=markdown, question="Dato?", mode="eval")
    assert answer.data["kind"] == "markdown_answer"
    assert "content" not in answer.data["source"]


def test_bedrock_runtime_client_embeddings_and_helpers(monkeypatch):
    monkeypatch.setattr(brc, "_import_bedrock_runtime", lambda: FakeBedrockRuntime)
    client = brc.BedrockRuntimeClient(
        model="model-a", embedding_model="amazon.titan-embed-text-v2:0"
    )

    single = client.embed("texto")
    assert single["ok"] is True
    assert single["dimensions"] == 2
    invoked = client.runtime.runtime.calls[-1]
    assert invoked["modelId"] == "amazon.titan-embed-text-v2:0"
    assert json.loads(invoked["body"].decode("utf-8")) == {"inputText": "texto"}

    client.runtime.runtime = FakeRuntimeAPI(
        {"embeddings": [{"embedding": [1.0]}, {"bad": []}, {"embedding": [2.0]}]}
    )
    multi = client.embed(["a", "b"], model="cohere.embed", input_type="search_query")
    assert multi["embedding_count"] == 2

    client.runtime.runtime = FakeRuntimeAPI({"vectors": [[1.0, 2.0, 3.0]]})
    vectors = client.embed(["a"], model="custom.embed")
    assert vectors["dimensions"] == 3

    client.runtime.runtime = FakeRuntimeAPI(error=AwsLikeError("denied"))
    failed = client.embed("x")
    assert failed["ok"] is False
    assert failed["error_code"] == "Denied"

    with pytest.raises(ValueError, match="No embedding model configured"):
        brc.BedrockRuntimeClient(model="model-a", embedding_model=None).embed("x")
    with pytest.raises(ValueError, match="at least one text"):
        client.embed([])

    assert (
        brc._embedding_payload("cohere.embed", ["a"], input_type=None)["input_type"]
        == "search_document"
    )
    assert brc._embedding_payload("titan.embed", ["a", "b"], input_type=None) == {
        "inputText": "a\n\nb"
    }
    assert brc._embedding_payload("custom.embed", ["a"], input_type="query") == {
        "texts": ["a"],
        "input_type": "query",
    }
    assert brc._extract_embeddings("bad") == []
    assert brc._extract_embeddings({"embeddings": [[1.0]]}) == [[1.0]]
    assert brc._extract_embeddings({}) == []


def test_bedrock_provider_exports_runtime_implementation():
    assert bedrock_provider.BedrockRuntime.__name__ == "BedrockRuntime"
    assert bedrock_provider.BedrockRunResult.__name__ == "BedrockRunResult"
    assert bedrock_provider.RuntimeToolCallRecord.__name__ == "RuntimeToolCallRecord"
    assert bedrock_provider.RuntimeToolSpec.__name__ == "RuntimeToolSpec"
    assert bedrock_provider.ToolEnvelope.__name__ == "ToolEnvelope"
    assert set(bedrock_provider.__all__) >= {
        "BedrockRuntime",
        "BedrockRunResult",
        "RuntimeToolCallRecord",
        "RuntimeToolSpec",
        "ToolEnvelope",
    }


def test_bedrock_compact_response_metadata_keeps_latency_fields() -> None:
    response = {
        "ResponseMetadata": {"RequestId": "abc", "HTTPStatusCode": 200},
        "usage": {"inputTokens": 1, "outputTokens": 2, "totalTokens": 3},
        "metrics": {"latencyMs": 123},
        "agentic_systems": {"client_duration_ms": 130.5},
        "stopReason": "end_turn",
    }

    compact = bedrock_provider.BedrockRuntime._compact_response_metadata(response)

    assert compact["service_latency_ms"] == 123
    assert compact["client_duration_ms"] == 130.5
