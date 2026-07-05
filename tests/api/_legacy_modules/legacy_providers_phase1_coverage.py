
from __future__ import annotations

import asyncio
import dataclasses
import sys
import types
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from agentic_systems.contracts import AgentContract, RunPolicy
from agentic_systems.providers import OpenAIRuntimeProvider, PythonDirectEngine, PythonDirectProvider
import agentic_systems.providers as providers
from agentic_systems.providers.base import RuntimeToolSpec, ToolRegistryRuntime
import agentic_systems.providers.openai_runtime as openai_runtime_module
from agentic_systems.providers.openai_runtime import (
    _canonical_runtime_engine,
    _execute_tool,
    _input_to_prompt,
    _json_loads,
    _openai_module,
    _openai_tools,
    _tool_choice,
    _tool_result_text,
)
from agentic_systems.providers.python_direct import _json_like, _parse_plan, _parse_pipeline, _summary_from_output_payload
from agentic_systems.tools import Tool


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


def build_agent(runtime, *, tools=("add",), framework="openai-agents", info_payload=None):
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
    usage = SimpleNamespace(input_tokens=3, output_tokens=4, total_tokens=7, completion_tokens=4, prompt_tokens=3)
    client = FakeClient([
        FakeResponse(FakeMessage(content="calling", tool_calls=[FakeToolCall("add", '{"a": 20, "b": 22}')])),
        FakeResponse(FakeMessage(content="final answer"), usage=usage),
    ])
    provider = OpenAIRuntimeProvider(SimpleNamespace(_runtime=runtime), client=client)

    result = provider.run(agent, {"question": "sum"}, RunPolicy(tool_choice="required"), mode="audit")

    assert result.ok is True
    assert result.text == "final answer"
    assert result.engine == "bedrock-runtime"
    assert result.meta["framework"] == "openai-agents"
    assert result.meta["execution_engine"] == "openai-runtime"
    assert result.usage["total_tokens"] == 7
    assert result.tool_events[0].output["result"] == 42
    assert client.calls[0]["tool_choice"] == "required"

    failing_client = FakeClient([
        FakeResponse(FakeMessage(tool_calls=[FakeToolCall("fail", "{}")])),
    ])
    failing = OpenAIRuntimeProvider(SimpleNamespace(_runtime=runtime), client=failing_client).run(
        build_agent(runtime, tools=("fail",)), "fail", RunPolicy(repair=False), mode="eval"
    )
    assert failing.ok is False
    assert failing.tool_events[0].ok is False
    assert failing.tool_events[0].input == {}
    assert "boom" in failing.text

    loop_client = FakeClient([
        FakeResponse(FakeMessage(tool_calls=[FakeToolCall("add", '{"a": 1, "b": 1}', "c1")])),
        FakeResponse(FakeMessage(tool_calls=[FakeToolCall("add", '{"a": 2, "b": 2}', "c2")])),
    ])
    exceeded = OpenAIRuntimeProvider(SimpleNamespace(_runtime=runtime), client=loop_client).run(
        agent, "loop", RunPolicy(max_turns=1), mode="debug"
    )
    assert exceeded.ok is False
    assert exceeded.data["error"]["code"] == "max_turns_exceeded"

    async_client = FakeClient([
        FakeResponse(FakeMessage(tool_calls=[FakeToolCall("add", '{"a": 2, "b": 3}')])),
        FakeResponse(FakeMessage(content="async final")),
    ])
    async_result = asyncio.run(
        OpenAIRuntimeProvider(SimpleNamespace(_runtime=runtime), async_client=FakeAsyncClient(async_client)).arun(
            agent, "async", RunPolicy(), mode="audit"
        )
    )
    assert async_result.text == "async final"


