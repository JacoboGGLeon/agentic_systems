from types import SimpleNamespace
import asyncio

import pytest
from pydantic import BaseModel
from strands.tools.registry import ToolRegistry
from strands.tools.structured_output.structured_output_tool import StructuredOutputTool

from agentic_systems.contracts import RunPolicy
from agentic_systems.integrations.adapters import strands as adapter


class ArbitraryPayload(BaseModel):
    value: str


def native():
    return SimpleNamespace(model=SimpleNamespace(), tool_registry=ToolRegistry())


def event(name, identity):
    return {
        "contentBlockStart": {
            "start": {
                "toolUse": {
                    "name": name,
                    "toolUseId": identity,
                }
            }
        }
    }


def test_schema_projection_and_conflict_do_not_mutate_config():
    config = {}
    agent = SimpleNamespace(
        output_contract=ArbitraryPayload,
        framework_config=SimpleNamespace(run_kwargs=config),
    )
    assert (
        adapter._run_kwargs(agent, RunPolicy())["structured_output_model"]
        is ArbitraryPayload
    )
    assert config == {}
    config["structured_output_model"] = BaseModel
    with pytest.raises(ValueError, match="must agree"):
        adapter._run_kwargs(agent, RunPolicy())


@pytest.mark.parametrize("limit", [0, 1, None])
def test_registered_output_is_not_a_business_action(limit):
    agent = native()
    adapter._configure_output(agent, {"structured_output_model": ArbitraryPayload})
    internal = StructuredOutputTool(ArbitraryPayload)
    agent.tool_registry.dynamic_tools[internal.tool_name] = internal
    adapter._reset_tool_budget(agent.model, limit)
    batch = [
        event(internal.tool_name, "out-1"),
        {"contentBlockStop": {}},
        {"messageStop": {"stopReason": "tool_use"}},
    ]
    kept = adapter._limit_tool_use_events(agent.model, batch, suppress_tools=True)
    assert kept == batch
    assert (
        sum(adapter._business_tool_use_count(agent.model, item) for item in kept) == 0
    )
    assert agent.model._agentic_systems_output_ids == {"out-1"}


def test_unregistered_lookalike_stays_blocked():
    agent = native()
    adapter._configure_output(agent, {"structured_output_model": ArbitraryPayload})
    adapter._reset_tool_budget(agent.model, 0)
    assert (
        adapter._limit_tool_use_events(agent.model, [event("ArbitraryPayload", "fake")])
        == []
    )
    assert agent.model._agentic_systems_output_ids == set()


def test_collision_is_rejected_before_invocation():
    agent = native()
    agent.tool_registry.registry["ArbitraryPayload"] = object()
    with pytest.raises(ValueError, match="collides"):
        adapter._configure_output(agent, {"structured_output_model": ArbitraryPayload})


def test_mixed_batch_does_not_turn_materialization_into_end_turn():
    agent = native()
    adapter._configure_output(agent, {"structured_output_model": ArbitraryPayload})
    internal = StructuredOutputTool(ArbitraryPayload)
    agent.tool_registry.dynamic_tools[internal.tool_name] = internal
    adapter._reset_tool_budget(agent.model, 0)
    batch = [
        event("business", "bad"),
        {"contentBlockStop": {}},
        event(internal.tool_name, "out"),
        {"contentBlockStop": {}},
        {"messageStop": {"stopReason": "tool_use"}},
    ]
    kept = adapter._limit_tool_use_events(agent.model, batch)
    assert kept[-1]["messageStop"]["stopReason"] == "tool_use"
    assert agent.model._agentic_systems_rejected_tool_calls == [
        {"name": "business", "reason": "max_tool_calls_exhausted"}
    ]


@pytest.mark.parametrize("asynchronous", [False, True])
def test_real_sdk_output_contract_preserves_business_and_materialization(asynchronous):
    import agentic_systems as toolkit

    @toolkit.tool
    def business(value: str) -> dict:
        return {"value": value}

    agent = toolkit.agent(
        name="structured",
        tools=[business],
        framework="strands",
        runtime=toolkit.runtime(provider="python-runtime"),
        output=ArbitraryPayload,
        policy=RunPolicy(max_tool_calls=1, max_turns=4),
    )
    payload = {"tool": "business", "input": {"value": "typed"}}
    result = asyncio.run(agent.arun(payload)) if asynchronous else agent.run(payload)
    assert result.ok
    assert result.data == {"value": "typed"}
    assert [item.name for item in result.tool_events] == ["business"]
    materialization = result.meta["output_materialization"]
    assert len(materialization) == 1
    assert materialization[0]["ok"]
    assert materialization[0]["id"] != result.tool_events[0].id
