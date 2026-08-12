from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from agentic_systems.contracts import RunPolicy
from agentic_systems.providers import PythonRuntimeEngine, PythonRuntimeProvider
from agentic_systems.providers.python_runtime import (
    _json_like,
    _parse_plan,
    _parse_pipeline,
    _summary_from_output_payload,
)
from agentic_systems.tools import Tool


def test_python_runtime_provider_plan_pipeline_errors_and_async():
    def add(a: int, b: int) -> dict:
        return {"result": a + b, "summary": f"sum={a + b}"}

    def double(result: int, summary: str = "", ok: bool = True, tool: str = "") -> dict:
        return {"result": result * 2, "message": f"double={result * 2}"}

    add_tool = Tool(add, name="add")
    double_tool = Tool(double, name="double")
    agent = SimpleNamespace(
        name="py",
        model="m",
        tools=("add", "double"),
        available_tools=lambda: [add_tool, double_tool],
    )
    provider = PythonRuntimeProvider()

    plan_result = provider.run(
        agent,
        {
            "steps": [
                {"tool": "add", "input": {"a": 2, "b": 3}},
                {"name": "double", "args": {"result": 5}},
            ]
        },
        RunPolicy(),
        mode="eval",
    )
    assert plan_result.ok is True
    assert plan_result.data["last"]["result"] == 10
    assert "double=10" in plan_result.text

    pipeline_result = provider.run(
        agent,
        {"pipeline": {"order": ["add", "double"], "state": {"a": 4, "b": 6}}},
        RunPolicy(),
        mode="audit",
    )
    assert pipeline_result.meta["execution_style"] == "state_pipeline"
    assert pipeline_result.data["last"]["result"] == 20

    direct_pipeline = provider.run(
        agent, {"tools": ["add"], "state": {"a": 1, "b": 2}}, RunPolicy(), mode="audit"
    )
    assert direct_pipeline.data["result"] == 3

    too_many = provider.run(
        agent,
        {
            "steps": [
                {"tool": "add", "input": {"a": 1, "b": 1}},
                {"tool": "double", "input": {"result": 2}},
            ]
        },
        RunPolicy(max_tool_calls=1),
        mode="eval",
    )
    assert too_many.data["error"]["code"] == "max_tool_calls_exceeded"

    bad_pipeline = provider.run(agent, {"pipeline": "add"}, RunPolicy(), mode="eval")
    assert bad_pipeline.data["error"]["code"] == "TypeError"

    unknown_pipeline = provider.run(
        agent, {"pipeline": ["missing"]}, RunPolicy(), mode="eval"
    )
    assert unknown_pipeline.data["error"]["code"] == "KeyError"

    assert (
        provider.run(SimpleNamespace(name="empty", tools=()), {}, RunPolicy()).data[
            "error"
        ]["code"]
        == "missing_tools"
    )
    assert (
        provider.run(agent, "not json", RunPolicy()).data["error"]["code"]
        == "ValueError"
    )
    assert provider.run(agent, "", RunPolicy()).data["error"]["code"] == "ValueError"
    assert (
        provider.run(
            agent, [{"tool_name": "add", "payload": {"a": 3, "b": 4}}], RunPolicy()
        ).data["result"]
        == 7
    )
    assert provider.run(agent, 123, RunPolicy()).data["error"]["code"] == "ValueError"
    assert (
        provider.run(agent, {"tool": "missing", "input": {}}, RunPolicy()).data[
            "error"
        ]["code"]
        == "KeyError"
    )
    assert (
        provider.run(
            agent,
            {"tool": "add", "input": {"a": "bad", "b": 2}},
            RunPolicy(repair=False),
        ).ok
        is False
    )

    single_agent = SimpleNamespace(
        name="single", model=None, tools=("add",), available_tools=lambda: [add_tool]
    )
    assert provider.run(single_agent, "raw text", RunPolicy()).data["ok"] is False
    assert (
        provider.run(single_agent, {"a": 8, "b": 9}, RunPolicy()).data["result"] == 17
    )
    assert (
        asyncio.run(
            provider.arun(
                single_agent, {"tool": "add", "input": {"a": 1, "b": 2}}, RunPolicy()
            )
        ).data["result"]
        == 3
    )
    assert isinstance(PythonRuntimeEngine(), PythonRuntimeProvider)

    tools = {"add": add_tool}
    assert _parse_pipeline("x", tools) is None
    with pytest.raises(TypeError):
        _parse_plan(["bad"], tools)


def test_python_runtime_handles_pipeline_and_input_errors():
    class PayloadModel(BaseModel):
        a: int
        b: int

    def add(a: int, b: int) -> dict:
        return {"result": a + b}

    def fail(result: int = 0, ok: bool = True, tool: str = "") -> dict:
        raise RuntimeError("pipeline boom")

    add_tool = Tool(add, name="add")
    fail_tool = Tool(fail, name="fail")
    agent = SimpleNamespace(
        name="py",
        model=None,
        tools=("add", "fail"),
        available_tools=lambda: [add_tool, fail_tool],
    )
    provider = PythonRuntimeProvider()

    too_many_pipeline = provider.run(
        agent,
        {"pipeline": ["add", "fail"], "state": {"a": 1, "b": 2}},
        RunPolicy(max_tool_calls=1),
    )
    assert too_many_pipeline.data["error"]["code"] == "max_tool_calls_exceeded"

    broken_pipeline = provider.run(
        agent,
        {"pipeline": ["add", "fail"], "state": {"a": 1, "b": 2}},
        RunPolicy(repair=False),
    )
    assert broken_pipeline.ok is False
    assert broken_pipeline.meta["planned_tool_calls"] == 2

    single_agent = SimpleNamespace(
        name="single", tools=("add",), available_tools=lambda: [add_tool]
    )
    scalar = provider.run(single_agent, 99, RunPolicy())
    assert scalar.ok is False
    assert scalar.data["tool"] == "add"

    missing_tool_name = provider.run(agent, {"steps": [{"input": {}}]}, RunPolicy())
    assert missing_tool_name.data["error"]["code"] == "ValueError"

    model_input = provider.run(single_agent, PayloadModel(a=2, b=5), RunPolicy())
    assert model_input.data["error"]["code"] == "TypeError"
    assert _json_like(PayloadModel(a=2, b=5)) == {"a": 2, "b": 5}
    assert _summary_from_output_payload(["not", "mapping"]) == ""
