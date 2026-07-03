from __future__ import annotations

from agentic_systems import RunResult, environment_summary, eval_report_summary, run_result_summary, tool, tool_result_summary
from agentic_systems.tools.compat import ToolEvent


def test_run_result_summary_is_small_and_keeps_tool_evidence() -> None:
    result = RunResult(
        text="- resultado: 30\nListo.",
        ok=True,
        validation={"ok": True, "issues": []},
        tool_events=[
            ToolEvent(id="1", name="sumar", input={"a": 10, "b": 20}, output={"data": {"operation": "sumar", "result": 30}}, ok=True)
        ],
        usage={"requests": 2, "total_tokens": 100},
    )

    summary = run_result_summary(result)

    assert summary["ok"] is True
    assert summary["validation_ok"] is True
    assert summary["fields"] == {"resultado": 30}
    assert summary["tools"] == [{"name": "sumar", "ok": True, "input": {"a": 10, "b": 20}, "output": {"operation": "sumar", "result": 30}}]
    assert "runtime" not in summary
    assert "usage" not in summary


def test_tool_result_summary_handles_decorated_tools() -> None:
    @tool
    def cuadrado(n: int) -> dict:
        return {"operation": "cuadrado", "result": n * n}

    summary = tool_result_summary(cuadrado.run({"n": 7}))

    assert summary == {"ok": True, "tool": "cuadrado", "output": {"operation": "cuadrado", "result": 49}}


def test_environment_summary_removes_embedded_run_result_noise() -> None:
    render = {
        "name": "env",
        "episode_id": "e1",
        "step": 1,
        "total_records": 1,
        "done": True,
        "history": [
            {
                "step_index": 0,
                "row": {"task": "math", "a": 10, "b": 20},
                "reward": 1.0,
                "terminated": True,
                "truncated": False,
                "graph_state": {
                    "selected_agent": "math",
                    "agent_text": "30",
                    "agent_result": {
                        "text": "30",
                        "validation": {"ok": True, "issues": []},
                        "tool_events": [{"name": "sumar"}],
                        "raw_responses": [{"huge": "omitted"}],
                    },
                },
            }
        ],
    }

    summary = environment_summary(render)

    assert summary["reward_total"] == 1.0
    assert summary["steps"][0]["agent"] == "math"
    assert summary["steps"][0]["tools"] == ["sumar"]
    assert "graph_state" not in summary["steps"][0]


def test_eval_report_summary_is_output_first() -> None:
    report = {
        "ok": True,
        "passed": 1,
        "failed": 0,
        "pass_rate": 1.0,
        "cases": [
            {
                "name": "case_1",
                "ok": True,
                "validation": {"ok": True},
                "result": {"text": "30", "tool_events": [{"name": "sumar"}]},
            }
        ],
    }

    summary = eval_report_summary(report)

    assert summary == {
        "ok": True,
        "passed": 1,
        "failed": 0,
        "pass_rate": 1.0,
        "cases": [{"name": "case_1", "ok": True, "answer": "30", "tools": ["sumar"], "validation_ok": True}],
    }
