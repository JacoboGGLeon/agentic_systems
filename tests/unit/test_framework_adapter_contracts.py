from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ValidationError

from agentic_systems import RunPolicy, RunResult
from agentic_systems.integrations.adapters import framework_adapter
from agentic_systems.integrations.adapters import bedrock_openai as bo
from agentic_systems.integrations.adapters import openai_agents as oa
from agentic_systems.integrations.adapters import openai_models as om
from agentic_systems.integrations.adapters import strands as sa
from agentic_systems.integrations.adapters import strands_scripted as ss
from agentic_systems.integrations.adapters.tools import (
    canonical_tool_callable,
    merge_tools,
    tool_identity,
)
from agentic_systems.integrations.config import FrameworkConfig
from agentic_systems.tools.decorators import tool


class Payload(BaseModel):
    value: int


@dataclass
class Record:
    value: int


def test_registry_config_and_tool_validation_contracts():
    with pytest.raises(ValueError, match="Unknown framework adapter"):
        framework_adapter("missing")
    with pytest.raises(ValidationError, match="Unknown framework"):
        FrameworkConfig(name="missing")
    with pytest.raises(TypeError, match="mappings"):
        FrameworkConfig(agent_kwargs=[("x", 1)])
    assert FrameworkConfig.coerce("").name == "native"

    anonymous = object()
    assert tool_identity(anonymous).endswith(f":{id(anonymous)}")
    assert tool_identity({"toolSpec": {"name": "lookup"}}) == "lookup"
    with pytest.raises(ValueError, match="collision"):
        merge_tools([{"name": "same"}], [{"name": "same"}])


def test_canonical_tool_callable_binds_positional_multi_parameter_inputs():
    @tool(name="multiply", description="Multiply two integers.")
    def multiply(a: int, b: int) -> dict[str, int]:
        return {"result": a * b}

    invoke = canonical_tool_callable(multiply)

    assert invoke(17, 19) == {"result": 323}
    assert invoke(a=17, b=19) == {"result": 323}


def test_bedrock_openai_translation_helpers_cover_all_shapes():
    raw, system = bo._bedrock_messages("hello")
    assert raw[0]["content"][0]["text"] == "hello"
    assert system == []

    items = [
        7,
        {"role": "system", "content": "system"},
        {"role": "developer", "content": [{"text": "developer"}]},
        {"role": "user", "content": [{"content": "ask"}, None]},
        {"role": "assistant", "content": "answer"},
        {
            "type": "function_call",
            "id": "id-1",
            "name": "tool",
            "arguments": "{'x': 1}",
        },
        {"type": "function_call", "name": "tool", "arguments": "raw"},
        {"type": "function_call_output", "call_id": "id-1", "output": '{"ok": true}'},
        {"type": "function_call_output", "call_id": "id-2", "output": "plain"},
    ]
    messages, system = bo._bedrock_messages(items)
    assert [entry["text"] for entry in system] == ["system", "developer"]
    assert messages[-1]["content"][0]["toolResult"]["content"][0]["json"] == {
        "ok": True
    }
    assert messages[-1]["content"][1]["toolResult"]["content"][0]["text"] == "plain"
    assert bo._bedrock_messages([])[0][0]["content"][0]["text"] == "[]"

    tools = [
        SimpleNamespace(name="", description="", params_json_schema=None),
        SimpleNamespace(name="lookup", description="", params_json_schema=None),
    ]
    specs = bo._bedrock_tools(tools)
    assert specs[0]["toolSpec"]["description"] == "Tool lookup"
    assert bo._tool_choice("auto", False) is None
    assert bo._tool_choice("required", True) == {"any": {}}
    assert bo._tool_choice("lookup", True) == {"tool": {"name": "lookup"}}
    assert bo._tool_choice("none", True) == {"auto": {}}

    response = bo._model_response(
        {
            "output": {
                "message": {
                    "content": [
                        None,
                        {"text": ""},
                        {"text": "done"},
                        {"toolUse": {"name": "lookup", "input": {"x": 1}}},
                    ]
                }
            },
            "usage": {"inputTokens": 2, "outputTokens": 3, "totalTokens": 5},
        }
    )
    assert len(response.output) == 2
    assert response.usage.total_tokens == 5
    assert bo._content_text("x") == "x"
    assert bo._content_text([{"text": "a"}, {"content": "b"}, None]) == "ab"
    assert bo._object('{"x": 1}') == {"x": 1}
    assert bo._object("x") == {"input": "x"}
    assert bo._decode(3) == 3
    assert bo._decode("[1]") == [1]
    assert bo._decode("{'x': 1}") == {"x": 1}
    assert bo._decode("not-data") == "not-data"
    assert bo._jsonable(Payload(value=2)) == {"value": 2}
    assert bo._jsonable((Payload(value=3),)) == [{"value": 3}]


