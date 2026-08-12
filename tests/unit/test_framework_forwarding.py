from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import agentic_systems as toolkit
from agentic_systems.contracts import RunPolicy
from agentic_systems.integrations.adapters.base import effective_max_turns
from agentic_systems.integrations.adapters.strands import _run_kwargs
from agentic_systems.integrations.adapters.tools import merge_tools


def echo(value: str) -> dict:
    return {"value": value}


def test_framework_kwargs_are_exact_copied_and_frozen():
    agent_kwargs = {"handoff_description": "delegate"}
    run_kwargs = {"max_turns": 3, "session": object()}

    config = toolkit.framework(
        "openai-agents",
        agent_kwargs=agent_kwargs,
        run_kwargs=run_kwargs,
    )
    agent_kwargs["new"] = True
    run_kwargs["max_turns"] = 99

    assert config.agent_kwargs == {"handoff_description": "delegate"}
    assert config.run_kwargs["max_turns"] == 3
    assert config.run_kwargs["session"] is not None
    with pytest.raises(ValidationError, match="frozen"):
        config.name = "native"


def test_unknown_framework_kwargs_reach_the_native_sdk():
    agent = toolkit.agent(
        name="unknown-kwarg",
        tools=[toolkit.tool(echo)],
        engine="python-runtime",
        framework=toolkit.framework(
            "openai-agents",
            agent_kwargs={"definitely_not_an_sdk_kwarg": True},
        ),
    )

    with pytest.raises(TypeError, match="definitely_not_an_sdk_kwarg"):
        agent.prepare()


def test_native_tool_collisions_fail_before_execution():
    native_tool = SimpleNamespace(name="echo")
    agent = toolkit.agent(
        name="collision",
        tools=[toolkit.tool(echo)],
        engine="python-runtime",
        framework=toolkit.framework(
            "openai-agents",
            agent_kwargs={"tools": [native_tool]},
        ),
    )

    with pytest.raises(ValueError, match="Tool identity collision for 'echo'"):
        agent.prepare()


def test_turn_limits_can_only_tighten_run_policy():
    policy = RunPolicy(max_turns=4)
    assert effective_max_turns(policy, {"max_turns": 2}) == 2
    assert effective_max_turns(policy, {"max_turns": 20}) == 4
    assert effective_max_turns(policy, {}) == 4
    with pytest.raises(ValueError, match="must be >= 1"):
        effective_max_turns(policy, {"max_turns": 0})

    agent = SimpleNamespace(
        framework_config=toolkit.framework(
            "strands",
            run_kwargs={"limits": {"turns": 20, "output_tokens": 100}},
        )
    )
    assert _run_kwargs(agent, policy) == {
        "limits": {"turns": 4, "output_tokens": 100}
    }


def test_native_tool_objects_are_preserved_by_identity():
    converted = SimpleNamespace(name="converted")
    native = SimpleNamespace(name="native")

    assert merge_tools([converted], [native]) == [converted, native]
