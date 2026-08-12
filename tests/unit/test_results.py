from __future__ import annotations


import pytest

from agentic_systems.results import RunResult, ToolEvent


def test_run_result_lineage_validation_and_normalized_tool_edges():
    failed = ToolEvent(
        id="e1",
        name="calc",
        ok=False,
        input={"a": 1},
        output={"error": "boom"},
        error={"message": "boom"},
    )
    recovered = ToolEvent(
        id="e2", name="calc", ok=True, input={"a": 1}, output={"text": "recovered"}
    )
    scalar = ToolEvent(
        id="e3", name="scalar", ok=True, input={}, output={"data": "raw-value"}
    )
    result = RunResult(
        text="answer",
        data={"result": 42},
        engine="python-runtime",
        model="local",
        mode="eval",
        meta={"input": {"question": "q"}, "framework": "native"},
        tool_events=[failed, recovered, scalar],
        usage={"input_tokens": "12", "output_tokens": "bad"},
    )

    normalized = result.normalized()
    assert normalized["runtime"]["framework"] == "native"
    assert normalized["tools"][2]["output"] == {"data": "raw-value"}
    assert normalized["tools"][1]["summary"] == "recovered"

    trace = result.trace("compact")
    assert trace["recovered_tool_error_count"] == 1
    assert trace["unresolved_failed_tool_count"] == 0
    assert result.compact_trace()["trace_schema_version"]
    full = result.trace("full")
    assert full["compact"]["tool_event_count"] == 3
    with pytest.raises(ValueError):
        result.trace("bad")

    validation = result.validate(
        {
            "must_call": ["calc", "missing"],
            "must_not_call": ["scalar"],
            "expected_output": {"result": 42},
            "expected_tool_outputs": {
                "scalar": {"value": "raw-value"},
                "missing": {"x": 1},
            },
            "tool_expectation": {"rule": "exactly", "tools": ["calc"]},
        }
    )
    codes = {issue.code for issue in validation.issues}
    assert "missing_required_tool" in codes
    assert "forbidden_tool_called" in codes
    assert "expected_tool_output_missing_tool" in codes
    assert "expected_tool_output_mismatch" in codes

    memory = result.lineage(name="calc.run", question="What?", goal="demo")
    assert memory.name == "calc.run"
    assert any(step.kind == "tool" for step in memory.steps)
