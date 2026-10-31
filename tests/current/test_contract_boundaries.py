"""Invalid declarations fail before effects; serialized data stays explicit."""

import asyncio
import json

import pydantic
import pytest

import agentic_systems as toolkit


@toolkit.tool
def first(value: int) -> dict:
    return {"value": value + 1}


@toolkit.tool
def second(value: int) -> dict:
    return {"value": value * 2}


@pytest.mark.parametrize("contract,error", [
    ({"unknown": True}, ValueError),
    ({"output_schema": []}, TypeError),
    ({"output_schema": {"$ref": "https://example.invalid/schema"}}, ValueError),
    ({"tool_expectation": {"all_of": "first"}}, TypeError),
    ({"tool_expectation": {"all_of": ["missing"]}}, ValueError),
    ({"tool_expectation": {"all_of": ["first"], "forbidden": ["first"]}}, ValueError),
    ({"tool_expectation": {"any_of": ["first"], "allowed": []}}, ValueError),
    ({"tool_expectation": {"min_count": -1}}, ValueError),
    ({"tool_expectation": {"min_count": 2}}, ValueError),
    ({"tool_expectation": {"all_of": ["first", "second"]}}, ValueError),
    ({"completion": "guess"}, ValueError),
    ({"failure_policy": "guess"}, ValueError),
    ({"expected_output": []}, TypeError),
    ({"expected_tool_outputs": {"missing": {}}}, ValueError),
])
def test_contract_declarations_reject_contradictions_and_remote_resolution(contract, error):
    skill = toolkit.skill(name="arithmetic", tools=(first, second))
    with pytest.raises(error):
        toolkit.Agent("invalid", runtime=toolkit.runtime(provider="openai-runtime", model="compile-only", max_tool_calls=1),
                      skills=(skill,), contract=contract).compile()


@pytest.mark.parametrize("sources", [["policy"], ("",), (3,)])
def test_context_requires_explicit_source_identifiers(sources):
    with pytest.raises(TypeError):
        toolkit.Context({"currency": "MXN"}, sources=sources)


def test_memory_remembers_evidence_once_and_context_is_not_arbitrary_state():
    with pytest.raises(TypeError):
        toolkit.Context([1, 2])
    memory = toolkit.Memory()
    with pytest.raises(TypeError):
        memory.remember({"ok": True})
    result = toolkit.RunResult(data={"value": 3})
    memory.remember(result)
    before = memory.read()
    memory.remember(result)
    assert memory.read() == before and len(before) == 1


def test_tool_async_wrapper_and_nonfinite_output_preserve_failure():
    assert asyncio.run(first.arun({"value": 3})).data == {"value": 4}

    class Output(pydantic.BaseModel):
        value: float

    @toolkit.tool(output_schema=Output)
    def invalid_output(value: int) -> Output:
        return Output(value=float("nan"))

    result = invalid_output.run({"value": 1})
    assert not result.ok and "non-finite" in str(result.errors)
    with pytest.raises(RuntimeError):
        first({"unexpected": 3})


def test_tool_and_skill_declarations_reject_ambiguous_shapes():
    async def asynchronous(value: int):
        return value

    with pytest.raises(TypeError):
        toolkit.tool(asynchronous)
    with pytest.raises(ValueError):
        toolkit.tool(first._function, name="")
    with pytest.raises(TypeError):
        toolkit.tool(first._function, input_schema=dict)
    with pytest.raises(ValueError):
        toolkit.skill(name="")
    with pytest.raises(TypeError):
        toolkit.skill(name="bad", tools=(lambda value: value,))
    with pytest.raises(ValueError):
        toolkit.skill(name="bad", tools=(first, first))
    with pytest.raises(TypeError):
        toolkit.skill(name="bad", instructions=3)
    with pytest.raises(TypeError):
        toolkit.load_skill(3)

    def positional(value: int, context: toolkit.Context):
        return {"value": value}

    def untyped(value: int, *, context):
        return {"value": value}

    for operation in (positional, untyped):
        with pytest.raises(TypeError):
            toolkit.tool(operation)


def test_connection_and_framework_rehydration_preserve_closed_configuration():
    with pytest.raises(ValueError):
        toolkit.runtime(provider="openai-runtime", api_key="")
    for identity in ("", None, 3):
        with pytest.raises(ValueError):
            toolkit.model_artifact(identity)
    selected = toolkit.framework("openai-agents", agent_kwargs={"handoff_description": "fixture"})
    assert selected.inspect()["agent_kwargs"] == {"handoff_description": "str"}
    assert json.loads(selected.model_dump_json())["agent_kwargs"]["handoff_description"] == "fixture"
    restored = type(selected).model_validate({"name": "openai-agents", "agent_kwargs": None})
    assert not restored.agent_kwargs
    with pytest.raises(ValueError):
        type(selected).model_validate({"name": "openai-agents", "agent_kwargs": []})
    with pytest.raises(ValueError):
        toolkit.pause({"approval": True})
