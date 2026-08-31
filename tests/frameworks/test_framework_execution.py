from __future__ import annotations

import asyncio
import json

import pytest
from pydantic import ValidationError

import agentic_systems as toolkit
from agentic_systems.integrations import FrameworkConfig


def echo(value: str) -> dict:
    return {"value": value}


def _agent(framework: str | FrameworkConfig | None):
    echo_tool = toolkit.tool(echo, name=f"echo_{framework or 'default'}")
    return toolkit.agent(
        name=f"worker_{framework or 'default'}",
        tools=[echo_tool],
        engine="python-runtime",
        framework=framework,
    )


def test_framework_factory_validates_reserved_keys_and_redacts_values():
    config = toolkit.framework(
        "strands",
        agent_kwargs={"hooks": [object()]},
        run_kwargs={"structured_output_model": dict},
    )

    assert isinstance(config, FrameworkConfig)
    assert config.inspect() == {
        "name": "strands",
        "agent_kwargs": {"hooks": "list"},
        "run_kwargs": {"structured_output_model": "type"},
    }
    assert "object" not in json.dumps(config.inspect())

    with pytest.raises(ValidationError, match="Agentic Systems-owned keys: model"):
        toolkit.framework("strands", agent_kwargs={"model": "forbidden"})
    with pytest.raises(ValidationError, match="Agentic Systems-owned keys: prompt"):
        toolkit.framework("strands", run_kwargs={"prompt": "forbidden"})


def test_default_framework_preserves_observable_identity():
    agent = _agent(None)

    assert agent.framework is None
    assert agent.framework_config.name == "native"


@pytest.mark.parametrize(
    ("framework", "adapter", "native_type"),
    [
        (None, "native", "PythonRuntimeEngine"),
        ("langgraph", "langgraph", "CompiledStateGraph"),
        ("openai-agents", "openai-agents", "Agent"),
        ("strands", "strands", "Agent"),
    ],
)
def test_python_provider_executes_the_real_framework_offline(
    framework: str | None,
    adapter: str,
    native_type: str,
):
    agent = _agent(framework)

    assert agent.prepare() is agent
    assert type(agent.native_agent).__name__ == native_type

    result = agent.run({"value": "ok"})

    assert result.ok is True
    assert result.data["value"] == "ok"
    assert result.engine == "python-runtime"
    assert result.meta["framework_adapter"] == adapter
    assert result.native_result is not None
    assert len(result.tool_events) == 1
    assert "native_result" not in result.model_dump(mode="json")
    json.dumps(result.model_dump(mode="json"))


@pytest.mark.parametrize("framework", [None, "langgraph", "openai-agents", "strands"])
def test_python_provider_frameworks_support_async_execution(framework: str | None):
    agent = _agent(framework)

    result = asyncio.run(agent.arun({"value": "async"}))

    assert result.ok is True
    assert result.data["value"] == "async"
    assert result.native_result is not None


def test_public_surface_is_frozen_for_2_1():
    assert toolkit.__version__ == "2.1.1"
    assert len(toolkit.__all__) == 89
    assert toolkit.__all__.count("framework") == 1


@pytest.mark.parametrize("framework", [None, "langgraph", "openai-agents", "strands"])
def test_native_skill_tools_cross_every_framework(framework: str | None):
    tool = toolkit.tool(echo, name=f"skill_echo_{framework or 'native'}")
    capability = toolkit.skill(name=f"skill_{framework or 'native'}", tools=[tool])
    agent = toolkit.agent(
        name=f"skill_agent_{framework or 'native'}",
        skills=[capability],
        runtime=toolkit.runtime(provider="python-runtime"),
        framework=framework,
    )

    result = agent.run({"value": "skill"})

    assert result.ok is True
    assert result.data["value"] == "skill"
    assert result.meta["framework_adapter"] == (framework or "native")


def test_openai_agents_native_capabilities_execute_offline(monkeypatch):
    from agents import (
        GuardrailFunctionOutput,
        SQLiteSession,
        function_tool,
        handoff,
        input_guardrail,
    )
    from pydantic import BaseModel

    monkeypatch.setenv("OPENAI_AGENTS_DISABLE_TRACING", "1")

    class Evidence(BaseModel):
        value: str

    @function_tool
    def native_echo(value: str) -> dict:
        return {"value": value}

    @input_guardrail(run_in_parallel=False)
    def reject_blocked(context, native_agent, input_value):
        return GuardrailFunctionOutput(
            output_info={"checked": True},
            tripwire_triggered="blocked" in str(input_value),
        )

    runtime = toolkit.runtime(provider="python-runtime")
    session = SQLiteSession("pytest", ":memory:")
    agent = toolkit.agent(
        name="openai_capabilities",
        tools=[toolkit.tool(echo, name="agentic_echo")],
        runtime=runtime,
        framework=toolkit.framework(
            "openai-agents",
            agent_kwargs={
                "tools": [native_echo],
                "input_guardrails": [reject_blocked],
                "output_type": Evidence,
            },
            run_kwargs={"session": session},
        ),
    )

    result = agent.run({"tool": "native_echo", "input": {"value": "typed"}})
    blocked = agent.run("blocked")
    session.close()

    assert result.ok is True
    assert result.data == {"value": "typed"}
    assert blocked.ok is False
    assert blocked.data["error"]["code"] == "InputGuardrailTripwireTriggered"

    specialist = toolkit.agent(
        name="specialist",
        tools=[toolkit.tool(echo, name="specialist_echo")],
        runtime=runtime,
        framework="openai-agents",
    )
    specialist.prepare()
    native_handoff = handoff(specialist.native_agent)
    triage = toolkit.agent(
        name="triage",
        runtime=runtime,
        framework=toolkit.framework(
            "openai-agents",
            agent_kwargs={"handoffs": [native_handoff]},
        ),
    )
    transferred = triage.run({"tool": native_handoff.tool_name, "input": {}})

    assert transferred.ok is True
    assert transferred.data == {"assistant": "specialist"}


