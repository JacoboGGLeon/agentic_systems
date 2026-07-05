from __future__ import annotations

from ._load_legacy import export_legacy_tests

export_legacy_tests(
    globals(),
    'checkpoint_02_2_human_output_declarative',
    'checkpoint_09_tutorial_output_helpers',
    'checkpoint_09b_output_views',
    'checkpoint_10c_tutorial_hotfixes',
    'checkpoint_10d_minimal_output_summaries',
    'checkpoint_10g_usage_timing_summaries',
    'human_output_utils_phase6b_coverage',
    'notebook_syntax',
    'notebook_top_level_helpers',
)


def _normalized_payload(*, framework="agentic-systems", tools=None, answer=None, data=None, usage=None, validation=None):
    answer_payload = answer or {
        "text": "respuesta textual",
        "final": {"resultado": 42},
        "data": data or {"resultado": 42},
    }
    return {
        "schema_version": "agentic_systems.run.v1",
        "ok": True,
        "runtime": {
            "engine": "python-runtime",
            "runtime_engine": "python-runtime",
            "framework": framework,
            "model": "python-runtime",
            "mode": "eval",
        },
        "input": {"question": "demo"},
        "answer": answer_payload,
        "tools": tools or [],
        "usage": usage or {"requests": 1, "input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
        "validation": validation,
        "errors": [],
        "final": answer_payload.get("final", {}),
    }


def test_human_result_debug_and_plain_text_fallbacks(capsys):
    import agentic_systems as lab

    lab.human_result(_normalized_payload(answer={"text": "solo texto", "final": {}, "data": {}}), title="Debug", render_mode="debug")
    out = capsys.readouterr().out
    assert "schema_version" in out

    lab.human_result(_normalized_payload(answer={"text": "solo texto", "final": {}, "data": {}}), title="Plain")
    out = capsys.readouterr().out
    assert "solo texto" in out


def test_human_result_uses_native_framework_label_when_missing(capsys):
    import agentic_systems as lab

    payload = _normalized_payload(framework=None)
    lab.human_result(payload, title="Native framework")
    out = capsys.readouterr().out
    assert "Framework: agentic-systems" in out
    assert "Framework: n/a" not in out


def test_human_result_plain_sql_table_validation_and_lineage(capsys):
    import agentic_systems as lab

    payload = _normalized_payload(
        tools=[
            {
                "name": "sql_tool",
                "ok": False,
                "input": {"q": "x"},
                "summary": "fallo controlado",
                "sql": "select 1",
                "rows": [{"a": 1}, {"a": 2}],
                "row_count": 2,
                "route": "demo",
                "query_id": "q1",
                "error": "boom",
            }
        ],
        answer={
            "text": "",
            "final": {
                "sections": [
                    "bad-section",
                    {"kind": "sql", "title": "SQL final", "content": "select 2"},
                    {"kind": "table", "title": "Tabla final", "rows": [{"b": 3}]},
                ],
                "rows": [{"c": 4}],
                "table_title": "Tabla directa",
            },
            "data": {},
        },
        validation={"ok": False, "issues": [{"code": "x", "message": "bad", "tools": ["sql_tool"]}]},
    )

    lab.human_result(
        payload,
        title="Plain blocks",
        expected_tools={"any_of": ["sql_tool", "other"], "min_count": 1},
        render_mode="lineage",
    )
    out = capsys.readouterr().out
    assert "SQL final" in out
    assert "Tabla final" in out
    assert "Preview de datos" in out
    assert "any_of=[sql_tool, other]" in out


def test_human_result_rich_eval_environment_and_empty_actions(capsys):
    import agentic_systems as lab

    eval_payload = _normalized_payload(
        framework="agentic-eval",
        data={"cases": [{"name": "c1", "ok": True, "input": {"x": 1}, "result": {"data": "raw", "final": "raw"}}]},
        answer={"text": "", "final": {"summary": "eval ok"}, "data": {"cases": [{"name": "c1", "ok": True, "input": {"x": 1}, "result": {"data": "raw", "final": "raw"}}]}},
    )
    lab.human_result(eval_payload, title="Eval rich", pretty=True)

    env_payload = _normalized_payload(
        framework="agentic-environment",
        answer={
            "text": "",
            "final": {"error": "env done"},
            "data": {"history": [{"step_index": 1, "reward": 1.0, "row": {"id": 1}, "graph_state": {"selected_agent": "judge"}}]},
        },
    )
    lab.human_result(env_payload, title="Env rich", pretty=True)

    empty_payload = _normalized_payload(answer={"text": "", "final": {}, "data": {}})
    lab.human_result(empty_payload, title="Empty rich", pretty=True, show_lineage=True, lineage={"lineage": "dict"})
    out = capsys.readouterr().out
    assert "Eval rich" in out
    assert "Env rich" in out
    assert "Empty rich" in out


def test_human_output_defensive_helpers(monkeypatch, capsys):
    import builtins
    import agentic_systems.human_output as human_output

    assert human_output._runtime_framework({}) == ""

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "rich":
            raise RuntimeError("rich unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert human_output._rich_available() is False

    monkeypatch.setattr(human_output, "_build_lineage", lambda *args, **kwargs: None)
    human_output._print_lineage(object(), _normalized_payload())
    assert "Lineage Memory no disponible" in capsys.readouterr().out


def test_human_output_remaining_defensive_branches(monkeypatch, capsys):
    import json
    import agentic_systems.human_output as human_output

    def boom(*args, **kwargs):
        raise TypeError("cannot json")

    monkeypatch.setattr(json, "dumps", boom)
    assert human_output._compact({"x": object()}).startswith("{")
    assert human_output._payload_brief({}) == ""

    import agentic_systems.lineage as lineage_module

    monkeypatch.setattr(lineage_module.LineageMemory, "from_run_result", classmethod(lambda cls, *args, **kwargs: (_ for _ in ()).throw(RuntimeError("lineage fail"))))
    assert human_output._build_lineage(object(), _normalized_payload()) is None


def test_human_result_rich_answer_variants_and_validation_issues(capsys):
    import agentic_systems as lab

    lab.human_result(
        _normalized_payload(answer={"text": "same", "final": {"text": "same"}, "data": {}}),
        title="Rich final text",
        pretty=True,
    )
    lab.human_result(
        _normalized_payload(answer={"text": "plain answer", "final": {}, "data": {}}),
        title="Rich answer text",
        pretty=True,
    )
    lab.human_result(
        _normalized_payload(answer={"text": "", "final": {}, "data": {"summary": "data summary"}}),
        title="Rich answer data",
        pretty=True,
    )
    lab.human_result(
        _normalized_payload(tools=[{"name": "actual", "ok": True, "summary": "ok"}]),
        title="Rich validation issues",
        pretty=True,
        expected_tools={"exactly": ["expected"]},
    )
    out = capsys.readouterr().out
    assert "Rich final text" in out
    assert "Rich answer text" in out
    assert "Rich answer data" in out
    assert "Issues" in out


def test_human_result_rich_eval_environment_overflow_and_empty(monkeypatch, capsys):
    import agentic_systems as lab
    import agentic_systems.human_output as human_output

    many_cases = [{"name": f"c{i}", "ok": True, "input": {"i": i}, "result": {"data": {"result": i}}} for i in range(12)]
    lab.human_result(
        _normalized_payload(
            framework="agentic-eval",
            answer={"text": "", "final": {"summary": "many"}, "data": {"cases": many_cases}},
        ),
        title="Rich eval many",
        pretty=True,
    )
    lab.human_result(
        _normalized_payload(framework="agentic-eval", answer={"text": "", "final": {"summary": "none"}, "data": {"cases": []}}),
        title="Rich eval empty",
        pretty=True,
    )

    many_steps = [{"step_index": i, "reward": i, "row": {"i": i}, "graph_state": {"route": "r"}} for i in range(12)]
    lab.human_result(
        _normalized_payload(
            framework="agentic-environment",
            answer={"text": "", "final": {"summary": "many"}, "data": {"history": many_steps}},
        ),
        title="Rich env many",
        pretty=True,
    )
    lab.human_result(
        _normalized_payload(framework="agentic-environment", answer={"text": "", "final": {"summary": "none"}, "data": {"history": []}}),
        title="Rich env empty",
        pretty=True,
    )

    monkeypatch.setattr(human_output, "_table_blocks", lambda answer, tools: [{"title": "Empty table", "rows": []}])
    lab.human_result(_normalized_payload(), title="Rich empty table", pretty=True)
    out = capsys.readouterr().out
    assert "Rich eval many" in out
    assert "Rich env many" in out
    assert "Rich empty table" in out


def test_human_result_rejects_invalid_render_mode():
    import pytest
    import agentic_systems as lab

    with pytest.raises(ValueError, match="render_mode"):
        lab.human_result(_normalized_payload(), render_mode="invalid")
