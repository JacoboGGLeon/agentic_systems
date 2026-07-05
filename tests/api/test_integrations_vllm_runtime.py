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
    monkeypatch.setenv("VLLM_MODEL_ID", "Qwen/Qwen3-0.6B")

    snapshot = vllm_environment_snapshot()

    assert snapshot["base_url"] == "http://127.0.0.1:8000/v1"
    assert snapshot["base_url_configured"] is True
    assert snapshot["model"] == "Qwen/Qwen3-0.6B"
    assert snapshot["api_key_configured"] is True
    assert "secret-value" not in str(snapshot)
    assert vllm_signal_present() is True
