from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from pydantic import BaseModel

import agentic_systems.human_output as ho
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
            output={
                "data": {
                    "operation": "sum",
                    "result": 3,
                    "table": {"rows": [{"x": 1}], "n_rows": 1},
                    "query": {"query_id": "q1"},
                    "sql": "select 1",
                    "route": "sqlite",
                }
            },
        ),
        ToolEvent(
            id="t2",
            name="fallo",
            ok=False,
            input={},
            output={"error": "boom"},
            error={"message": "boom"},
        ),
    ]
    return RunResult(
        text="resultado: 3\ncolor: azul",
        final={
            "summary": "resultado final",
            "sections": [
                {"kind": "sql", "content": "select 1"},
                {"kind": "table", "rows": [{"x": 1}]},
            ],
        },
        data={"answer": "ok", "items": [1, 2, 3]},
        ok=ok,
        engine="python-runtime",
        model="local",
        mode="eval",
        meta={
            "input": {"question": "q"},
            "framework": "native",
            "runtime_engine": "python-runtime",
        },
        tool_events=events,
        usage={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
        validation={
            "ok": ok,
            "issues": [] if ok else [{"code": "bad", "message": "boom"}],
        },
    )


def test_human_output_helpers_and_plain_render(capsys, monkeypatch):
    result = make_result()
    normalized = result.normalized()
    assert ho._jsonable(PayloadModel(value=1)) == {"value": 1}
    assert ho._jsonable(PayloadData(2)).value == 2
    assert ho._as_dict(SimpleNamespace(model_dump=lambda mode="json": {"a": 1})) == {
        "a": 1
    }
    assert len(ho._compact("x" * 20, max_chars=8)) <= 9
    assert ho._one_line("a\nb") == "a b"
    assert ho._event_payload({"output": {"data": {"x": 1}}}) == {"x": 1}
    assert ho._payload_brief({"summary": "s"}) == '{"summary": "s"}'
    assert ho._is_normalized_run_schema(normalized) is True
    assert ho._normalized(result)["ok"] is True
    assert ho._normalized({"x": 1})["answer"]["data"] == {}
    assert ho._normalize_event(result.tool_events[0].model_dump())["name"] == "sumar"
    assert "fila" in ho._format_rows([{"a": 1}, {"a": 2}], max_rows=1)
    assert ho._format_usage({"total_tokens": 3}) == "total_tokens=3"
    assert list(ho._iter_final_sections(normalized["answer"]["final"])) == []
    assert ho._sql_blocks(normalized, normalized["tools"])
    assert ho._table_blocks(normalized, normalized["tools"])
    assert (
        ho._should_print_validation([], None, {"ok": False, "issues": [{"code": "x"}]})
        is True
    )
    assert ho._tool_label({"name": "t", "route": "r"}, 1) == "t (route=r)"
    assert ho._runtime_framework(normalized) == "native"
    assert ho._eval_cases_from_normalized({"cases": [1]}) == []
    assert ho._environment_history_from_normalized({"history": [1]}) == []
    assert ho._case_result_preview({"name": "c", "ok": True})
    assert (
        ho._validation_summary(
            [], None, {"ok": False, "issues": [{"code": "x", "message": "bad"}]}
        )["ok"]
        is False
    )
    assert ho._format_expectation({"exactly": ["a"]})

    monkeypatch.setattr(ho, "_rich_available", lambda: False)
    ho.human_result(result, title="Demo", show_lineage=True)
    plain = capsys.readouterr().out
    assert "Demo" in plain
    assert "Runtime" in plain
    ho.human_result([result, result], title="Batch")
    assert "Batch" in capsys.readouterr().out
    rendered = ho.human_result(result, title="One")
    assert rendered is None
    assert "One" in capsys.readouterr().out
    assert ho.human_result([result]) is None
    assert "Ejecuciones" in capsys.readouterr().out


def test_human_output_render_modes_and_domain_blocks(capsys, monkeypatch):
    monkeypatch.setattr(ho, "_rich_available", lambda: False)

    normalized_eval = {
        "schema_version": ho.RUN_SCHEMA_FALLBACK,
        "ok": True,
        "runtime": {
            "engine": "python-runtime",
            "framework": "agentic-eval",
            "mode": "eval",
        },
        "input": {"suite": "demo"},
        "answer": {
            "text": "",
            "final": {},
            "data": {
                "cases": [
                    {
                        "name": "case_a",
                        "ok": True,
                        "input": {"x": 1},
                        "result": {"final": {"result": 1}},
                    }
                ]
            },
        },
        "tools": [],
        "usage": {},
        "validation": {"ok": True, "passed": 1, "failed": 0},
    }
    ho.human_result(normalized_eval, title="Eval demo")
    out = capsys.readouterr().out
    assert "Casos evaluados" in out
    assert "case_a" in out

    normalized_env = {
        "schema_version": ho.RUN_SCHEMA_FALLBACK,
        "ok": True,
        "runtime": {
            "engine": "python-runtime",
            "framework": "agentic-environment",
            "mode": "eval",
        },
        "input": {"episode": "demo"},
        "answer": {
            "text": "",
            "final": {},
            "data": {
                "history": [
                    {
                        "step_index": 1,
                        "reward": 1,
                        "row": {"x": 2},
                        "graph_state": {"selected_agent": "judge"},
                    }
                ]
            },
        },
        "tools": [],
        "usage": {},
        "validation": {"ok": True, "passed_steps": 1, "failed_steps": 0},
    }
    ho.human_result(normalized_env, title="Env demo")
    out = capsys.readouterr().out
    assert "Pasos del episodio" in out
    assert "route=judge" in out

    ho.human_result(make_result(), title="JSON demo", render_mode="debug")
    out = capsys.readouterr().out
    assert "schema_version" in out


def test_human_output_helpers_handle_empty_and_nested_values(capsys):
    assert ho._jsonable((PayloadModel(value=3), {"x": PayloadModel(value=4)})) == [
        {"value": 3},
        {"x": {"value": 4}},
    ]
    assert ho._event_payload({"output": "raw"}) == {"value": "raw"}
    assert (
        ho._payload_brief({"operation": "sum", "result": 3})
        == '{"operation": "sum", "result": 3}'
    )
    assert (
        ho._is_normalized_run_schema({"schema_version": ho.RUN_SCHEMA_FALLBACK}) is True
    )
    assert (
        ho._normalized({"normalized": {"runtime": {}, "answer": {}, "tools": []}})[
            "tools"
        ]
        == []
    )
    assert (
        ho._normalized(
            {"compact": {"normalized": {"runtime": {}, "answer": {}, "tools": []}}}
        )["tools"]
        == []
    )
    assert (
        ho._fallback_normalized({"ok": True, "text": "hola", "meta": {"input": "q"}})[
            "answer"
        ]["text"]
        == "hola"
    )
    assert ho._format_rows([]) == ""
    ho._print_payload({"summary": "s"})
    ho._print_payload({"error": "e"})
    ho._print_payload(
        {
            "operation": "sum",
            "result": 1,
            "sql": "select 1",
            "table": {"rows": [{"x": 1}]},
        },
        include_sql=True,
        include_table=True,
    )
    ho._print_answer({"final": {"text": "hello"}, "text": "hello", "data": {}})
    ho._print_answer({"final": {"error": "bad"}, "text": "", "data": {}})
    ho._print_answer({"final": {}, "text": "", "data": {"summary": "data summary"}})
    ho._print_answer({"final": {}, "text": "", "data": {"x": 1}})
    ho._print_answer({"final": {}, "text": "", "data": {}})
    out = capsys.readouterr().out
    assert "Resultado" in out
    assert "sin respuesta" in out

    answer = {
        "final": {
            "rows": [{"a": 1}],
            "table_title": "Final table",
            "sections": [
                {"kind": "sql", "content": "select 1"},
                {"kind": "table", "rows": [{"b": 2}]},
            ],
        }
    }
    assert ho._sql_blocks(answer, [])[0]["content"] == "select 1"
    assert len(ho._table_blocks(answer, [])) == 2
    ho._print_sql([{"name": "sql_tool", "ok": True, "sql": "select 1"}])
    ho._print_tables([{"name": "table_tool", "ok": True, "rows": [{"a": 1}]}])
    ho._print_actions([])
    ho._print_actions([{"name": "bad", "ok": False, "error": "boom"}])
    ho._print_eval_cases([])
    ho._print_eval_cases(
        [
            {
                "name": f"c{i}",
                "ok": bool(i % 2),
                "input": i,
                "result": {"data": {"result": i}},
            }
            for i in range(12)
        ],
        max_cases=2,
    )
    ho._print_environment_steps([])
    ho._print_environment_steps(
        [
            {
                "step_index": i,
                "reward": i,
                "row": {"i": i},
                "graph_state": {"route": "r"},
            }
            for i in range(12)
        ],
        max_steps=2,
    )
    ho._print_validation(
        [{"name": "a", "ok": False}], {"all_of": ["a", "b"]}, {"ok": False}
    )
    out = capsys.readouterr().out
    assert "Tools ejecutadas" in out
    assert "caso(s)" in out
    assert "paso(s)" in out
    assert "REVISAR" in out


class MemoryLike:
    def human_text(self):
        return "memory text"


def test_human_output_lineage_and_rich_paths(capsys, monkeypatch):
    result = make_result()
    normalized = result.normalized()
    assert ho._build_lineage(result, normalized, lineage="manual") == "manual"
    ho._print_lineage(result, normalized, lineage=MemoryLike())
    assert "memory text" in capsys.readouterr().out
    ho._print_lineage(result, normalized, lineage={"x": 1})
    assert "x" in capsys.readouterr().out

    monkeypatch.setattr(ho, "_rich_available", lambda: True)
    ho.human_result(result, title="Pretty demo", pretty=True, show_lineage=False)
    assert "Pretty demo" in capsys.readouterr().out