def test_bedrock_model_positional_call_and_streaming_error():
    calls = []
    runtime = SimpleNamespace(
        converse=lambda **kwargs: (
            calls.append(kwargs)
            or {"output": {"message": {"content": [{"text": "ok"}]}}}
        )
    )
    model = bo.BedrockOpenAIModel(runtime, "model")
    settings = SimpleNamespace(
        tool_choice="any", max_tokens=4, temperature=0.2, top_p=0.9
    )
    result = asyncio.run(model.get_response(None, "hello", settings, []))
    assert result.output
    assert calls[0]["model_id"] == "model"

    async def consume():
        return await anext(model.stream_response())

    with pytest.raises(NotImplementedError, match="streaming"):
        asyncio.run(consume())


def test_scripted_openai_model_helper_contracts():
    tool = SimpleNamespace(
        name="lookup", params_json_schema={"properties": {"query": {}}}
    )
    assert om._plan_calls({"query": "x"}, [tool]) == [
        {"tool": "lookup", "input": {"query": "x"}}
    ]
    assert om._plan_calls("x", [tool]) == [{"tool": "lookup", "input": {"query": "x"}}]
    assert om._plan_calls("x", []) == []
    assert om._plan_calls({"steps": []}, [tool]) == []
    assert om._normalize_call({"name": "lookup", "payload": 3}, ["lookup"])[
        "input"
    ] == {"input": 3}
    with pytest.raises(TypeError, match="mappings"):
        om._normalize_call("bad", ["lookup"])
    with pytest.raises(KeyError, match="Unknown scripted"):
        om._normalize_call({"tool": "missing"}, ["lookup"])
    assert om._single_argument(SimpleNamespace(params_json_schema={}), "x") == {
        "input": "x"
    }
    assert om._decode_output(1) == 1
    assert om._decode_output("{'x': 1}") == {"x": 1}
    assert om._decode_output("raw") == "raw"
    assert om._parse_input([{"role": "user", "content": [{"text": '{"x": 1}'}]}]) == {
        "x": 1
    }
    assert om._parse_input([None]) == [None]
    assert om._jsonable(Payload(value=1)) == {"value": 1}

    model = om.ScriptedOpenAIModel()
    completed = asyncio.run(
        model.get_response(
            None, [{"type": "function_call_output", "output": "1"}], None, []
        )
    )
    assert completed.output
    multi = asyncio.run(
        model.get_response(
            input=[
                {"type": "function_call_output", "output": "1"},
                {"type": "function_call_output", "output": "2"},
            ],
            tools=[],
        )
    )
    assert multi.output
    echoed = asyncio.run(model.get_response(input="hello", tools=[]))
    assert echoed.output

    async def consume():
        return await anext(model.stream_response())

    with pytest.raises(NotImplementedError, match="streaming"):
        asyncio.run(consume())


def test_openai_adapter_normalization_and_json_helpers():
    agent = SimpleNamespace(engine="python-runtime", model="m")
    provider = RunResult(text="provider", engine="python-runtime", model="m")
    native = SimpleNamespace(
        last_agent=SimpleNamespace(model=SimpleNamespace(last_result=provider))
    )
    assert oa._normalize_result(agent, native, {"x": 1}, "eval") is provider

    class Dumped:
        def model_dump(self, mode="json"):
            return {"value": 1}

    class JsonOutput:
        def model_dump_json(self):
            return '{"value":1}'

    item = type(
        "ToolCallItem",
        (),
        {"raw_item": {"call_id": "c", "name": "lookup", "arguments": "bad"}},
    )()
    output = type(
        "ToolCallOutputItem", (), {"raw_item": {"call_id": "c", "output": Dumped()}}
    )()
    generic = SimpleNamespace(
        last_agent=None,
        final_output=JsonOutput(),
        raw_responses=[Dumped()],
        new_items=[item, output, SimpleNamespace(raw_item=3)],
        context_wrapper=SimpleNamespace(usage=Dumped()),
        to_input_list=lambda: [Dumped()],
    )
    result = oa._normalize_result(agent, generic, "input", "default")
    assert result.tool_events[0].input == {"value": "bad"}
    assert result.usage == {"value": 1}
    assert oa._usage(SimpleNamespace(context_wrapper=None)) == {}
    assert oa._failure(agent, "x", "eval", RuntimeError("boom")).ok is False
    assert oa._input_text({"x": 1}) == '{"x": 1}'
    assert oa._output_text("x") == "x"
    assert oa._output_text([1]) == "[1]"
    assert oa._output_data("x", '{"x": 1}') == {"x": 1}
    assert oa._output_data("x", "[1]") == {"value": [1]}
    assert oa._output_data("x", "bad") == {"text": "bad"}
    assert oa._json_object({"x": 1}) == {"x": 1}
    assert oa._json_object("[1]") == {"value": [1]}
    assert oa._jsonable(Record(1)) == {"value": 1}
    assert oa._jsonable((Record(2),)) == [{"value": 2}]

    configured = []
    oa._configure_model(
        SimpleNamespace(configure=lambda *args: configured.append(args)),
        RunPolicy(),
        "eval",
    )
    oa._configure_model(object(), RunPolicy(), "eval")
    assert configured

    from agents import ModelSettings

    native_agent = SimpleNamespace(model_settings=ModelSettings(), tools=[object()])
    named_policy = RunPolicy(
        max_tokens=321,
        temperature=0.7,
        tool_choice="multiply",
    )
    oa._configure_native_agent(native_agent, named_policy)
    assert native_agent.model_settings.temperature == 0.7
    assert native_agent.model_settings.max_tokens == 321
    assert native_agent.model_settings.tool_choice == "multiply"

    completion_agent = SimpleNamespace(model_settings=ModelSettings(), tools=[])
    oa._configure_native_agent(completion_agent, named_policy)
    assert completion_agent.model_settings.tool_choice is None


