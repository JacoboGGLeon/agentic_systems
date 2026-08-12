from __future__ import annotations

import asyncio
import importlib

import pytest
from pydantic import BaseModel

from agentic_systems.agents import (
    Agent,
    _coerce_output_data,
    _contract_name,
    _json_like,
)
from agentic_systems.contracts import RunPolicy
from agentic_systems.core.runtime import RuntimeConfig
from agentic_systems.engines.names import PYTHON_DIRECT_ENGINE
from agentic_systems.results import RunResult
from agentic_systems.system import AgenticSystem
from agentic_systems.tools import Tool

system_module = importlib.import_module("agentic_systems.system")


class EchoEngine:
    def __init__(self, ok=True, fail=False):
        self.ok = ok
        self.fail = fail

    def run(self, agent, input, policy, *, mode="default"):
        if self.fail:
            raise RuntimeError("sync boom")
        return RunResult(
            text="sync", data={"input": input}, ok=self.ok, engine="echo", mode=mode
        )


class SyncOnlyEngine:
    def run(self, agent, input, policy, *, mode="default"):
        return RunResult(
            text="threaded",
            data={"input": input},
            ok=True,
            engine="sync-only",
            mode=mode,
        )


def test_agent_bind_describe_async_scheduler_and_validation():
    def add(a: int, b: int) -> dict:
        return {"result": a + b}

    add_tool = Tool(add, name="add")
    agent = Agent(name="direct", tools=[add_tool], skills=[], engine="python-runtime")
    assert "Agent `direct`" in agent.describe()
    assert _contract_name(BaseModel) == "BaseModel"
    assert _json_like(type("X", (), {})) == "X"
    assert _coerce_output_data(RunResult(text="hello"), None).final == {"text": "hello"}
    assert _coerce_output_data(RunResult(text="", data={"a": 1}), None).final == {
        "a": 1
    }

    with pytest.raises(ValueError):
        Agent(name=" ")
    with pytest.raises(TypeError):
        agent.bind(None)
    assert agent.bind(agent.system) is agent if agent.system is not None else True

    runtime = RuntimeConfig(
        provider="python-runtime", scheduler={"timeout_s": None, "max_retries": 0}
    )
    runtime_agent = Agent(name="runtime", tools=[add_tool], runtime=runtime)
    assert runtime_agent.engine == PYTHON_DIRECT_ENGINE

    system = AgenticSystem(
        model="m",
        region="r",
        runtime={
            "provider": "python-runtime",
            "scheduler": {"timeout_s": None, "max_retries": 0},
        },
    )
    system._engines[PYTHON_DIRECT_ENGINE] = EchoEngine()
    sys_agent = system.agent(
        name="sys", instructions="x", tools=[add_tool], engine="python-runtime"
    )
    assert (
        asyncio.run(sys_agent.arun({"tool": "add", "input": {"a": 1, "b": 2}})).ok
        is True
    )
    assert sys_agent.bind(system) is sys_agent
    default_mode_result = sys_agent.run({"tool": "add", "input": {"a": 1, "b": 2}})
    assert default_mode_result.mode == "eval"

    system._engines[PYTHON_DIRECT_ENGINE] = SyncOnlyEngine()
    sync_only = system.agent(
        name="sync_only", instructions="x", tools=[add_tool], engine="python-runtime"
    )
    assert asyncio.run(sync_only.arun("x")).text == "threaded"

    failing_system = AgenticSystem(
        model="m",
        region="r",
        runtime={
            "provider": "python-runtime",
            "scheduler": {"timeout_s": None, "max_retries": 0},
        },
    )
    failing_system._engines[PYTHON_DIRECT_ENGINE] = EchoEngine(fail=True)
    failing_agent = failing_system.agent(
        name="fail", instructions="x", tools=[add_tool], engine="python-runtime"
    )
    result = failing_agent.run({"tool": "add", "input": {"a": 1, "b": 2}})
    assert result.ok is False
    assert result.meta["scheduler_execution"]["timed_out"] is False

    async_result = asyncio.run(
        failing_agent.arun({"tool": "add", "input": {"a": 1, "b": 2}})
    )
    assert async_result.ok is False
    assert async_result.meta["scheduler_execution"]["timed_out"] is False

    class SlowAsyncEngine:
        async def arun(self, agent, input, policy, *, mode="default"):
            await asyncio.sleep(0.05)
            return RunResult(text="late", ok=True, engine="slow", mode=mode)

    slow_system = AgenticSystem(
        model="m",
        region="r",
        runtime={
            "provider": "python-runtime",
            "scheduler": {"timeout_s": 0.001, "max_retries": 0},
        },
    )
    slow_system._engines[PYTHON_DIRECT_ENGINE] = SlowAsyncEngine()
    slow_agent = slow_system.agent(
        name="slow", instructions="x", tools=[add_tool], engine="python-runtime"
    )
    slow_result = asyncio.run(slow_agent.arun("x"))
    assert slow_result.data["error"]["code"] == "scheduler_timeout"

    non_direct = Agent(name="cloud", engine="openai-runtime")
    with pytest.raises(RuntimeError):
        asyncio.run(non_direct.arun("x"))

    dup = Agent(name="dup", tools=[add_tool], engine="python-runtime")
    dup.tools = ("add", "add")
    validation = dup.validate()
    assert any(issue.code == "duplicate_agent_tool" for issue in validation.issues)

    def untyped(x):
        return []

    bad_tool = Tool(untyped, name="bad_tool")
    invalid_agent = Agent(name="invalid", tools=[], engine="python-runtime")
    invalid_agent._direct_tools = (bad_tool,)
    invalid_agent.tools = ("bad_tool",)
    invalid_validation = invalid_agent.validate()
    assert any(
        issue.code == "missing_parameter_annotation"
        for issue in invalid_validation.issues
    )

    contract_agent = Agent(
        name="contract",
        tools=[add_tool],
        engine="python-runtime",
        contract={"must_call": ["add"]},
        policy={"max_tool_calls": 0} if False else None,
    )
    contract_agent.policy = RunPolicy(max_tool_calls=1)
    assert contract_agent.validate().ok is True
