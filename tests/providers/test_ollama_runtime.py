from __future__ import annotations

import asyncio
from types import SimpleNamespace

import agentic_systems as toolkit
from agentic_systems.engines.names import OLLAMA_RUNTIME_ENGINE
from agentic_systems.providers.ollama_runtime import (
    OllamaRuntimeProvider,
    ollama_environment_snapshot,
    ollama_signal_present,
)


class FakeChatCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            tool_call = SimpleNamespace(
                id="call_1",
                function=SimpleNamespace(name="duplicar", arguments='{"value": 21}'),
            )
            message = SimpleNamespace(content="", tool_calls=[tool_call])
        else:
            message = SimpleNamespace(content="El resultado es 42.", tool_calls=[])
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message)],
            usage=usage,
        )


class FakeOllamaClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeChatCompletions())


class FakeAsyncChatCompletions:
    async def create(self, **kwargs):
        message = SimpleNamespace(content="Respuesta async Ollama.", tool_calls=[])
        usage = SimpleNamespace(prompt_tokens=3, completion_tokens=2, total_tokens=5)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message)],
            usage=usage,
        )


class FakeAsyncOllamaClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeAsyncChatCompletions())


@toolkit.tool
def duplicar(value: int) -> dict:
    return {"result": value * 2}


def test_ollama_runtime_provider_runs_openai_compatible_tool_loop() -> None:
    runtime = toolkit.runtime(provider="ollama-runtime", model="qwen3:4b")
    system = toolkit.system(runtime=runtime, model="qwen3:4b")
    provider = OllamaRuntimeProvider(system, client=FakeOllamaClient())
    agent = system.agent(
        name="qwen",
        instructions="Usa tools cuando sea necesario.",
        tools=[duplicar],
        engine="ollama-runtime",
        runtime=runtime,
    )

    result = provider.run(
        agent,
        "Duplica 21 usando la tool.",
        toolkit.RunPolicy(max_turns=4),
        mode="eval",
    )

    assert result.ok is True
    assert result.engine == OLLAMA_RUNTIME_ENGINE
    assert result.meta["runtime_engine"] == OLLAMA_RUNTIME_ENGINE
    assert result.meta["execution_engine"] == OLLAMA_RUNTIME_ENGINE
    assert result.tool_events[0].name == "duplicar"
    assert result.tool_events[0].id.startswith("tool-")
    assert result.tool_events[0].id != result.tool_events[0].name
    assert result.tool_events[0].meta["provider_tool_call_id"] == "call_1"
    assert result.tool_events[0].output["result"] == 42
    assert result.usage["total_tokens"] == 15
    assert (
        result.meta["source_result_type"] == "ollama.openai_compatible.chat.completions"
    )

    repeated_provider = OllamaRuntimeProvider(system, client=FakeOllamaClient())
    repeated = repeated_provider.run(
        agent,
        "Duplica 21 otra vez usando la tool.",
        toolkit.RunPolicy(max_turns=4),
        mode="eval",
    )
    event_ids = [result.tool_events[0].id, repeated.tool_events[0].id]
    assert len(event_ids) == len(set(event_ids))
    assert repeated.check_invariants().ok is True


def test_ollama_missing_tools_and_async_execution() -> None:
    runtime = toolkit.runtime(provider="ollama-runtime", model="qwen3:4b")
    provider = OllamaRuntimeProvider(
        client=FakeOllamaClient(),
        async_client=FakeAsyncOllamaClient(),
    )
    missing_agent = toolkit.Agent(name="empty", tools=[], runtime=runtime)

    missing = provider.run(
        missing_agent,
        "Hola",
        toolkit.RunPolicy(max_turns=1),
    )

    assert missing.ok is False
    assert missing.engine == OLLAMA_RUNTIME_ENGINE
    assert missing.data["error"]["code"] == "missing_tools"

    system = toolkit.system(runtime=runtime, model="qwen3:4b")
    agent = system.agent(
        name="qwen_async",
        instructions="Responde.",
        tools=[duplicar],
        engine="ollama-runtime",
        runtime=runtime,
    )
    result = asyncio.run(
        provider.arun(
            agent,
            "Contesta sin tools.",
            toolkit.RunPolicy(max_turns=1),
            mode="eval",
        )
    )

    assert result.ok is True
    assert result.engine == OLLAMA_RUNTIME_ENGINE
    assert result.text == "Respuesta async Ollama."
    assert result.usage["total_tokens"] == 5


def test_ollama_environment_snapshot_is_non_secret(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("OLLAMA_API_KEY", "secret-value")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")

    snapshot = ollama_environment_snapshot()

    assert snapshot["base_url"] == "http://127.0.0.1:11434/v1"
    assert snapshot["base_url_configured"] is True
    assert snapshot["model"] == "qwen3:4b"
    assert snapshot["api_key_configured"] is True
    assert "secret-value" not in str(snapshot)
    assert ollama_signal_present() is True


def test_ollama_environment_clients_defaults_and_engine(monkeypatch) -> None:
    import agentic_systems.providers.ollama_runtime as ollama_module

    created = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            created["sync"] = kwargs

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            created["async"] = kwargs

    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.setattr(
        ollama_module,
        "_openai_module",
        lambda: SimpleNamespace(
            OpenAI=FakeOpenAI,
            AsyncOpenAI=FakeAsyncOpenAI,
        ),
    )

    provider = OllamaRuntimeProvider()
    provider._client_from_environment()
    provider._async_client_from_environment()

    expected = {
        "base_url": "http://127.0.0.1:11434/v1",
        "api_key": "ollama",
    }
    assert created["sync"] == expected
    assert created["async"] == expected

    system = toolkit.system(runtime=toolkit.runtime(provider="ollama-runtime"))
    assert isinstance(system._engine("ollama-runtime"), OllamaRuntimeProvider)


class FakeEmptyChatCompletions:
    def create(self, **kwargs):
        message = SimpleNamespace(content="", tool_calls=[])
        usage = SimpleNamespace(
            prompt_tokens=12, completion_tokens=1024, total_tokens=1036
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message)],
            usage=usage,
        )


class FakeEmptyOllamaClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeEmptyChatCompletions())


def test_ollama_empty_completion_is_structured_failure() -> None:
    runtime = toolkit.runtime(provider="ollama-runtime", model="qwen3:4b-thinking")
    system = toolkit.system(runtime=runtime, model="qwen3:4b-thinking")
    provider = OllamaRuntimeProvider(system, client=FakeEmptyOllamaClient())
    agent = system.agent(
        name="empty_completion",
        instructions="Return a concrete answer.",
        tools=[duplicar],
        engine="ollama-runtime",
        runtime=runtime,
    )

    result = provider.run(
        agent,
        "Answer after any internal reasoning.",
        toolkit.RunPolicy(max_turns=1, max_tokens=1024),
    )

    assert result.ok is False
    assert result.engine == OLLAMA_RUNTIME_ENGINE
    assert result.data["error"]["code"] == "empty_model_output"
    assert result.usage["completion_tokens"] == 1024