def test_scripted_strands_model_helpers_and_streams():
    model = ss.ScriptedStrandsModel()
    model.update_config(extra=True)
    assert model.get_config()["extra"] is True
    spec = {"toolSpec": {"name": "lookup"}}
    assert ss._tool_name(spec) == "lookup"
    assert ss._tool_name(SimpleNamespace(name="native")) == "native"
    assert ss._user_input("raw") == "raw"
    messages = [
        None,
        {"role": "user", "content": [{"text": "first"}]},
        {"role": "user", "content": [{"toolResult": {}}]},
    ]
    assert ss._user_input(messages) == "first"
    assert ss._user_input([{"role": "assistant", "content": []}]) == [
        {"role": "assistant", "content": []}
    ]
    assert ss._tool_outputs("raw") == []
    outputs = ss._tool_outputs(
        [
            None,
            {
                "content": [
                    None,
                    {"toolResult": {"content": [{"json": {"x": 1}}, {"text": "2"}]}},
                ]
            },
        ]
    )
    assert outputs == [[{"x": 1}, 2]]
    assert ss._tool_outputs(
        [
            {"content": [{"toolResult": {"content": [{"json": {"old": 1}}]}}]},
            {"content": [{"toolResult": {"content": [{"json": {"new": 2}}]}}]},
        ]
    ) == [{"new": 2}]
    assert (
        ss._tool_outputs(
            [
                {
                    "role": "user",
                    "content": [{"text": "old"}],
                },
                {
                    "role": "user",
                    "content": [{"toolResult": {"content": [{"json": {"old": 1}}]}}],
                },
                {
                    "role": "user",
                    "content": [{"text": "new"}],
                },
            ]
        )
        == []
    )
    assert ss._parse_value("raw") == "raw"
    assert ss._plan_calls("x", []) == []
    assert ss._plan_calls({"calls": []}, [spec]) == []
    assert ss._normalize_call({"tool_name": "lookup", "args": 1}, ["lookup"])[
        "input"
    ] == {"input": 1}
    with pytest.raises(TypeError, match="mappings"):
        ss._normalize_call(1, ["lookup"])
    with pytest.raises(KeyError, match="Unknown scripted"):
        ss._normalize_call({"name": "missing"}, ["lookup"])

    async def collect(messages, specs):
        return [event async for event in model.stream(messages, specs)]

    planned = asyncio.run(
        collect(
            [
                {
                    "role": "user",
                    "content": [{"text": '{"tool":"lookup","input":{"x":1}}'}],
                }
            ],
            [spec],
        )
    )
    assert any("toolUse" in str(event) for event in planned)
    finished = asyncio.run(
        collect(
            [{"content": [{"toolResult": {"content": [{"json": {"x": 1}}]}}]}], [spec]
        )
    )
    assert any("end_turn" in str(event) for event in finished)

    async def structured():
        return [item async for item in model.structured_output(Payload, '{"value": 4}')]

    assert asyncio.run(structured())[0]["output"].value == 4


