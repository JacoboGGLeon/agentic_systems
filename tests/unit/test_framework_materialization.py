from __future__ import annotations

from types import SimpleNamespace

from agentic_systems.integrations.adapters.bedrock_openai import BedrockOpenAIModel
from agentic_systems.integrations.adapters.openai_agents import (
    _materialize_model as openai_model,
    _runner_kwargs,
)
from agentic_systems.integrations.adapters.openai_models import ScriptedOpenAIModel
from agentic_systems.integrations.adapters.strands import (
    _materialize_model as strands_model,
)
from agentic_systems.integrations.adapters.strands_scripted import ScriptedStrandsModel
from agentic_systems.providers.bedrock_runtime import BedrockRuntime


def _agent(provider: str, *, metadata=None):
    return SimpleNamespace(
        engine=provider,
        model=f"model-{provider}",
        runtime_config=SimpleNamespace(
            metadata=metadata or {},
            region_name="eu-west-1",
        ),
    )


def test_openai_agents_materializes_each_provider(monkeypatch):
    monkeypatch.delenv("VLLM_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    runtime = object()
    engine = SimpleNamespace(system=SimpleNamespace(_runtime=runtime, model="fallback"))

    assert openai_model(_agent("openai-runtime"), engine) == "model-openai-runtime"
    assert isinstance(
        openai_model(_agent("python-runtime"), engine), ScriptedOpenAIModel
    )

    bedrock = openai_model(_agent("bedrock-runtime"), engine)
    assert isinstance(bedrock, BedrockOpenAIModel)
    assert bedrock.runtime is runtime
    assert bedrock.model_id == "model-bedrock-runtime"

    calls = {}
    monkeypatch.setattr(
        "openai.AsyncOpenAI",
        lambda **kwargs: calls.setdefault("client", kwargs) or object(),
    )
    monkeypatch.setattr(
        "agents.OpenAIChatCompletionsModel",
        lambda **kwargs: calls.setdefault("model", kwargs) or object(),
    )
    vllm = _agent(
        "vllm-runtime",
        metadata={"vllm": {"base_url": "http://vllm.invalid/v1"}},
    )

    openai_model(vllm, engine)

    assert calls["client"]["base_url"] == "http://vllm.invalid/v1"
    assert calls["client"]["api_key"] == "vllm"
    assert calls["model"]["model"] == "model-vllm-runtime"

    calls.clear()
    ollama = _agent(
        "ollama-runtime",
        metadata={"ollama": {"base_url": "http://ollama.invalid/v1"}},
    )

    openai_model(ollama, engine)

    assert calls["client"]["base_url"] == "http://ollama.invalid/v1"
    assert calls["client"]["api_key"] == "ollama"
    assert calls["model"]["model"] == "model-ollama-runtime"


def test_openai_agents_disables_vendor_tracing_for_non_openai_providers():
    from agents import RunConfig

    for provider in (
        "bedrock-runtime",
        "ollama-runtime",
        "vllm-runtime",
        "python-runtime",
    ):
        configured = _runner_kwargs(_agent(provider), {})
        assert configured["run_config"].tracing_disabled is True

    assert _runner_kwargs(_agent("openai-runtime"), {}) == {}

    explicit = RunConfig(tracing_disabled=False)
    configured = _runner_kwargs(
        _agent("bedrock-runtime"), {"run_config": explicit, "context": "user"}
    )
    assert configured == {"run_config": explicit, "context": "user"}


def test_strands_materializes_each_provider(monkeypatch):
    monkeypatch.delenv("VLLM_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bedrock_calls = {}
    openai_calls = []

    class FakeOpenAIModel:
        def __init__(self, **kwargs):
            openai_calls.append(kwargs)

        def format_request(self, messages, tool_specs=None, **kwargs):
            return {
                "messages": messages,
                "tools": tool_specs,
                **kwargs,
            }

    monkeypatch.setattr(
        "strands.models.BedrockModel",
        lambda **kwargs: bedrock_calls.update(kwargs) or object(),
    )
    monkeypatch.setattr(
        "strands.models.openai.OpenAIModel",
        FakeOpenAIModel,
    )

    assert isinstance(
        strands_model(_agent("python-runtime"), object()),
        ScriptedStrandsModel,
    )
    session = object()
    strands_model(
        _agent("bedrock-runtime"),
        SimpleNamespace(
            system=SimpleNamespace(
                _runtime=SimpleNamespace(
                    session=session,
                    auth_mode="aws-credential-chain",
                    streaming=False,
                )
            )
        ),
    )
    strands_model(_agent("openai-runtime"), object())
    strands_model(
        _agent(
            "vllm-runtime",
            metadata={"vllm": {"base_url": "http://vllm.invalid/v1"}},
        ),
        object(),
    )
    strands_model(
        _agent(
            "ollama-runtime",
            metadata={"ollama": {"base_url": "http://ollama.invalid/v1"}},
        ),
        object(),
    )

    assert bedrock_calls["model_id"] == "model-bedrock-runtime"
    assert bedrock_calls["region_name"] is None
    assert bedrock_calls["boto_session"] is session
    assert bedrock_calls["streaming"] is False
    assert bedrock_calls["boto_client_config"].signature_version == "v4"
    assert openai_calls[0] == {
        "model_id": "model-openai-runtime",
        "client_args": None,
    }
    assert openai_calls[1]["client_args"] == {
        "base_url": "http://vllm.invalid/v1",
        "api_key": "vllm",
    }
    assert openai_calls[2]["model_id"] == "model-ollama-runtime"
    assert openai_calls[2]["client_args"] == {
        "base_url": "http://ollama.invalid/v1",
        "api_key": "ollama",
    }

def test_strands_real_bedrock_model_accepts_canonical_runtime(monkeypatch):
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("BEDROCK_STREAMING", "0")
    runtime = BedrockRuntime(
        model_id="amazon.nova-micro-v1:0",
        region_name="us-east-1",
    )
    engine = SimpleNamespace(system=SimpleNamespace(_runtime=runtime))

    model = strands_model(_agent("bedrock-runtime"), engine)

    assert model.config["streaming"] is False
    assert model.client.meta.region_name == "us-east-1"
    assert model.client.meta.config.signature_version == "v4"
