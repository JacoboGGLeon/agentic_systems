from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel

import agentic_systems.utils as utils
from agentic_systems.results import RunResult, ToolEvent


class PayloadModel(BaseModel):
    value: int


@dataclass
class PayloadData:
    value: int


def make_result(ok: bool = True) -> RunResult:
    events = [
        ToolEvent(
            id="t1",
            name="sumar",
            ok=True,
            input={"a": 1, "b": 2},
            output={"data": {"operation": "sum", "result": 3, "table": {"rows": [{"x": 1}], "n_rows": 1}, "query": {"query_id": "q1"}, "sql": "select 1", "route": "sqlite"}},
        ),
        ToolEvent(id="t2", name="fallo", ok=False, input={}, output={"error": "boom"}, error={"message": "boom"}),
    ]
    return RunResult(
        text="resultado: 3\ncolor: azul",
        final={"summary": "resultado final", "sections": [{"kind": "sql", "content": "select 1"}, {"kind": "table", "rows": [{"x": 1}]}]},
        data={"answer": "ok", "items": [1, 2, 3]},
        ok=ok,
        engine="python-runtime",
        model="local",
        mode="eval",
        meta={"input": {"question": "q"}, "framework": "native", "runtime_engine": "python-runtime"},
        tool_events=events,
        usage={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
        validation={"ok": ok, "issues": [] if ok else [{"code": "bad", "message": "boom"}]},
    )


def test_utils_agent_output_compare_and_json_helpers():
    result = make_result()
    output = utils.agent_output(result, include_trace=True, max_string_chars=80)
    assert output["answer"] or output["fields"]
    assert output["trace"]["run_ok"] is True
    assert output["tools"][0]["name"] == "sumar"
    mapped = utils.make_agent_output_mapper(include_trace=True)(result, {})
    assert mapped["agent_output"]["kind"] == "agent"
    assert utils.agent_output_mapper(result)["agent_output"]["ok"] is True

    class BadTrace:
        def trace(self, mode):
            raise RuntimeError("bad")

    assert utils._coerce_compare_item(BadTrace())["value"]
    assert utils._coerce_compare_item("scalar") == {"run_ok": False, "value": "scalar"}
    compact = utils._coerce_compare_item(result)
    assert compact["tool_event_count"] == 2
    assert utils._all_equal([]) is None
    assert utils._all_equal([1, 1]) is True
    assert utils._all_equal([1, 2]) is False
    assert utils._lookup_key({"a": {"b": 1}}, "a.b") == 1
    assert utils._lookup_key({"a": {}}, "a.b") is None
    assert utils._compact_run_for_keys("bad", ["ok"], index=2)["ok"] is False
    assert utils._compact_run_for_keys({"run_ok": True}, ["ok", "run_ok"], index=1)["ok"] is True
    row = utils._compact_run_for_compare({"runtime": {"engine": "e"}, "executed": True, "run_requested": False, "sdk_available": True, "graph_mode": "single", "tools": ["a"], "reason": "r", "answer": "a"}, key="answer", include_key=True)
    assert row["answer"] == "a"
    assert utils._compact_run_for_compare("bad", key="answer", include_key=True)["ok"] is False


def test_utils_result_views_summaries_and_masking(monkeypatch):
    result = make_result(ok=False)
    out = utils.run_result_output(result, include_trace=True)
    assert out["trace"]["run_ok"] is False
    view = utils.run_result_view(result, include_tools=True, include_usage=True, max_string_chars=40)
    assert view["status"]["ok"] is False
    assert view["tools"]
    assert view["usage"]["total_tokens"] == 3
    no_tools = utils.run_result_view(result, include_tools=False, include_usage=False)
    assert "tools" not in no_tools and "usage" not in no_tools
    assert utils.tool_result_summary(result)["error"]
    assert utils.run_result_summary(result)["ok"] is False
    assert utils.chain_history_summary([{"name": "a", "output": {"text": "x"}}])[0]["name"] == "a"

    env = SimpleNamespace(summary=lambda: {"ok": True, "steps": []}, history=[{"state": {"x": 1}}])
    assert "steps" in utils.environment_summary(env)
    report = SimpleNamespace(to_dict=lambda: {"ok": False, "cases": [{"name": "c", "ok": False}]})
    assert utils.eval_report_summary(report)["ok"] is False
    assert utils.eval_report_output(report)["cases"][0]["name"] == "c"
    assert utils.maybe_show_trace(result) is None

    masked = utils.mask_sensitive({"OPENAI_API_KEY": "sk-abc123456789", "nested": {"password": "secret"}})
    assert "sk-" in masked["OPENAI_API_KEY"]
    assert masked["nested"]["password"] == "secr..."
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST")
    snap = utils.aws_environment_snapshot()
    assert "AWS_ACCESS_KEY_ID" in snap


def test_utils_parse_summarize_and_json_edges(tmp_path):
    assert len(utils._answer_string("x" * 20, max_string_chars=8)) <= 9
    assert utils._answer_preview("", max_string_chars=5) == {}
    assert utils._user_facing_answer_text("raw", {"summary": "s"}, {}) == "raw"
    assert utils._looks_like_json_object('{"a":1}') is True
    assert utils._looks_like_json_object("not json") is False
    assert len(utils._maybe_bound_string("abcdef", max_string_chars=4)) <= 5
    assert len(utils._maybe_bound_json({"a": "abcdef"}, max_string_chars=4)["a"]) <= 5
    assert utils._result_answer_summary({"x": 1}, {}, max_string_chars=20)["x"] == 1
    assert utils._tool_event_summary({"name": "t", "input": {"x": 1}, "output": {"data": {"result": 1}}}, include_input=True, max_string_chars=20)["input"] == {"x": 1}
    assert utils._usage_summary({"input_tokens": 1, "output_tokens": 2, "total_tokens": 3})["total_tokens"] == 3
    assert len(utils._minimal_json({"long": "x" * 30}, max_string_chars=8)["long"]) <= 9
    assert utils._summarize_json([{"a": 1}, {"b": 2}], max_items=1, max_string_chars=20, max_depth=2)[1]["__truncated__"]["omitted_items"] == 1
    assert utils._summarize_string("x" * 20, max_chars=8)["chars"] == 20
    assert utils._shape_summary({"rows": [1, 2]})["keys"] == ["rows"]
    assert utils._parse_answer_fields("- a: 1\ncolor: azul")["a"] == 1
    assert utils._parse_json_object_fields('{"a": 1}')["a"] == 1
    assert utils._strip_markdown_code_fence("```json\n{\"a\":1}\n```").startswith("{")
    assert utils._loads_json_object('{"a": 1}')["a"] == 1
    assert utils._loads_first_json_object('pre {"a": 1} post')["a"] == 1
    assert utils._normalize_field_key("A B") == "a_b"
    assert utils._coerce_field_value("42") == 42
    assert utils._coerce_field_value("true") is True
    assert utils._discover_repo_root(Path.cwd())




def test_utils_show_and_environment_edge_cases(capsys):
    normalized = make_result().normalized()
    assert utils._coerce_compare_item({"normalized": normalized})["normalized"]["ok"] is True
    assert utils._coerce_compare_item({"compact": {"normalized": normalized}})["normalized"]["ok"] is True
    serialized = make_result().model_dump()
    assert utils._coerce_compare_item(serialized)["framework"] is None
    compact_serialized = utils._compact_from_serialized_run(serialized)
    assert compact_serialized["failed_tool_event_count"] == 1
    compact_norm = utils._compact_from_normalized(normalized, {"trace_schema_version": "x"})
    assert compact_norm["trace_schema_version"] == "x"
    event = utils._normalize_compare_event(make_result().tool_events[0].model_dump())
    assert event["query_id"] == "q1"

    class HumanText:
        def human_text(self):
            return "human explanation"

    utils.show(HumanText(), title="Human", explanations={"a": "b"})
    assert "human explanation" in capsys.readouterr().out

    summary = utils.run_result_summary(make_result(ok=False), include_runtime=True, include_usage=True)
    assert summary["runtime"]["engine"] == "python-runtime"
    assert summary["usage"]["total_tokens"] == 3

    history = [
        "raw",
        {
            "step_index": 1,
            "reward": 2,
            "row": {"id": 1},
            "graph_state": {
                "selected_agent": "solver",
                "plan": {"step_id": "s1", "reason": "porque", "expected_tools": ["sumar"]},
                "agent_output": {"answer": "ok", "fields": {"x": 1}, "tools": [{"name": "sumar"}], "validation": {"ok": True}},
            },
        },
        {"step_index": 2, "graph_state": {"agent_result": {"text": "raw answer", "tool_events": [{"name": "t"}], "validation": {"ok": False}}}},
    ]
    env_summary = utils.environment_summary({"done": True, "history": history})
    assert env_summary["steps"][0]["agent"] == "solver"
    assert env_summary["steps"][1]["tools"] == ["t"]

    report_payload = {"ok": True, "total": 1, "passed": 1, "failed": 0, "pass_rate": 1.0, "cases": [{"name": "case", "ok": True, "validation": {"ok": True}, "result": make_result().model_dump()}]}
    assert utils.eval_report_output(report_payload, include_trace=True)["ok"] is True
    assert utils.eval_report_output(report_payload)["cases"][0]["result"]["ok"] is True

    class Traceable:
        def trace(self, mode):
            return {"mode": mode}

    utils.maybe_show_trace(Traceable(), show_trace=True, title="Trace")
    assert "Trace" in capsys.readouterr().out
    utils.maybe_show_trace({"x": 1}, show_trace=True, title="Raw trace")
    assert "Raw trace" in capsys.readouterr().out

    assert utils._compact_tool_event({"name": "raw", "ok": True, "output": "text"})["output"] == "text"
    assert utils._usage_summary("bad") == {}
    assert utils._usage_summary({"inputTokens": 1, "custom": 9})["custom"] == 9
    assert utils._minimal_json({str(i): i for i in range(8)}, max_string_chars=20)["__more__"] == 2
    assert utils._minimal_json(list(range(8)), max_string_chars=20)[-1]["__more__"] == 2
    assert utils._summarize_json({"a": 1, "b": 2}, max_items=1, max_string_chars=20, max_depth=2)["__truncated__"]["omitted_items"] == 1
    assert utils._parse_answer_fields("- : bad") == {}
    assert utils._parse_json_object_fields("```json\n{\"A B\": 1}\n```")["a_b"] == 1
    assert utils._strip_markdown_code_fence("no fence") == "no fence"
    assert utils._loads_json_object("[1]") is None
    assert utils._loads_first_json_object("{bad} {\"ok\": true}")["ok"] is True
    assert utils._coerce_field_value("") == ""
    assert utils._coerce_field_value("null") is None
    assert utils._coerce_field_value("3.14") == 3.14
    assert utils._agent_data_summary({"steps": [1], "last": {"x": 1}}, "", max_string_chars=20)["kind"] == "tool_plan"
    assert utils._agent_data_summary({}, "text", max_string_chars=20)["kind"] == "text"
    assert utils._agent_data_summary({}, "", max_string_chars=20)["kind"] == "empty"
    assert utils._maybe_bound_string("abc", max_string_chars=None) == "abc"
    assert utils._maybe_bound_json({"a": 1}, max_string_chars=None) == {"a": 1}
    assert utils._result_answer_summary("", {"steps": [1], "last": {"x": 1}}, max_string_chars=20)["step_count"] == 1
