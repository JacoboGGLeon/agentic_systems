import pytest

from agentic_systems import (
    RunResult,
)
from agentic_systems.results import _contains_subset
from agentic_systems.tools import ToolEvent


def test_result_trace_validate_and_subset_paths():
    assert _contains_subset({"a": {"b": 2}}, {"a": {"b": 2}}) is True
    assert _contains_subset("not a dict", {"a": 1}) is False
    assert _contains_subset({"a": 1}, {"b": 1}) is False
    assert _contains_subset("hello world", "world") is True
    assert _contains_subset([{"x": 1}, {"x": 2}], [{"x": 2}]) is True
    assert _contains_subset({"x": 1}, [{"x": 1}]) is False
    assert _contains_subset([1], [2]) is False

    fail = ToolEvent(id="f1", name="lookup", ok=False, error={"message": "fail"})
    ok = ToolEvent(
        id="s1", name="lookup", ok=True, output={"data": {"id": 1, "name": "ok"}}
    )
    forbidden = ToolEvent(id="x1", name="delete", ok=True, output={"data": {"id": 9}})
    result = RunResult(
        text="done",
        data={"status": "done"},
        tool_events=[fail, ok, forbidden],
        raw_responses=[
            {"usage": {"inputTokens": 1, "output_tokens": 2, "totalTokens": 3}}
        ],
    )

    assert result.to_dict()["text"] == "done"
    assert result.compact_trace()["recovered_tool_error_count"] == 1
    assert result.trace("full")["compact"]["tool_event_count"] == 3
    with pytest.raises(ValueError, match="compact"):
        result.trace("bad")

    validation = result.validate(
        {
            "must_call": ["lookup"],
            "must_not_call": ["delete"],
            "expected_output": {"status": "missing"},
            "expected_tool_outputs": {
                "missing_tool": {"id": 1},
                "lookup": {"name": "missing"},
            },
        }
    )
    codes = {issue.code for issue in validation.issues}
    assert {
        "forbidden_tool_called",
        "expected_output_mismatch",
        "expected_tool_output_missing_tool",
        "expected_tool_output_mismatch",
    } <= codes

    unresolved = RunResult(
        text="bad",
        tool_events=[ToolEvent(id="u1", name="u", ok=False, error={"e": "x"})],
    )
    assert unresolved.trace()["unresolved_failed_tool_count"] == 1
    assert "unresolved_tool_failure" in {
        issue.code for issue in unresolved.validate().issues
    }


def test_run_result_from_bedrock_runtime_dict_and_usage_aliases():
    raw = {
        "final_text": "ok",
        "messages": [{"role": "assistant"}],
        "tool_calls": [
            {
                "tool_use_id": "1",
                "tool_name": "t",
                "tool_input": {},
                "tool_output": {"data": {"x": 1}},
                "ok": True,
            }
        ],
        "raw_responses": [
            {"usage": {"input_tokens": 2, "outputTokens": 3, "totalTokens": 5}}
        ],
    }
    result = RunResult.from_bedrock_runtime(raw, engine="bedrock", model="m")
    assert result.usage == {
        "input_tokens": 2,
        "output_tokens": 3,
        "total_tokens": 5,
        "requests": 1,
    }


def test_tool_event_non_dict_error_data_path():
    event = ToolEvent.from_runtime_record(
        {
            "tool_use_id": "e1",
            "tool_name": "broken",
            "tool_input": {},
            "tool_output": {"data": "plain error"},
            "ok": False,
        }
    )
    assert event.error == {"message": "plain error"}
