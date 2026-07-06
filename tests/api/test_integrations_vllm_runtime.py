from __future__ import annotations

from types import SimpleNamespace

import agentic_systems as toolkit
from agentic_systems.engines.names import VLLM_RUNTIME_ENGINE
from agentic_systems.providers.vllm_runtime import VLLMRuntimeProvider, vllm_environment_snapshot, vllm_signal_present


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
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


class FakeVLLMClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeChatCompletions())


@toolkit.tool
def duplicar(value: int) -> dict:
    return {"result": value * 2}


def test_vllm_runtime_provider_runs_openai_compatible_tool_loop() -> None:
    runtime = toolkit.runtime(provider="vllm-runtime", model="Qwen/Qwen3-0.6B")
    system = toolkit.AgenticSystem(runtime=runtime, model="Qwen/Qwen3-0.6B")
    provider = VLLMRuntimeProvider(system, client=FakeVLLMClient())
    agent = system.agent(name="qwen", instructions="Usa tools cuando sea necesario.", tools=[duplicar], engine="vllm-runtime", runtime=runtime)

    result = provider.run(agent, "Duplica 21 usando la tool.", toolkit.RunPolicy(max_turns=4), mode="eval")

    assert result.ok is True
    assert result.engine == VLLM_RUNTIME_ENGINE
    assert result.meta["runtime_engine"] == VLLM_RUNTIME_ENGINE
    assert result.meta["execution_engine"] == VLLM_RUNTIME_ENGINE
    assert result.tool_events[0].name == "duplicar"
    assert result.tool_events[0].output["result"] == 42
    assert result.usage["total_tokens"] == 15
    assert result.meta["source_result_type"] == "vllm.openai_compatible.chat.completions"


def test_vllm_runtime_provider_reports_missing_tools_with_vllm_engine() -> None:
    runtime = toolkit.runtime(provider="vllm-runtime", model="Qwen/Qwen3-0.6B")
    provider = VLLMRuntimeProvider(client=FakeVLLMClient())
    agent = toolkit.Agent(name="qwen", tools=[], runtime=runtime)

    result = provider.run(agent, "Hola", toolkit.RunPolicy(max_turns=1))

    assert result.ok is False
    assert result.engine == VLLM_RUNTIME_ENGINE
    assert result.data["error"]["code"] == "missing_tools"
    assert result.meta["runtime_engine"] == VLLM_RUNTIME_ENGINE


def test_agentic_system_can_create_vllm_runtime_engine() -> None:
    system = toolkit.AgenticSystem(model="Qwen/Qwen3-0.6B", runtime=toolkit.runtime(provider="vllm-runtime"))

    assert isinstance(system._engine("vllm-runtime"), VLLMRuntimeProvider)


def test_vllm_environment_snapshot_is_non_secret(monkeypatch) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("VLLM_API_KEY", "secret-value")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen3-0.6B")

    snapshot = vllm_environment_snapshot()

    assert snapshot["base_url"] == "http://127.0.0.1:8000/v1"
    assert snapshot["base_url_configured"] is True
    assert snapshot["model"] == "Qwen/Qwen3-0.6B"
    assert snapshot["api_key_configured"] is True
    assert "secret-value" not in str(snapshot)
    assert vllm_signal_present() is True


def test_runtime_auto_resolves_vllm_when_base_url_is_configured(monkeypatch) -> None:
    import agentic_systems.core.runtime as runtime_module
    import agentic_systems.system as system_module

    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen3-0.6B")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-should-be-fallback")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setattr(runtime_module, "_module_available", lambda name: name in {"openai", "boto3"})
    monkeypatch.setattr(system_module, "_module_available", lambda name: name == "openai")

    runtime = toolkit.runtime(provider="auto", provider_priority=["vllm-runtime", "openai-runtime", "bedrock-runtime"])
    summary = runtime.describe()
    system = toolkit.AgenticSystem(model="Qwen/Qwen3-0.6B", runtime=runtime)

    assert runtime.model_id == "Qwen/Qwen3-0.6B"
    assert summary["selected_provider"] == VLLM_RUNTIME_ENGINE
    assert summary["mode"] == "auto"
    assert summary["preferred_provider"] == VLLM_RUNTIME_ENGINE
    assert summary["fallback_provider"] == "openai-runtime"
    assert summary["provider_priority"] == ["vllm-runtime", "openai-runtime", "bedrock-runtime"]
    assert summary["configuration"]["vllm"]["base_url"] == "http://127.0.0.1:8000/v1"
    assert isinstance(system._engine("auto"), VLLMRuntimeProvider)