def test_strands_adapter_helpers_cover_results_tools_and_failures():
    policy = RunPolicy(max_turns=5)
    agent = SimpleNamespace(
        engine="python-runtime",
        model="m",
        framework_config=SimpleNamespace(
            run_kwargs={"max_turns": 9, "limits": {"turns": 8}}
        ),
    )
    kwargs = sa._run_kwargs(agent, policy)
    assert kwargs["limits"]["turns"] == 5

    configured = []
    sa._configure_model(
        SimpleNamespace(configure=lambda *args: configured.append(args)), policy, "eval"
    )
    sa._configure_model(object(), policy, "eval")
    assert configured

    class OpenAICompatibleModel:
        def __init__(self):
            self.config = {"params": {"top_p": 0.8}}

        def update_config(self, **configuration):
            self.config.update(configuration)

    openai_model = OpenAICompatibleModel()
    named_policy = RunPolicy(
        max_tokens=321,
        temperature=0.7,
        tool_choice="multiply",
    )
    sa._configure_model(openai_model, named_policy, "eval")
    assert openai_model.config["params"] == {
        "top_p": 0.8,
        "temperature": 0.7,
        "max_tokens": 321,
        "tool_choice": {
            "type": "function",
            "function": {"name": "multiply"},
        },
    }

    class DirectModel:
        def __init__(self):
            self.config = {"model_id": "native-model"}
            self.updates = []

        def update_config(self, **configuration):
            self.updates.append(configuration)
            self.config.update(configuration)

    direct_model = DirectModel()
    sa._configure_model(direct_model, named_policy, "eval")
    assert direct_model.updates == [
        {
            "temperature": 0.7,
            "max_tokens": 321,
        }
    ]
    assert "params" not in direct_model.config

    no_max_tokens = DirectModel()
    sa._configure_model(no_max_tokens, RunPolicy(temperature=0.2), "eval")
    assert no_max_tokens.updates == [{"temperature": 0.2}]

    provider = RunResult(text="provider", engine="python-runtime", model="m")
    native_agent = SimpleNamespace(model=SimpleNamespace(last_result=provider))
    assert sa._normalize_result(agent, native_agent, object(), "x", "eval") is provider

    messages = [
        None,
        {
            "content": [
                None,
                {"toolUse": {"toolUseId": "c1", "name": "lookup", "input": {"x": 1}}},
                {
                    "toolResult": {
                        "toolUseId": "c1",
                        "status": "error",
                        "content": [{"text": "bad"}],
                    }
                },
                {"toolResult": {"toolUseId": "orphan", "content": []}},
            ]
        },
    ]
    generic_agent = SimpleNamespace(model=object(), messages=messages[1:])
    generic_result = SimpleNamespace(
        structured_output=Payload(value=2),
        message=Payload(value=2),
        metrics=Payload(value=3),
        stop_reason="done",
    )
    result = sa._normalize_result(
        agent, generic_agent, generic_result, {"x": 1}, "default"
    )
    events = sa._tool_events(messages)
    assert events[0].ok is False
    assert events[1].ok is True
    assert result.usage == {"value": 3}
    assert sa._failure(agent, "x", "eval", RuntimeError("boom")).ok is False
    assert sa._input_text({"x": 1}) == '{"x": 1}'
    assert sa._output_data("x", '{"x": 1}') == {"x": 1}
    assert sa._output_data("x", "[1]") == {"value": [1]}
    assert sa._output_data("x", "bad") == {"text": "bad"}
    assert sa._json_dict("x") == {}
    assert sa._jsonable(SimpleNamespace(to_dict=lambda: {"x": Payload(value=1)})) == {
        "x": {"value": 1}
    }

    empty_tool = SimpleNamespace(name="empty", function=None)
    with pytest.raises(ValueError, match="no function"):
        sa._strands_tool(empty_tool)


def test_scripted_openai_model_executes_native_handoff_calls():
    handoff = SimpleNamespace(
        tool_name="transfer_to_specialist",
        input_json_schema={"type": "object", "properties": {}},
    )
    model = om.ScriptedOpenAIModel()

    response = asyncio.run(
        model.get_response(
            None,
            '{"tool":"transfer_to_specialist","input":{}}',
            None,
            [],
            None,
            [handoff],
            None,
            previous_response_id=None,
            conversation_id=None,
            prompt=None,
        )
    )

    assert response.output[0].name == "transfer_to_specialist"
    assert om._single_argument(handoff, "value") == {"input": "value"}


def test_scripted_strands_model_invokes_structured_output_tool():
    model = ss.ScriptedStrandsModel()
    structured_spec = {
        "name": "Payload",
        "description": "IMPORTANT: This StructuredOutputTool is final.",
        "inputSchema": {"json": Payload.model_json_schema()},
    }
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "call",
                        "status": "success",
                        "content": [{"json": {"value": 7}}],
                    }
                }
            ],
        }
    ]

    async def collect():
        return [event async for event in model.stream(messages, [structured_spec])]

    events = asyncio.run(collect())

    assert any("Payload" in str(event) for event in events)
    assert any("tool_use" in str(event) for event in events)
    assert ss._is_structured_output_spec(structured_spec) is True
    assert ss._is_structured_output_spec(object()) is False


def test_scripted_strands_tool_outputs_ignore_non_mapping_messages():
    messages = [
        {"role": "user", "content": [{"text": "current turn"}]},
        object(),
    ]

    assert ss._tool_outputs(messages) == []