def test_openai_provider_helpers_and_import_paths(monkeypatch):
    runtime = build_runtime()
    empty_runtime = ToolRegistryRuntime(model_id="empty")
    agent = build_agent(empty_runtime, tools=())
    provider = OpenAIRuntimeProvider(SimpleNamespace(_runtime=empty_runtime))
    missing = provider.run(agent, "x", RunPolicy(), mode="eval")
    assert missing.data["error"]["code"] == "missing_tools"

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
    assert no_runtime["event"].output["error"]["message"] == "missing runtime for missing"

    class SchemaModel(BaseModel):
        x: int

    class AvailableTool:
        name = "available"
        description = "Available tool"
        input_schema = SchemaModel

    available_agent = SimpleNamespace(tools=(), available_tools=lambda: [AvailableTool()])
    defs = _openai_tools(None, available_agent)
    assert defs[0]["function"]["name"] == "available"

    class MappingTool:
        name = "mapping"
        description = ""
        __doc__ = "Mapping doc"
        input_schema = {"type": "object", "properties": {}}

    mapping_agent = SimpleNamespace(tools=(), available_tools=lambda: [MappingTool()])
    assert _openai_tools(None, mapping_agent)[0]["function"]["description"] == "Mapping doc"

    module = types.SimpleNamespace(OpenAI=lambda: "client", AsyncOpenAI=lambda: "async-client")
    monkeypatch.setitem(sys.modules, "openai", module)
    assert _openai_module() is module


def test_python_direct_provider_plan_pipeline_errors_and_async():
    def add(a: int, b: int) -> dict:
        return {"result": a + b, "summary": f"sum={a + b}"}

    def double(result: int, summary: str = "", ok: bool = True, tool: str = "") -> dict:
        return {"result": result * 2, "message": f"double={result * 2}"}

    add_tool = Tool(add, name="add")
    double_tool = Tool(double, name="double")
    agent = SimpleNamespace(name="py", model="m", tools=("add", "double"), available_tools=lambda: [add_tool, double_tool])
    provider = PythonDirectProvider()

    plan_result = provider.run(agent, {"steps": [{"tool": "add", "input": {"a": 2, "b": 3}}, {"name": "double", "args": {"result": 5}}]}, RunPolicy(), mode="eval")
    assert plan_result.ok is True
    assert plan_result.data["last"]["result"] == 10
    assert "double=10" in plan_result.text

    pipeline_result = provider.run(agent, {"pipeline": {"order": ["add", "double"], "state": {"a": 4, "b": 6}}}, RunPolicy(), mode="audit")
    assert pipeline_result.meta["execution_style"] == "state_pipeline"
    assert pipeline_result.data["last"]["result"] == 20

    direct_pipeline = provider.run(agent, {"tools": ["add"], "state": {"a": 1, "b": 2}}, RunPolicy(), mode="audit")
    assert direct_pipeline.data["result"] == 3

    too_many = provider.run(agent, {"steps": [{"tool": "add", "input": {"a": 1, "b": 1}}, {"tool": "double", "input": {"result": 2}}]}, RunPolicy(max_tool_calls=1), mode="eval")
    assert too_many.data["error"]["code"] == "max_tool_calls_exceeded"

    bad_pipeline = provider.run(agent, {"pipeline": "add"}, RunPolicy(), mode="eval")
    assert bad_pipeline.data["error"]["code"] == "TypeError"

    unknown_pipeline = provider.run(agent, {"pipeline": ["missing"]}, RunPolicy(), mode="eval")
    assert unknown_pipeline.data["error"]["code"] == "KeyError"

    assert provider.run(SimpleNamespace(name="empty", tools=()), {}, RunPolicy()).data["error"]["code"] == "missing_tools"
    assert provider.run(agent, "not json", RunPolicy()).data["error"]["code"] == "ValueError"
    assert provider.run(agent, "", RunPolicy()).data["error"]["code"] == "ValueError"
    assert provider.run(agent, [{"tool_name": "add", "payload": {"a": 3, "b": 4}}], RunPolicy()).data["result"] == 7
    assert provider.run(agent, 123, RunPolicy()).data["error"]["code"] == "ValueError"
    assert provider.run(agent, {"tool": "missing", "input": {}}, RunPolicy()).data["error"]["code"] == "KeyError"
    assert provider.run(agent, {"tool": "add", "input": {"a": "bad", "b": 2}}, RunPolicy(repair=False)).ok is False

    single_agent = SimpleNamespace(name="single", model=None, tools=("add",), available_tools=lambda: [add_tool])
    assert provider.run(single_agent, "raw text", RunPolicy()).data["ok"] is False
    assert provider.run(single_agent, {"a": 8, "b": 9}, RunPolicy()).data["result"] == 17
    assert asyncio.run(provider.arun(single_agent, {"tool": "add", "input": {"a": 1, "b": 2}}, RunPolicy())).data["result"] == 3
    assert isinstance(PythonDirectEngine(), PythonDirectProvider)

    tools = {"add": add_tool}
    assert _parse_pipeline("x", tools) is None
    with pytest.raises(TypeError):
        _parse_plan(["bad"], tools)