def test_runtime_auto_unresolved_mentions_vllm(monkeypatch) -> None:
    import agentic_systems.core.runtime as runtime_module

    for key in (
        "VLLM_BASE_URL",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(runtime_module, "_module_available", lambda name: False)

    summary = toolkit.runtime(provider="auto").describe()

    assert summary["selected_provider"] == "auto"
    assert summary["mode"] == "auto-unresolved"
    assert "VLLM_BASE_URL" in summary["reason"]


class FakeAsyncChatCompletions:
    async def create(self, **kwargs):
        message = SimpleNamespace(content="Respuesta async vLLM.", tool_calls=[])
        usage = SimpleNamespace(prompt_tokens=3, completion_tokens=2, total_tokens=5)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


class FakeAsyncVLLMClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeAsyncChatCompletions())


def test_vllm_runtime_provider_async_missing_tools_and_success() -> None:
    import asyncio

    runtime = toolkit.runtime(provider="vllm-runtime", model="Qwen/Qwen3-0.6B")
    provider = VLLMRuntimeProvider(async_client=FakeAsyncVLLMClient())
    missing_agent = toolkit.Agent(name="empty", tools=[], runtime=runtime)

    missing = asyncio.run(provider.arun(missing_agent, "Hola", toolkit.RunPolicy(max_turns=1)))

    assert missing.ok is False
    assert missing.engine == VLLM_RUNTIME_ENGINE
    assert missing.meta["runtime_engine"] == VLLM_RUNTIME_ENGINE

    system = toolkit.AgenticSystem(runtime=runtime, model="Qwen/Qwen3-0.6B")
    agent = system.agent(name="qwen_async", instructions="Responde.", tools=[duplicar], engine="vllm-runtime", runtime=runtime)

    result = asyncio.run(provider.arun(agent, "Contesta sin tools.", toolkit.RunPolicy(max_turns=1), mode="eval"))

    assert result.ok is True
    assert result.engine == VLLM_RUNTIME_ENGINE
    assert result.text == "Respuesta async vLLM."
    assert result.usage["total_tokens"] == 5


def test_vllm_runtime_provider_environment_clients_and_defaults(monkeypatch) -> None:
    import agentic_systems.providers.vllm_runtime as vllm_module

    created = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            created["sync"] = kwargs

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            created["async"] = kwargs

    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    monkeypatch.delenv("VLLM_API_KEY", raising=False)
    monkeypatch.setattr(vllm_module, "_openai_module", lambda: SimpleNamespace(OpenAI=FakeOpenAI, AsyncOpenAI=FakeAsyncOpenAI))

    provider = VLLMRuntimeProvider()

    assert provider._client_from_environment().__class__ is FakeOpenAI
    assert provider._async_client_from_environment().__class__ is FakeAsyncOpenAI
    assert created["sync"] == {"base_url": "http://127.0.0.1:8000/v1", "api_key": "EMPTY"}
    assert created["async"] == {"base_url": "http://127.0.0.1:8000/v1", "api_key": "EMPTY"}

    monkeypatch.setenv("VLLM_API_KEY", "configured")
    assert vllm_module._vllm_api_key() == "configured"


def test_system_unknown_engine_and_auto_vllm_priority(monkeypatch) -> None:
    import pytest
    import agentic_systems.core.runtime as runtime_module

    system = toolkit.AgenticSystem(model="python-runtime", runtime=toolkit.runtime(provider="python-runtime"))
    with pytest.raises(ValueError, match="Unknown runtime/provider"):
        system._engine("unknown-runtime")

    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.setattr(runtime_module, "_module_available", lambda name: name == "openai")

    runtime = toolkit.runtime(provider="auto", provider_priority=["vllm-runtime"])
    system = toolkit.AgenticSystem(model="python-runtime", runtime=runtime)
    assert isinstance(system._engine("auto"), VLLMRuntimeProvider)



def test_openai_tool_def_builder_skips_missing_tool_specs() -> None:
    from agentic_systems.providers.openai_runtime import _openai_tools

    runtime = SimpleNamespace(tool_names=lambda: ["missing"], tool_specs=lambda names: {})
    agent = SimpleNamespace(system=None, tools=[])

    assert _openai_tools(runtime, agent) == []


def test_openai_tool_def_builder_uses_default_schema_for_schema_less_tools() -> None:
    from agentic_systems.providers.openai_runtime import _openai_tools

    tool = SimpleNamespace(name="plain", description="Plain tool", input_schema=None)
    agent = SimpleNamespace(tools=[], available_tools=lambda: [tool])

    defs = _openai_tools(None, agent)

    assert defs[0]["function"]["name"] == "plain"
    assert defs[0]["function"]["parameters"] == {"type": "object", "properties": {}, "additionalProperties": True}


def test_system_module_available_real_lookup() -> None:
    import agentic_systems.system as system_module

    assert system_module._module_available("sys") is True
    assert system_module._module_available("definitely_missing_agentic_systems_module") is False
