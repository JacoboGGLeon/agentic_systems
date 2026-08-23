from __future__ import annotations

import asyncio
import sys
import types
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from agentic_systems.contracts import AgentContract, RunPolicy
from agentic_systems.providers import OpenAIRuntimeProvider
from agentic_systems.providers.base import ToolRegistryRuntime
import agentic_systems.providers.openai_runtime as openai_runtime_module
from agentic_systems.providers.openai_runtime import (
    _canonical_tool_name,
    _canonical_runtime_engine,
    _execute_tool,
    _input_to_prompt,
    _json_loads,
    _openai_module,
    _openai_tools,
    _provider_tool_name,
    _tool_choice,
    _tool_result_text,
)


class FakeResponse:
    def __init__(self, message, *, usage=None):
        self.choices = [SimpleNamespace(message=message)]
        self.usage = usage


class FakeMessage:
    def __init__(self, *, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeToolCall:
    def __init__(self, name, arguments, call_id="call_1"):
        self.id = call_id
        self.function = SimpleNamespace(name=name, arguments=arguments)


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            return FakeResponse(FakeMessage(content="fallback final"))
        return self.responses.pop(0)


class FakeAsyncCompletions:
    def __init__(self, sync_client):
        self.sync_client = sync_client

    async def create(self, **kwargs):
        return self.sync_client.create(**kwargs)


class FakeAsyncClient:
    def __init__(self, sync_client):
        self.chat = SimpleNamespace(completions=FakeAsyncCompletions(sync_client))


def build_runtime():
    runtime = ToolRegistryRuntime(model_id="runtime-model", region_name="us-west-2")

    @runtime.tool(name="add", description="Add two numbers")
    def add(a: int, b: int) -> dict:
        return {"result": a + b, "summary": f"{a}+{b}={a + b}"}

    @runtime.tool(name="fail", description="Always fail")
    def fail() -> dict:
        raise RuntimeError("boom")

    return runtime


def build_agent(
    runtime, *, tools=("add",), framework="openai-agents", info_payload=None
):
    def info():
        if isinstance(info_payload, BaseException):
            raise info_payload
        return info_payload or {}

    return SimpleNamespace(
        name="agent",
        instructions="Use tools.",
        tools=tools,
        model=None,
        contract=AgentContract(),
        framework=framework,
        system=SimpleNamespace(_runtime=runtime, model="system-model"),
        info=info,
    )


def test_openai_provider_tool_success_failure_async_and_max_turns():
    runtime = build_runtime()
    agent = build_agent(runtime, info_payload={"runtime_engine": "bedrock-runtime"})
    usage = SimpleNamespace(
        input_tokens=3,
        output_tokens=4,
        total_tokens=7,
        completion_tokens=4,
        prompt_tokens=3,
    )
    client = FakeClient(
        [
            FakeResponse(
                FakeMessage(
                    content="calling",
                    tool_calls=[FakeToolCall("add", '{"a": 20, "b": 22}')],
                )
            ),
            FakeResponse(FakeMessage(content="final answer"), usage=usage),
        ]
    )
    provider = OpenAIRuntimeProvider(SimpleNamespace(_runtime=runtime), client=client)

    result = provider.run(
        agent, {"question": "sum"}, RunPolicy(tool_choice="required"), mode="audit"
    )

    assert result.ok is True
    assert result.text == "final answer"
    assert result.engine == "bedrock-runtime"
    assert result.meta["framework"] == "openai-agents"
    assert result.meta["execution_engine"] == "openai-runtime"
    assert result.usage["total_tokens"] == 7
    assert result.tool_events[0].output["result"] == 42
    assert client.calls[0]["tool_choice"] == "required"

    failing_client = FakeClient(
        [
            FakeResponse(FakeMessage(tool_calls=[FakeToolCall("fail", "{}")])),
        ]
    )
    failing = OpenAIRuntimeProvider(
        SimpleNamespace(_runtime=runtime), client=failing_client
    ).run(
        build_agent(runtime, tools=("fail",)),
        "fail",
        RunPolicy(repair=False),
        mode="eval",
    )
    assert failing.ok is False
    assert failing.tool_events[0].ok is False
    assert failing.tool_events[0].input == {}
    assert "boom" in failing.text

    loop_client = FakeClient(
        [
            FakeResponse(
                FakeMessage(tool_calls=[FakeToolCall("add", '{"a": 1, "b": 1}', "c1")])
            ),
            FakeResponse(
                FakeMessage(tool_calls=[FakeToolCall("add", '{"a": 2, "b": 2}', "c2")])
            ),
        ]
    )
    exceeded = OpenAIRuntimeProvider(
        SimpleNamespace(_runtime=runtime), client=loop_client
    ).run(agent, "loop", RunPolicy(max_turns=1), mode="debug")
    assert exceeded.ok is False
    assert exceeded.data["error"]["code"] == "max_turns_exceeded"

    async_client = FakeClient(
        [
            FakeResponse(
                FakeMessage(tool_calls=[FakeToolCall("add", '{"a": 2, "b": 3}')])
            ),
            FakeResponse(FakeMessage(content="async final")),
        ]
    )
    async_result = asyncio.run(
        OpenAIRuntimeProvider(
            SimpleNamespace(_runtime=runtime),
            async_client=FakeAsyncClient(async_client),
        ).arun(agent, "async", RunPolicy(), mode="audit")
    )
    assert async_result.text == "async final"


def test_openai_provider_aliases_namespaced_tools_without_public_identity_loss():
    runtime = ToolRegistryRuntime(model_id="runtime-model")

    @runtime.tool(name="quality.echo", description="Echo a value")
    def quality_echo(value: str) -> dict[str, str]:
        return {"value": value}

    alias = _provider_tool_name("quality.echo")
    client = FakeClient(
        [
            FakeResponse(
                FakeMessage(tool_calls=[FakeToolCall(alias, '{"value": "ok"}')])
            ),
            FakeResponse(FakeMessage(content="done")),
        ]
    )
    agent = build_agent(runtime, tools=("quality.echo",))
    result = OpenAIRuntimeProvider(
        SimpleNamespace(_runtime=runtime), client=client
    ).run(agent, "echo", RunPolicy(tool_choice="quality.echo"))

    assert alias.startswith("as_quality_echo_")
    assert len(alias) <= 64
    assert client.calls[0]["tools"][0]["function"]["name"] == alias
    assert client.calls[0]["tool_choice"]["function"]["name"] == alias
    assert result.tool_events[0].name == "quality.echo"
    assert result.ok is True
    assert _provider_tool_name("already_valid") == "already_valid"
    assert _provider_tool_name(".").startswith("as_tool_")
    assert _provider_tool_name("x" * 65).startswith("as_")
    assert _canonical_tool_name(None, SimpleNamespace(), "unknown") == "unknown"


def test_openai_provider_rejects_ambiguous_provider_aliases(monkeypatch):
    runtime = build_runtime()
    agent = build_agent(runtime, tools=("add", "fail"))
    monkeypatch.setattr(
        openai_runtime_module, "_provider_tool_name", lambda name: "same"
    )

    with pytest.raises(ValueError, match="not unique"):
        _openai_tools(runtime, agent)
    with pytest.raises(ValueError, match="Ambiguous"):
        _canonical_tool_name(runtime, agent, "same")


def test_openai_provider_helpers_and_import_paths(monkeypatch):
    runtime = build_runtime()
    empty_runtime = ToolRegistryRuntime(model_id="empty")
    agent = build_agent(empty_runtime, tools=())
    completion_client = FakeClient([FakeResponse(FakeMessage(content="complete"))])
    provider = OpenAIRuntimeProvider(
        SimpleNamespace(_runtime=empty_runtime), client=completion_client
    )
    completion = provider.run(agent, "x", RunPolicy(), mode="eval")
    assert completion.text == "complete"
    assert completion_client.calls[0]["tools"] is None
    assert completion_client.calls[0]["tool_choice"] is None

    assert _tool_choice(None) == "auto"
    assert _tool_choice("auto") == "auto"
    assert _tool_choice("any") == "required"
    assert _tool_choice("add") == {"type": "function", "function": {"name": "add"}}
    assert _tool_choice({"raw": True}) == "auto"
    assert _json_loads("[1, 2]") == {"value": [1, 2]}
    assert _json_loads("bad") == {"input": "bad"}
    assert _canonical_runtime_engine(None) is None
    assert _canonical_runtime_engine(" ") is None
    assert _canonical_runtime_engine("openai-runtime") is None
    assert _canonical_runtime_engine("bedrock-runtime") == "bedrock-runtime"
    assert _canonical_runtime_engine(object()) is None

    class DumpJsonNoIndent:
        def model_dump_json(self, *args, **kwargs):
            if kwargs:
                raise TypeError("no indent")
            return "compact"

    class NotJsonable:
        def __str__(self):
            return "not-jsonable"

    assert _input_to_prompt(None) == ""
    assert _input_to_prompt("text") == "text"
    assert _input_to_prompt(DumpJsonNoIndent()) == "compact"
    assert _input_to_prompt({"items": {2, 1}}).startswith("{")
    assert _input_to_prompt(NotJsonable()) == "not-jsonable"

    assert _tool_result_text({"data": {"message": "hello"}}) == "hello"
    assert _tool_result_text({"data": {"x": 1}}).startswith("{")
    assert _tool_result_text("plain") == "plain"

    wrapped = SimpleNamespace(_runtime=runtime)
    executed = _execute_tool(wrapped, agent, "add", {"a": 1, "b": 2})
    assert executed["event"].output["result"] == 3
    no_runtime = _execute_tool(None, agent, "missing", {})
    assert (
        no_runtime["event"].output["error"]["message"] == "missing runtime for missing"
    )

    class SchemaModel(BaseModel):
        x: int

    class AvailableTool:
        name = "available"
        description = "Available tool"
        input_schema = SchemaModel

    available_agent = SimpleNamespace(
        tools=(), available_tools=lambda: [AvailableTool()]
    )
    defs = _openai_tools(None, available_agent)
    assert defs[0]["function"]["name"] == "available"
    assert _canonical_tool_name(None, available_agent, "available") == "available"

    class MappingTool:
        name = "mapping"
        description = ""
        __doc__ = "Mapping doc"
        input_schema = {"type": "object", "properties": {}}

    mapping_agent = SimpleNamespace(tools=(), available_tools=lambda: [MappingTool()])
    assert (
        _openai_tools(None, mapping_agent)[0]["function"]["description"]
        == "Mapping doc"
    )

    module = types.SimpleNamespace(
        OpenAI=lambda: "client", AsyncOpenAI=lambda: "async-client"
    )
    monkeypatch.setitem(sys.modules, "openai", module)
    assert _openai_module() is module


def test_openai_provider_handles_client_import_and_response_errors(monkeypatch):
    runtime = build_runtime()
    agent = build_agent(runtime, info_payload=RuntimeError("bad info"))
    assert (
        OpenAIRuntimeProvider(SimpleNamespace(_runtime=runtime))._runtime_engine(agent)
        == "openai-runtime"
    )

    missing_defs_agent = build_agent(runtime, tools=("missing",))
    assert _openai_tools(runtime, missing_defs_agent) == []

    async_success_client = FakeClient(
        [FakeResponse(FakeMessage(content="module async"))]
    )
    fake_openai = types.SimpleNamespace(
        AsyncOpenAI=lambda: FakeAsyncClient(async_success_client)
    )
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    result = asyncio.run(
        OpenAIRuntimeProvider(SimpleNamespace(_runtime=runtime)).arun(
            agent, "x", RunPolicy(), mode="debug"
        )
    )
    assert result.text == "module async"

    empty_runtime = ToolRegistryRuntime(model_id="empty")
    fake_openai_missing = types.SimpleNamespace(
        AsyncOpenAI=lambda: FakeAsyncClient(FakeClient([]))
    )
    monkeypatch.setitem(sys.modules, "openai", fake_openai_missing)
    completion = asyncio.run(
        OpenAIRuntimeProvider(SimpleNamespace(_runtime=empty_runtime)).arun(
            build_agent(empty_runtime, tools=()), "x", RunPolicy()
        )
    )
    assert completion.ok is True
    assert completion.text == "fallback final"

    async_loop_client = FakeClient(
        [
            FakeResponse(
                FakeMessage(tool_calls=[FakeToolCall("add", '{"a": 1, "b": 2}', "a1")])
            ),
            FakeResponse(
                FakeMessage(tool_calls=[FakeToolCall("add", '{"a": 2, "b": 3}', "a2")])
            ),
        ]
    )
    exceeded = asyncio.run(
        OpenAIRuntimeProvider(
            SimpleNamespace(_runtime=runtime),
            async_client=FakeAsyncClient(async_loop_client),
        ).arun(agent, "loop", RunPolicy(max_turns=1))
    )
    assert exceeded.data["error"]["code"] == "max_turns_exceeded"

    async_fail_client = FakeClient(
        [FakeResponse(FakeMessage(tool_calls=[FakeToolCall("fail", "{}")]))]
    )
    failed = asyncio.run(
        OpenAIRuntimeProvider(
            SimpleNamespace(_runtime=runtime),
            async_client=FakeAsyncClient(async_fail_client),
        ).arun(build_agent(runtime, tools=("fail",)), "fail", RunPolicy(repair=False))
    )
    assert failed.ok is False
    assert "boom" in failed.text

    class DumpableEnvelope:
        def model_dump(self, mode="json"):
            return {"data": {"text": "dumped"}}

    assert _tool_result_text(DumpableEnvelope()) == "dumped"

    class DumpableValue:
        def model_dump(self, mode="json"):
            return {"x": 1}

    assert '"x": 1' in _input_to_prompt({"payload": DumpableValue()})

    monkeypatch.setattr(
        openai_runtime_module,
        "canonical_engine_name",
        lambda value: (_ for _ in ()).throw(ValueError("bad")),
    )
    assert _canonical_runtime_engine("bad-engine") is None
