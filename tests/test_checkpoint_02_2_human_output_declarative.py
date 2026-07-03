import agentic_systems as lab
from agentic_systems import RunResult
from agentic_systems.tools.compat import ToolEvent


def test_compact_human_result_does_not_emit_empty_sql_or_table_blocks(capsys):
    result = RunResult(
        text="Respuesta simple",
        final={"value": 42},
        data={"value": 42},
        engine="python-direct",
        mode="demo",
        meta={"input": {"operation": "answer"}},
    )

    lab.human_result(result, title="Demo sin SQL", pretty=False)
    out = capsys.readouterr().out

    assert "Respuesta simple" not in out  # final dict takes precedence over fallback text
    assert '"value": 42' in out
    assert "SQL ejecutado" not in out
    assert "Preview de datos" not in out
    assert "sin SQL registrado" not in out
    assert "sin filas para mostrar" not in out


def test_compact_human_result_renders_declared_final_sections(capsys):
    result = RunResult(
        text="Consulta demo",
        final={
            "summary": "Consulta lista.",
            "sections": [
                {"kind": "sql", "title": "Consulta ejecutada", "content": "SELECT 1 AS answer"},
                {"kind": "table", "title": "Resultado tabular", "rows": [{"answer": 1}]},
            ],
        },
        data={"evidence": "demo"},
        engine="python-direct",
        mode="demo",
    )

    lab.human_result(result, title="Demo declarativo", pretty=False)
    out = capsys.readouterr().out

    assert "Consulta lista." in out
    assert "SQL ejecutado" in out
    assert "Consulta ejecutada" in out
    assert "SELECT 1 AS answer" in out
    assert "Preview de datos" in out
    assert "Resultado tabular" in out
    assert "answer" in out
    assert "sin SQL registrado" not in out
    assert "sin filas para mostrar" not in out


def test_compact_human_result_still_renders_tool_sql_and_rows_when_present(capsys):
    result = RunResult(
        text="Consulta con tool",
        ok=True,
        engine="bedrock-runtime",
        tool_events=[
            ToolEvent(
                id="tool-1",
                name="free_sql",
                input={"query_id": "demo"},
                output={
                    "data": {
                        "summary": "1 fila.",
                        "sql": "SELECT currency_id FROM table LIMIT 1",
                        "table": {"n_rows": 1, "rows": [{"currency_id": "MXN"}]},
                    }
                },
                ok=True,
            )
        ],
    )

    lab.human_result(result, title="Demo SQL", pretty=False)
    out = capsys.readouterr().out

    assert "SQL ejecutado" in out
    assert "Preview de datos" in out
    assert "SELECT currency_id" in out
    assert "currency_id" in out
    assert "sin SQL registrado" not in out
    assert "sin filas para mostrar" not in out
