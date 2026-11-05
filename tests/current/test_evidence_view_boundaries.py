"""Evidence views preserve observed order, omission counts and exact boundaries."""
import json
import pytest
from agentic_systems import RunResult
from agentic_systems._results import _Event, _Lineage, _preview, _redact


def test_redaction_marker_is_stable_in_nested_sequences():
    assert _redact({"rows": [{"password": "secret"}]}) == {"rows": [{"password": "[REDACTED]"}]}


def test_preview_default_boundary_is_400_characters():
    assert _preview("x" * 398) == "x" * 398
    assert _preview("x" * 399) == {"preview": '"' + "x" * 399, "omitted": True}


def test_lineage_render_exact_twelve_steps_has_no_omission_notice():
    steps = tuple({"step_id": str(i), "title": "step", "summary": "done"} for i in range(12))
    line = _Lineage("audit", "q", "g", "answer", True, steps, {}, None, (), {})
    assert line.render().splitlines() == ["audit: OK", "answer", *[f"- step: done [{i}]" for i in range(12)]]


def test_lineage_attempt_keeps_result_errors_before_fallback_errors():
    run = RunResult(execution_id="r", meta={"scheduler_execution": {"attempt_history": [
        {"number": 1, "status": "failed", "error": [{"code": "fallback"}],
         "result": {"usage": {"requests": 2}, "errors": [{"code": "observed"}]}}]}})
    attempt = run.lineage().steps[1]
    assert attempt["evidence"] == {"ok": False, "usage": {"requests": 2}, "errors": [{"code": "observed"}]}
    assert attempt["step_id"] == "r:attempt:1"


def test_single_successful_attempt_is_not_a_retry():
    run = RunResult(meta={"scheduler_execution": {"attempt_history": [{"number": 1, "status": "completed"}]}})
    assert len(run.lineage().steps) == 1
    assert "Attempt" not in run.human_results()


@pytest.mark.parametrize("kind", ["action", "model"])
def test_lineage_retains_business_parent_with_children(kind):
    parent = RunResult(execution_id="parent", meta={"kind": kind}, children=(RunResult(execution_id="leaf"),))
    run = RunResult(execution_id="root", children=(parent,))
    assert [s["step_id"] for s in run.lineage().steps] == ["root", "parent", "leaf"]


def test_lineage_bounds_execution_summary_and_answer_independently():
    run = RunResult(text="ñ" * 450)
    line = run.lineage(question="explicit", goal="goal", tags=["tag"], metadata={"owner": "review"})
    assert line.steps[0]["summary"] == "ñ" * 200
    assert line.answer == "ñ" * 400
    assert (line.question, line.goal, line.tags, line.metadata) == ("explicit", "goal", ("tag",), {"owner": "review"})


def test_human_title_and_execution_id_are_bounded():
    run = RunResult(execution_id="e" * 90, meta={"tool_name": "t" * 90})
    assert run.human_results().splitlines()[:2] == ["t" * 80 + ": COMPLETED", "Execution: " + "e" * 80]


def test_human_tool_output_with_extra_metadata_is_not_unwrapped():
    run = RunResult(tool_events=(_Event("e", "quote", output={"data": {"amount": 4}, "source": "observed"}),))
    assert run.human_results().splitlines()[-1] == '- Tool quote: completed -> {"data":{"amount":4},"source":"observed"}'


def test_human_internal_owner_hides_operation_and_decision():
    child = RunResult(meta={"owner_kind": "eval", "kind": "agent", "name": "hidden", "next": "hidden"})
    assert RunResult(children=(child,)).human_results().splitlines()[-1] == "- No business operation recorded."


def test_prompt_includes_fitting_steps_in_original_order_after_failure_priority():
    steps = ({"step_id": "good", "evidence": {"ok": True}}, {"step_id": "bad", "evidence": {"ok": False}})
    line = _Lineage("audit", "q", "g", "answer", False, steps, {}, None, (), {}, execution_id="r")
    payload = json.loads(line.to_prompt_context(max_chars=1000))
    assert payload == {"ok": False, "steps": list(steps), "omitted_steps": 0, "failed_steps": 1, "execution_id": "r", "answer": "answer"}
