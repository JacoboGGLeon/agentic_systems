from __future__ import annotations

from pydantic import BaseModel

import agentic_systems as ags
from agentic_systems.engines.names import OPENAI_RUNTIME_ENGINE
from agentic_systems.system import AgenticSystem


class AddInput(BaseModel):
    a: int
    b: int


class AddOutput(BaseModel):
    result: int


def add_fn(data: AddInput) -> AddOutput:
    return AddOutput(result=data.a + data.b)


def test_tool_supports_pydantic_aliases_and_infers_name() -> None:
    tool = ags.Tool(add_fn, input=AddInput, output=AddOutput)

    assert tool.name == "add_fn"
    assert tool.input_schema is AddInput
    assert tool.output_schema is AddOutput

    result = tool.run({"a": 17, "b": 25})

    assert result.ok is True
    assert result.data == {"result": 42}
    assert result.tool_events[0].name == "add_fn"


def test_decorator_supports_pydantic_aliases() -> None:
    @ags.tool(input=AddInput, output=AddOutput)
    def sumar(data: AddInput) -> AddOutput:
        return AddOutput(result=data.a + data.b)

    result = sumar.run({"a": 20, "b": 22})

    assert result.ok is True
    assert result.data == {"result": 42}
    assert sumar.info()["input_schema"]["name"] == "AddInput"
    assert sumar.info()["output_schema"]["name"] == "AddOutput"


def test_pydantic_tool_schema_is_preserved_for_openai_runtime_bridge() -> None:
    tool = ags.Tool(add_fn, input=AddInput, output=AddOutput)
    system = AgenticSystem(model="dummy", strict=True)
    agent = system.agent(
        name="math_agent",
        instructions="Use tools.",
        tools=[tool],
        engine=OPENAI_RUNTIME_ENGINE,
    )

    assert agent.tools == ("add_fn",)
    spec = system._runtime._tools["add_fn"]
    assert spec.input_model is AddInput
    assert spec.input_schema["properties"]["a"]["type"] == "integer"

    envelope = system._runtime.execute_tool("add_fn", {"a": 40, "b": 2})
    assert envelope.ok is True
    assert envelope.data == {"result": 42}


def test_explicit_keyword_runner_accepts_state_pipeline_without_steps_or_fields_mapper() -> None:
    class AddState(BaseModel):
        x: int | None = None
        y: int | None = None
        result: int | None = None

    def add_state(data: AddState) -> AddState:
        return AddState(result=(data.x or 0) + (data.y or 0))

    tool = ags.Tool(add_state, name="add_state", input=AddState, output=AddState)

    agent = ags.Agent(name="state_agent", tools=[tool], engine="python-direct")

    result = agent.run({"tool": "add_state", "input": {"x": 17, "y": 25}}, mode="eval")

    assert result.ok is True
    assert result.data["result"] == 42
    assert result.data["tool"] == "add_state"