def test_tool_registry_runtime_payloads_validation_and_lazy_provider(monkeypatch, capsys):
    runtime = ToolRegistryRuntime(model_id="m", region_name="r", max_tokens_default="9", temperature_default="0.25")
    assert runtime.max_tokens_default == 9
    assert runtime.temperature_default == 0.25

    @runtime.tool(description="Untyped param")
    def loose(x):
        return x

    async def async_tool(x: int) -> dict:
        return {"x": x}

    runtime.tool(async_tool, name="async_tool", description="Async tool")

    report = runtime.validate_tool_registry()
    assert report["ok"] is False
    assert any(issue["issue"] == "parameter_missing_type_annotation" for issue in report["issues"])
    assert runtime.export_tool_specs(["loose"])[0]["name"] == "loose"
    runtime.print_tool_specs()
    assert "loose" in capsys.readouterr().out
    with pytest.raises(KeyError):
        runtime.export_tool_specs(["missing"])

    assert runtime.execute_tool("missing", {}).ok is False
    assert runtime.execute_tool("async_tool", {"x": 1}).ok is False
    assert runtime.execute_tool("loose", {"x": object()}).ok is True

    class PayloadModel(BaseModel):
        value: int

    @dataclasses.dataclass
    class PayloadData:
        value: int

    payloads = [
        PayloadModel(value=1),
        PayloadData(value=2),
        {"a": 1},
        [1, 2],
        "text",
        True,
        3,
        None,
        object(),
    ]
    kinds = [ToolRegistryRuntime.to_envelope(value, tool_name="payload").kind for value in payloads]
    assert kinds == ["pydantic", "dataclass", "object", "list", "text", "boolean", "number", "null", "repr"]

    def bad_varargs(*args):
        return {}

    with pytest.raises(TypeError, match="cannot use"):
        runtime.tool(bad_varargs, name="bad_varargs")

    fake_module = types.ModuleType("agentic_systems.providers.bedrock_runtime")
    fake_module.BedrockRuntime = object
    monkeypatch.setitem(sys.modules, "agentic_systems.providers.bedrock_runtime", fake_module)
    assert providers.BedrockRuntime is object
    with pytest.raises(AttributeError):
        providers.__getattr__("Nope")



