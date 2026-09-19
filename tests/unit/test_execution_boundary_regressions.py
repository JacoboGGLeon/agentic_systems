import asyncio
import pytest
import agentic_systems as ags
from scripts.compact_evaluation_system import Assessment, Decision
from agentic_systems.integrations.adapters.openai_agents import _sdk_tool_failure
from agentic_systems.integrations.adapters.tools import decode_tool_output


def record_assessments(
    fulfillment: Assessment, clarity: Assessment, grounding: Assessment
) -> dict:
    return Decision(
        fulfillment=fulfillment, clarity=clarity, grounding=grounding
    ).model_dump()


def test_nested_schema_survives_provider_and_sdk_builders():
    from agents import function_tool
    from jsonschema import Draft202012Validator
    from agentic_systems.integrations.adapters.tools import canonical_tool_callable
    from agentic_systems.integrations.adapters.strands import _tool_input_json_schema
    from agentic_systems.providers.openai_runtime import _openai_tools

    tool = ags.tool(input=Decision)(record_assessments)
    system = ags.system(runtime=ags.runtime(provider="python-runtime"))
    agent = system.agent(name="review", instructions="Review", tools=[tool])
    sdk = function_tool(canonical_tool_callable(tool))
    schemas = [
        _openai_tools(system._runtime, agent)[0]["function"]["parameters"],
        sdk.params_json_schema,
        _tool_input_json_schema(tool, tool.function),
    ]
    positive = {
        name: {"conclusion": "pass", "evidence_ids": ["e1"], "reason": "Observed"}
        for name in Decision.model_fields
    }
    negative = {name: "free text" for name in Decision.model_fields}
    for schema in schemas:
        validator = Draft202012Validator(schema)
        assert not list(validator.iter_errors(positive))
        assert len(list(validator.iter_errors(negative))) == 3


@pytest.mark.parametrize(
    "provider", ["openai-runtime", "ollama-runtime", "bedrock-runtime"]
)
def test_explicit_runtime_model_wins_over_system_default(provider):
    system = ags.system(runtime=ags.runtime(provider="python-runtime"))
    agent = system.agent(
        name="reviewer",
        instructions="Review",
        runtime=ags.runtime(provider=provider, model="selected-model"),
    )
    assert agent.model == "selected-model"
    override = system.agent(
        name="override",
        instructions="Review",
        runtime=ags.runtime(provider=provider, model="selected-model"),
        model="explicit-model",
    )
    assert override.model == "explicit-model"


def test_inherited_model_is_preserved():
    system = ags.system(model="inherited-model")
    assert system.agent(name="a", instructions="test").model == "inherited-model"


def test_real_sdk_invalid_arguments_have_typed_failure():
    from agents import function_tool
    from agents.tool_context import ToolContext

    def count(value: int) -> int:
        return value + 1

    tool = function_tool(count, failure_error_function=_sdk_tool_failure)
    context = ToolContext(
        context=None, tool_name="count", tool_call_id="call-1", tool_arguments="{}"
    )
    output = asyncio.run(tool.on_invoke_tool(context, '{"value":"not-an-integer"}'))
    data, ok, error = decode_tool_output(output)
    assert not ok
    assert data is None
    assert error["code"] == "ModelBehaviorError"
    positive = asyncio.run(tool.on_invoke_tool(context, '{"value":2}'))
    assert positive == 3


def test_error_like_success_text_is_not_reclassified():
    text = "An error occurred while running the tool."
    assert decode_tool_output(text) == (text, True, None)


def test_strands_compaction_preserves_new_identical_messages():
    from types import SimpleNamespace
    from agentic_systems.integrations.adapters.strands import (
        _message_cursor,
        _invocation_messages,
    )

    old = {"role": "assistant", "content": [{"text": "same"}]}
    retained = {"role": "user", "content": [{"text": "prior"}]}
    agent = SimpleNamespace(messages=[old, retained])
    cursor = _message_cursor(agent)
    new = {"role": "assistant", "content": [{"text": "same"}]}
    agent.messages = [retained, new]
    assert _invocation_messages(agent, cursor) == [new]


def test_sdk_budget_prevents_extra_side_effects_and_is_isolated():
    from agents import Agent, function_tool
    from agents.tool_context import ToolContext
    from agentic_systems.integrations.adapters.openai_agents import (
        _configure_tool_budget,
        _execution_agent,
    )

    observed = []

    def record(value: int) -> int:
        observed.append(value)
        return value

    prepared = Agent(name="test", tools=[function_tool(record)])
    context = ToolContext(
        context=None, tool_name="record", tool_call_id="call", tool_arguments="{}"
    )
    for _ in range(2):
        execution = _execution_agent(prepared)
        _configure_tool_budget(execution, ags.RunPolicy(max_tool_calls=1))
        tool = execution.tools[0]
        assert asyncio.run(tool.on_invoke_tool(context, '{"value":1}')) == 1
        rejected = asyncio.run(tool.on_invoke_tool(context, '{"value":2}'))
        assert decode_tool_output(rejected)[1] is False
    assert observed == [1, 1]
    assert prepared.tools[0] is not tool
