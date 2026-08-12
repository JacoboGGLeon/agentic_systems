from __future__ import annotations

from types import SimpleNamespace

from agentic_systems.integrations.adapters.bedrock_openai import BedrockOpenAIModel
from agentic_systems.integrations.adapters.openai_agents import (
    _materialize_model as openai_model,
)
from agentic_systems.integrations.adapters.openai_models import ScriptedOpenAIModel
from agentic_systems.integrations.adapters.strands import (
    _materialize_model as strands_model,
)
from agentic_systems.integrations.adapters.strands_scripted import ScriptedStrandsModel


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


def test_strands_materializes_each_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bedrock_calls = {}
    openai_calls = []
    monkeypatch.setattr(
        "strands.models.BedrockModel",
        lambda **kwargs: bedrock_calls.update(kwargs) or object(),
    )
    monkeypatch.setattr(
        "strands.models.openai.OpenAIModel",
        lambda **kwargs: openai_calls.append(kwargs) or object(),
    )

    assert isinstance(
        strands_model(_agent("python-runtime"), object()),
        ScriptedStrandsModel,
    )
    strands_model(_agent("bedrock-runtime"), object())
    strands_model(_agent("openai-runtime"), object())
    strands_model(
        _agent(
            "vllm-runtime",
            metadata={"vllm": {"base_url": "http://vllm.invalid/v1"}},
        ),
        object(),
    )

    assert bedrock_calls == {
        "model_id": "model-bedrock-runtime",
        "region_name": "eu-west-1",
    }
    assert openai_calls[0] == {
        "model_id": "model-openai-runtime",
        "client_args": None,
    }
    assert openai_calls[1]["client_args"] == {
        "base_url": "http://vllm.invalid/v1",
        "api_key": "vllm",
    }