def test_openai_remaining_provider_branches(monkeypatch):
    runtime = build_runtime()
    agent = build_agent(runtime, info_payload=RuntimeError("bad info"))
    assert OpenAIRuntimeProvider(SimpleNamespace(_runtime=runtime))._runtime_engine(agent) == "openai-runtime"

    missing_defs_agent = build_agent(runtime, tools=("missing",))
    assert _openai_tools(runtime, missing_defs_agent) == []

    async_success_client = FakeClient([FakeResponse(FakeMessage(content="module async"))])
    fake_openai = types.SimpleNamespace(AsyncOpenAI=lambda: FakeAsyncClient(async_success_client))
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    result = asyncio.run(OpenAIRuntimeProvider(SimpleNamespace(_runtime=runtime)).arun(agent, "x", RunPolicy(), mode="debug"))
    assert result.text == "module async"

    empty_runtime = ToolRegistryRuntime(model_id="empty")
    fake_openai_missing = types.SimpleNamespace(AsyncOpenAI=lambda: FakeAsyncClient(FakeClient([])))
    monkeypatch.setitem(sys.modules, "openai", fake_openai_missing)
    missing = asyncio.run(OpenAIRuntimeProvider(SimpleNamespace(_runtime=empty_runtime)).arun(build_agent(empty_runtime, tools=()), "x", RunPolicy()))
    assert missing.data["error"]["code"] == "missing_tools"

    async_loop_client = FakeClient([
        FakeResponse(FakeMessage(tool_calls=[FakeToolCall("add", '{"a": 1, "b": 2}', "a1")])),
        FakeResponse(FakeMessage(tool_calls=[FakeToolCall("add", '{"a": 2, "b": 3}', "a2")])),
    ])
    exceeded = asyncio.run(
        OpenAIRuntimeProvider(SimpleNamespace(_runtime=runtime), async_client=FakeAsyncClient(async_loop_client)).arun(
            agent, "loop", RunPolicy(max_turns=1)
        )
    )
    assert exceeded.data["error"]["code"] == "max_turns_exceeded"

    async_fail_client = FakeClient([FakeResponse(FakeMessage(tool_calls=[FakeToolCall("fail", "{}")]))])
    failed = asyncio.run(
        OpenAIRuntimeProvider(SimpleNamespace(_runtime=runtime), async_client=FakeAsyncClient(async_fail_client)).arun(
            build_agent(runtime, tools=("fail",)), "fail", RunPolicy(repair=False)
        )
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

    monkeypatch.setattr(openai_runtime_module, "canonical_engine_name", lambda value: (_ for _ in ()).throw(ValueError("bad")))
    assert _canonical_runtime_engine("bad-engine") is None


def test_python_direct_remaining_branches():
    class PayloadModel(BaseModel):
        a: int
        b: int

    def add(a: int, b: int) -> dict:
        return {"result": a + b}

    def fail(result: int = 0, ok: bool = True, tool: str = "") -> dict:
        raise RuntimeError("pipeline boom")

    add_tool = Tool(add, name="add")
    fail_tool = Tool(fail, name="fail")
    agent = SimpleNamespace(name="py", model=None, tools=("add", "fail"), available_tools=lambda: [add_tool, fail_tool])
    provider = PythonDirectProvider()

    too_many_pipeline = provider.run(agent, {"pipeline": ["add", "fail"], "state": {"a": 1, "b": 2}}, RunPolicy(max_tool_calls=1))
    assert too_many_pipeline.data["error"]["code"] == "max_tool_calls_exceeded"

    broken_pipeline = provider.run(agent, {"pipeline": ["add", "fail"], "state": {"a": 1, "b": 2}}, RunPolicy(repair=False))
    assert broken_pipeline.ok is False
    assert broken_pipeline.meta["planned_tool_calls"] == 2

    single_agent = SimpleNamespace(name="single", tools=("add",), available_tools=lambda: [add_tool])
    scalar = provider.run(single_agent, 99, RunPolicy())
    assert scalar.ok is False
    assert scalar.data["tool"] == "add"

    missing_tool_name = provider.run(agent, {"steps": [{"input": {}}]}, RunPolicy())
    assert missing_tool_name.data["error"]["code"] == "ValueError"

    model_input = provider.run(single_agent, PayloadModel(a=2, b=5), RunPolicy())
    assert model_input.data["error"]["code"] == "TypeError"
    assert _json_like(PayloadModel(a=2, b=5)) == {"a": 2, "b": 5}
    assert _summary_from_output_payload(["not", "mapping"]) == ""


def test_base_provider_remaining_validation_branches():
    runtime = ToolRegistryRuntime(model_id="m")

    @runtime.tool(name="ok", description="ok")
    def ok(x: int) -> dict:
        return {"x": x}

    spec = runtime._tools["ok"]
    runtime._tools[""] = RuntimeToolSpec(
        name="",
        description="",
        func=spec.func,
        signature=spec.signature,
        input_model=spec.input_model,
        input_schema={"type": "array"},
        is_async=False,
    )
    runtime._tools["bad_schema"] = RuntimeToolSpec(
        name="bad_schema",
        description="bad",
        func=spec.func,
        signature=spec.signature,
        input_model=spec.input_model,
        input_schema={"type": "object", "additionalProperties": True},
        is_async=False,
    )
    report = runtime.validate_tool_registry(["", "bad_schema"])
    issues = {issue["issue"] for issue in report["issues"]}
    assert "tool_name_must_be_non_empty_string" in issues
    assert "input_schema_type_must_be_object" in issues
    assert "input_schema_missing_properties" in issues
    assert "additionalProperties_should_be_false" in issues

    class Dumpable(BaseModel):
        value: int

    @dataclasses.dataclass
    class NestedData:
        value: int

    envelope = runtime.to_envelope({"model": Dumpable(value=1), "data": NestedData(value=2)}, tool_name="nested")
    assert envelope.data == {"model": {"value": 1}, "data": {"value": 2}}
