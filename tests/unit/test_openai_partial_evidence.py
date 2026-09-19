"""Completed SDK tool calls survive a later operational failure, without network."""

import asyncio
from types import SimpleNamespace

import pytest
from agents import Agent, Runner, function_tool
from agents.tool_context import ToolContext

from agentic_systems.contracts import RunPolicy
from agentic_systems.integrations.adapters.openai_agents import (
    OpenAIAgentsFrameworkAdapter,
)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("failed_tool", [False, True])
def test_completed_tool_survives_connection_failure(
    monkeypatch, asynchronous, failed_tool
):
    def multiply(a: int, b: int) -> dict:
        if failed_tool:
            return {
                "__agentic_systems_tool_result__": {
                    "ok": False,
                    "data": {},
                    "error": {"code": "controlled", "message": "failed"},
                }
            }
        return {"product": a * b}

    native = Agent(name="worker", tools=[function_tool(multiply)], model="unused")
    original = native.tools[0].on_invoke_tool
    agent = SimpleNamespace(
        engine="openai-runtime",
        model="unused",
        available_tools=lambda: [SimpleNamespace(name="multiply")],
        framework_config=SimpleNamespace(agent_kwargs={}, run_kwargs={}),
    )
    adapter = OpenAIAgentsFrameworkAdapter()
    monkeypatch.setattr(adapter, "prepare", lambda *_: native)

    async def run(execution_agent, *_args, **_kwargs):
        for identity in ("first", "second"):
            await execution_agent.tools[0].on_invoke_tool(
                ToolContext(
                    context=None,
                    tool_name="multiply",
                    tool_call_id=identity,
                    tool_arguments='{"a":23,"b":29}',
                ),
                '{"a":23,"b":29}',
            )
        raise ConnectionError("after tool completion")

    monkeypatch.setattr(Runner, "run", run)
    monkeypatch.setattr(Runner, "run_sync", lambda *a, **k: asyncio.run(run(*a, **k)))
    for _ in range(2):
        if asynchronous:
            result = asyncio.run(
                adapter.arun(agent, object(), "input", RunPolicy(), mode="eval")
            )
        else:
            result = adapter.run(agent, object(), "input", RunPolicy(), mode="eval")
        assert result.ok is False
        assert "after tool completion" in result.text
        assert [e.id for e in result.tool_events] == ["first", "second"]
        assert all(e.ok is not failed_tool for e in result.tool_events)
        assert all(e.input == {"a": 23, "b": 29} for e in result.tool_events)
        assert "after tool completion" in result.text
        assert len([s for s in result.lineage().steps if s.kind == "tool"]) == 2
    assert native.tools[0].on_invoke_tool is original


def test_concurrent_observers_are_isolated_and_snapshot_outputs():
    from agentic_systems.integrations.adapters.openai_agents import (
        _execution_agent,
        _observe_tools,
    )
    from agentic_systems.integrations.adapters.tools import tool_name_aliases

    shared = {"items": [1]}

    async def invoke(context, arguments):
        await asyncio.sleep(0)
        return shared

    tool = SimpleNamespace(name="multiply", on_invoke_tool=invoke)
    cached = SimpleNamespace(tools=[tool, object()])
    left, right = _execution_agent(cached), _execution_agent(cached)
    aliases = tool_name_aliases([tool])
    left_events, right_events = (
        _observe_tools(left, aliases),
        _observe_tools(right, aliases),
    )

    async def run():
        await asyncio.gather(
            left.tools[0].on_invoke_tool(SimpleNamespace(tool_call_id="left"), "{}"),
            right.tools[0].on_invoke_tool(SimpleNamespace(tool_call_id="right"), "{}"),
        )

    asyncio.run(run())
    shared["items"].append(2)
    assert [e.id for e in left_events] == ["left"]
    assert [e.id for e in right_events] == ["right"]
    assert left_events[0].output == {"data": {"items": [1]}}
    assert right_events[0].output == {"data": {"items": [1]}}
    assert cached.tools[0].on_invoke_tool is invoke
