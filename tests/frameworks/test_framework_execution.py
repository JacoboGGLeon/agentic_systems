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


def test_public_surface_adds_only_framework_factory():
    assert toolkit.__version__ == "2.0.0a1"
    assert len(toolkit.__all__) == 112
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
