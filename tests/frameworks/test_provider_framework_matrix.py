from __future__ import annotations

import json
from typing import Any

import pytest

import agentic_systems as toolkit
from agentic_systems.integrations.adapters.openai_models import ScriptedOpenAIModel
from agentic_systems.integrations.adapters.strands_scripted import ScriptedStrandsModel


PROVIDERS = (
    "python-runtime",
    "openai-runtime",
    "ollama-runtime",
    "vllm-runtime",
    "bedrock-runtime",
)
FRAMEWORKS = ("native", "langgraph", "openai-agents", "strands")


def echo(value: str) -> dict:
    return {"value": value}


class FakeProviderEngine:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    def run(self, agent: Any, input_value: Any, policy: Any, *, mode: str):
        self.calls += 1
        tool_result = agent.available_tools()[0].run(input_value)
        return toolkit.RunResult(
            text=json.dumps(tool_result.data),
            data=tool_result.data,
            ok=tool_result.ok,
            tool_events=tool_result.tool_events,
            engine=self.name,
            model=agent.model or self.name,
            mode=mode,
            meta={"fake_provider": self.name},
        )

    async def arun(self, agent: Any, input_value: Any, policy: Any, *, mode: str):
        return self.run(agent, input_value, policy, mode=mode)


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_provider_framework_matrix_invokes_selected_adapter_and_fake_provider(
    provider: str,
    framework: str,
    monkeypatch: pytest.MonkeyPatch,
):
    materialized: list[tuple[str, str]] = []

    def openai_model(agent: Any, engine: Any) -> ScriptedOpenAIModel:
        materialized.append((agent.engine, "openai-agents"))
        return ScriptedOpenAIModel()

    def strands_model(agent: Any, engine: Any) -> ScriptedStrandsModel:
        materialized.append((agent.engine, "strands"))
        return ScriptedStrandsModel(agent.model or agent.engine)

    monkeypatch.setattr(
        "agentic_systems.integrations.adapters.openai_agents._materialize_model",
        openai_model,
    )
    monkeypatch.setattr(
        "agentic_systems.integrations.adapters.strands._materialize_model",
        strands_model,
    )

    system = toolkit.AgenticSystem(model=f"fake-{provider}")
    agent = system.agent(
        name=f"{framework}-{provider}",
        instructions="Use the Tool.",
        tools=[toolkit.tool(echo, name=f"echo_{framework}_{provider}")],
        engine=provider,
        framework=framework,
    )
    provider_engine = FakeProviderEngine(provider)
    system._engines[provider] = provider_engine

    result = agent.run({"value": "matrix"})

    assert result.ok is True
    assert result.data["value"] == "matrix"
    assert result.engine == provider
    assert result.meta["framework_adapter"] == framework
    assert result.native_result is not None
    assert len(result.tool_events) == 1
    if framework in {"native", "langgraph"}:
        assert provider_engine.calls == 1
        assert materialized == []
    else:
        assert provider_engine.calls == 0
        assert materialized == [(provider, framework)]
