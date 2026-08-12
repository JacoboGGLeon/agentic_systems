import asyncio
import os

import pytest
from pydantic import BaseModel

from agentic_systems import (
    AgenticSystem,
    RunResult,
)
from agentic_systems.agents import (
    Agent,
    _coerce_input,
    _coerce_output_data,
    _try_parse_json_object,
)


def build_system(strict=True, defaults=None):
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(
        model="demo-model", region="us-east-1", strict=strict, defaults=defaults
    )


class EchoEngine:
    name = "bedrock"

    def run(self, agent, input, policy, *, mode="default"):
        if isinstance(input, BaseModel):
            payload = input.model_dump(mode="json")
        else:
            payload = input if isinstance(input, dict) else {"input": input}
        text = payload.get("text") or payload.get("input") or "ok"
        data = payload.get("data") or {"answer": str(text), "score": 1}
        return RunResult(
            text=str(text),
            data=data,
            ok=True,
            engine=self.name,
            model=agent.model,
            mode=mode,
        )

    async def arun(self, agent, input, policy, *, mode="default"):
        return self.run(agent, input, policy, mode=mode)


class InputModel(BaseModel):
    input: str


class OutputModel(BaseModel):
    answer: str
    score: int = 1


def test_agent_input_output_coercion_accepts_supported_shapes():
    model = InputModel(input="ready")
    assert _coerce_input("raw", None) == "raw"
    assert _coerce_input(model, InputModel) is model
    assert _coerce_input({"input": "dict"}, InputModel).input == "dict"
    assert _coerce_input("scalar", InputModel).input == "scalar"

    assert _try_parse_json_object("not json") == {"text": "not json"}
    assert _try_parse_json_object('["a"]') == {"value": ["a"]}
    assert _try_parse_json_object('{"answer":"yes"}') == {"answer": "yes"}

    result = RunResult(text='{"answer":"yes","score":2}')
    coerced = _coerce_output_data(result, OutputModel)
    assert coerced.data == {"answer": "yes", "score": 2}
    same = RunResult(text="x", data={"answer": "data", "score": 3})
    assert _coerce_output_data(same, OutputModel).data["answer"] == "data"
    untouched = RunResult(text="x")
    assert _coerce_output_data(untouched, None) is untouched


def test_agent_runtime_paths_as_node_as_tool_eval_and_loop_error():
    system = build_system()
    system._engines["bedrock"] = EchoEngine()
    agent = system.agent(
        name="echo", instructions="echo", input=InputModel, output=OutputModel
    )

    result = agent.run_sync("hello", mode="eval", config={"max_tokens": 10})
    assert result.data == {"answer": "hello", "score": 1}
    assert (
        asyncio.run(agent.arun("async hello", mode="eval")).data["answer"]
        == "async hello"
    )

    async def call_run_sync_inside_loop():
        assert agent.run_sync("loop-safe").text == "loop-safe"
        async_node = agent.as_async_node(
            input=lambda state: state["value"], output="answer"
        )
        assert (await async_node({"value": "async node"}))["answer"] == "async node"

    asyncio.run(call_run_sync_inside_loop())

    missing_node = agent.as_node(input="missing")
    with pytest.raises(Exception, match="input key 'missing'"):
        missing_node({"prompt": "x"})

    callable_node = agent.as_node(
        input=lambda state: {"input": state["value"]},
        output=lambda run_result, state: {
            "custom": run_result.data["answer"],
            "kept": state["keep"],
        },
        trace=None,
    )
    assert callable_node({"value": "via callable", "keep": 7}) == {
        "custom": "via callable",
        "kept": 7,
    }

    empty_update_node = agent.as_node(
        input=lambda state: "empty", output=None, trace=None
    )
    assert empty_update_node({}) == {}

    tool = agent.as_tool(name="tools.echo", description="Run echo")
    assert tool.__name__ == "tools_echo"
    assert tool.__doc__ == "Run echo"
    assert tool("from tool")["data"]["answer"] == "from tool"

    report = agent.eval([{"input": "case", "expected": {"text_contains": "case"}}])
    assert report.ok is True


def test_agent_validation_error_paths_direct_construction():
    system = build_system()
    with pytest.raises(ValueError, match="unknown_agent_tool"):
        Agent(system=system, name="bad", instructions="x", tools=("missing",))
    with pytest.raises(ValueError, match="contract_references_unknown_tool"):
        Agent(
            system=system,
            name="bad_contract",
            instructions="x",
            tools=(),
            contract={"must_call": ["missing"]},
        )
    with pytest.raises(ValueError, match="langgraph_is_not_engine"):
        Agent(
            system=system,
            name="bad_engine",
            instructions="x",
            tools=(),
            engine="langgraph",
        )

    openai_agent = Agent(
        system=system,
        name="openai_framework_agent",
        instructions="x",
        tools=(),
        engine="openai-runtime",
        framework="openai-agents",
    )
    assert openai_agent.engine == "openai-runtime"
    assert openai_agent.framework == "openai-agents"
    with pytest.raises(ValueError, match="openai-agents"):
        Agent(
            system=system,
            name="bad_framework",
            instructions="x",
            tools=(),
            engine="openai-runtime",
            framework="unsupported-framework",
        )


def test_agent_sync_run_inside_loop_reraises_engine_error():
    class BrokenEngine:
        def run(self, agent, input, policy, *, mode="default"):
            raise RuntimeError("controlled sync failure")

    system = build_system()
    system._engines["bedrock"] = BrokenEngine()
    agent = system.agent(name="broken", instructions="fail")

    async def call_inside_loop():
        with pytest.raises(RuntimeError, match="controlled sync failure"):
            agent.run("x")

    asyncio.run(call_inside_loop())
