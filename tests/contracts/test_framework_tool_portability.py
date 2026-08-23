from __future__ import annotations

import json
from types import SimpleNamespace

import agentic_systems as toolkit

from agentic_systems.integrations.adapters import openai_agents as oa
from agentic_systems.integrations.adapters import strands as sa
from agentic_systems.integrations.adapters.tools import (
    canonical_tool_callable,
    decode_tool_output,
    tool_name_aliases,
)


def _failing_tool() -> toolkit.Tool:
    @toolkit.tool(name="quality.raise.error")
    def fail(value: int) -> dict[str, int]:
        raise RuntimeError(f"failure-{value}")

    return fail


def test_tool_aliases_are_sdk_safe_reversible_and_input_aware() -> None:
    aliases = tool_name_aliases(
        [
            SimpleNamespace(name="quality.echo"),
            SimpleNamespace(name="quality/echo"),
            SimpleNamespace(name="already_safe"),
        ]
    )
    dotted = aliases.native("quality.echo")
    slashed = aliases.native("quality/echo")
    assert dotted != slashed
    assert "." not in dotted
    assert "/" not in slashed
    assert aliases.canonical(dotted) == "quality.echo"
    assert aliases.canonical(slashed) == "quality/echo"
    assert aliases.native("already_safe") == "already_safe"
    assert aliases.map_input(
        {"tool": "quality.echo", "input": {"name": "quality.echo"}}
    ) == {"tool": dotted, "input": {"name": "quality.echo"}}


def test_canonical_tool_callable_preserves_success_and_marks_failure() -> None:
    @toolkit.tool(name="quality.echo")
    def echo(value: int) -> dict[str, int]:
        return {"value": value}

    assert canonical_tool_callable(echo)(value=3) == {"value": 3}

    marked = canonical_tool_callable(_failing_tool())(value=4)
    data, ok, error = decode_tool_output(json.dumps(marked))
    assert ok is False
    assert data["error_type"] == "RuntimeError"
    assert error is not None


def test_openai_agents_recovers_canonical_failed_tool_event() -> None:
    tool = _failing_tool()
    aliases = tool_name_aliases([tool])
    native_name = aliases.native(tool.name)
    marked = canonical_tool_callable(tool)(value=7)
    call = type(
        "ToolCallItem",
        (),
        {
            "raw_item": {
                "call_id": "call-1",
                "name": native_name,
                "arguments": '{"value": 7}',
            }
        },
    )()
    output = type(
        "ToolCallOutputItem",
        (),
        {"raw_item": {"call_id": "call-1", "output": json.dumps(marked)}},
    )()
    native = SimpleNamespace(
        last_agent=None,
        final_output="tool failed",
        raw_responses=[],
        new_items=[call, output],
        context_wrapper=None,
        to_input_list=lambda: [],
    )
    agent = SimpleNamespace(engine="python-runtime", model="scripted")
    result = oa._normalize_result(
        agent, native, {"tool": tool.name}, "default", aliases
    )
    assert result.ok is False
    assert result.tool_events[0].name == tool.name
    assert result.tool_events[0].ok is False
    assert result.errors
    assert result.check_invariants().ok is True


def test_strands_projects_native_alias_back_to_canonical_name() -> None:
    aliases = tool_name_aliases([SimpleNamespace(name="quality.echo")])
    native_name = aliases.native("quality.echo")
    messages = [
        {
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "call-1",
                        "name": native_name,
                        "input": {"value": 1},
                    }
                },
                {
                    "toolResult": {
                        "toolUseId": "call-1",
                        "status": "success",
                        "content": [{"json": {"value": 1}}],
                    }
                },
            ]
        }
    ]
    events = sa._tool_events(messages, aliases)
    assert events[0].name == "quality.echo"
    assert events[0].ok is True
