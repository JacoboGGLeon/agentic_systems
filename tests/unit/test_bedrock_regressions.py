import asyncio
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from agentic_systems import (
    AgentContract,
    RunPolicy,
)
from agentic_systems.engines.bedrock import _input_to_prompt


def test_bedrock_input_to_prompt_accepts_supported_shapes():
    class Dumpable(BaseModel):
        value: int

    class NotJson:
        def __str__(self):
            return "not-json"

    assert _input_to_prompt(None) == ""
    assert _input_to_prompt("hello") == "hello"
    assert '"value": 1' in _input_to_prompt(Dumpable(value=1))
    assert _input_to_prompt({"x": {1, 2}}) == "{'x': {1, 2}}"
    assert _input_to_prompt(NotJson()) == "not-json"


def test_bedrock_async_openai_prompt_and_environment_paths():
    class RuntimeForBedrock:
        region_name = "us-east-1"

        def run_direct(self, prompt, **kwargs):
            return {"final_text": f"bedrock:{prompt}", "tool_calls": [], "raw_responses": []}

    fake_system = SimpleNamespace(_runtime=RuntimeForBedrock(), model="model-x")
    agent = SimpleNamespace(instructions="inst", tools=(), model=None, contract=AgentContract())
    from agentic_systems.engines.bedrock import BedrockEngine

    arun_result = asyncio.run(BedrockEngine(fake_system).arun(agent, "async", RunPolicy(), mode="debug"))
    assert arun_result.text == "bedrock:async"
    assert arun_result.mode == "debug"

    from agentic_systems.providers.openai_runtime import _input_to_prompt as openai_input_to_prompt

    assert openai_input_to_prompt("already text") == "already text"

    from agentic_systems import AgenticEnvironment

    class AsyncGraph:
        async def ainvoke(self, state):
            return {**state, "async": True}

    env = AgenticEnvironment(records=[{"case_id": "a"}], graph=AsyncGraph())
    env.reset(seed=11)
    observation, reward, terminated, truncated, info = asyncio.run(env.astep())
    assert observation is None
    assert terminated is True and truncated is False
    assert info["graph_state"]["async"] is True

    class SyncGraphOnly:
        def invoke(self, state):
            return "sync-output"

    env = AgenticEnvironment(records=[{"case_id": "b"}], graph=SyncGraphOnly())
    env.reset(seed=12)
    *_, info = asyncio.run(env.astep())
    assert info["graph_state"] == {"output": "sync-output"}

    class NoInvokeAsync:
        pass

    env = AgenticEnvironment(records=[{"case_id": "c"}], graph=NoInvokeAsync())
    env.reset(seed=13)
    with pytest.raises(TypeError, match="ainvoke"):
        asyncio.run(env.astep())