def test_strands_native_capabilities_execute_offline():
    from pydantic import BaseModel
    from strands import tool as strands_tool
    from strands.hooks import AfterInvocationEvent

    class Evidence(BaseModel):
        value: str

    hook_events = []

    def record(event):
        hook_events.append(type(event).__name__)

    record.__annotations__["event"] = AfterInvocationEvent

    @strands_tool
    def native_echo(value: str) -> dict:
        return {"value": value}

    agent = toolkit.agent(
        name="strands_capabilities",
        tools=[toolkit.tool(echo, name="agentic_echo")],
        runtime=toolkit.runtime(provider="python-runtime"),
        framework=toolkit.framework(
            "strands",
            agent_kwargs={"tools": [native_echo], "hooks": [record]},
            run_kwargs={"structured_output_model": Evidence},
        ),
    )

    result = asyncio.run(
        agent.arun({"tool": "native_echo", "input": {"value": "typed"}})
    )

    assert result.ok is True
    assert result.data == {"value": "typed"}
    assert hook_events == ["AfterInvocationEvent"]
    assert type(result.native_result).__name__ == "AgentResult"


def test_framework_tracing_is_owned_by_native_sdks():
    import inspect

    assert (
        "disable_framework_tracing" not in inspect.signature(toolkit.system).parameters
    )
    assert (
        "disable_framework_tracing"
        not in inspect.signature(toolkit.AgenticSystem).parameters
    )
    with pytest.raises(TypeError, match="disable_framework_tracing"):
        toolkit.system(disable_framework_tracing=True)


def test_strands_plain_callback_is_lifted_to_hook_provider():
    from agentic_systems.integrations.adapters.strands import _strands_hook

    class Event:
        pass

    observed = []

    def callback(event: Event):
        observed.append(event)

    callback.__annotations__["event"] = Event

    class Registry:
        def __init__(self):
            self.registered = []

        def add_callback(self, event_type, handler):
            self.registered.append((event_type, handler))

    provider = _strands_hook(callback)
    registry = Registry()
    provider.register_hooks(registry)

    assert registry.registered == [(Event, callback)]


def test_strands_plain_callback_requires_one_typed_event():
    from agentic_systems.integrations.adapters.strands import _strands_hook

    with pytest.raises(TypeError, match="type its event parameter"):
        _strands_hook(lambda event: None)

    with pytest.raises(TypeError, match="exactly one event parameter"):
        _strands_hook(lambda first, second: None)


def test_strands_materializes_explicit_vllm_endpoint_and_secret(monkeypatch):
    from types import SimpleNamespace

    import strands.models.openai as strands_openai

    from agentic_systems.integrations.adapters.strands import _materialize_model

    observed = {}

    class FakeOpenAIModel:
        def __init__(self, *, model_id, client_args):
            observed.update(model_id=model_id, client_args=client_args)

        def format_request(self, *args, **kwargs):
            return {"model": "served-qwen", "tools": [], "tool_choice": "auto"}

    monkeypatch.setattr(strands_openai, "OpenAIModel", FakeOpenAIModel)
    runtime = toolkit.runtime(
        provider="vllm-runtime",
        model="served-qwen",
        endpoint="http://127.0.0.1:8123/v1",
        api_key="private-vllm-key",
    )
    agent = SimpleNamespace(
        engine="vllm-runtime",
        model="served-qwen",
        runtime_config=runtime,
    )

    model = _materialize_model(agent, None)

    assert observed == {
        "model_id": "served-qwen",
        "client_args": {
            "base_url": "http://127.0.0.1:8123/v1",
            "api_key": "private-vllm-key",
        },
    }
    request = model.format_request()
    assert request == {"model": "served-qwen"}


def test_strands_preserves_hook_provider_and_rejects_non_callable():
    from agentic_systems.integrations.adapters.strands import _strands_hook

    class Provider:
        def register_hooks(self, registry):
            return None

    provider = Provider()
    assert _strands_hook(provider) is provider
    with pytest.raises(TypeError, match="HookProvider objects or callables"):
        _strands_hook(object())


def test_strands_hook_falls_back_when_type_hints_cannot_resolve():
    from agentic_systems.integrations.adapters.strands import _strands_hook

    def callback(event):
        return event

    callback.__annotations__["event"] = "MissingEvent"
    with pytest.raises(TypeError, match="type its event parameter"):
        _strands_hook(callback)


def test_strands_materializes_explicit_openai_endpoint(monkeypatch):
    from types import SimpleNamespace

    import strands.models.openai as strands_openai

    from agentic_systems.integrations.adapters.strands import _materialize_model

    observed = {}

    class FakeOpenAIModel:
        def __init__(self, *, model_id, client_args):
            observed.update(model_id=model_id, client_args=client_args)

    monkeypatch.setattr(strands_openai, "OpenAIModel", FakeOpenAIModel)
    runtime = toolkit.runtime(
        provider="openai-runtime",
        model="served-openai",
        endpoint="http://127.0.0.1:9000/v1",
        api_key="private-openai-key",
    )
    agent = SimpleNamespace(
        engine="openai-runtime",
        model="served-openai",
        runtime_config=runtime,
    )

    _materialize_model(agent, None)

    assert observed["client_args"] == {
        "base_url": "http://127.0.0.1:9000/v1",
        "api_key": "private-openai-key",
    }
