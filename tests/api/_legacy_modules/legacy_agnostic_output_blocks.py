import agentic_systems as lab
from agentic_systems import RunResult
from agentic_systems.tools.compat import ToolEvent


def _sample_result() -> RunResult:
    return RunResult(
        text="hallazgo_principal: ok",
        ok=True,
        engine="bedrock-runtime",
        mode="eval",
        usage={"requests": 1, "input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        meta={"input": "Compara exposición OTC por moneda contra MTM por clase de activo.", "framework": "bedrock"},
        tool_events=[
            ToolEvent(
                id="tool-1",
                name="free_sql",
                input={"query_id": "otc_exposure_by_currency"},
                output={
                    "data": {
                        "summary": "Exposición por moneda: 1 fila(s).",
                        "route": "catalog_sql",
                        "query": {"query_id": "otc_exposure_by_currency"},
                        "sql": "SELECT currency_id FROM table LIMIT 1",
                        "table": {"n_rows": 1, "rows": [{"currency_id": "MXN"}]},
                    }
                },
                ok=True,
            )
        ],
    )


def test_normalized_schema_has_human_blocks():
    normalized = _sample_result().normalized()

    assert normalized["blocks"]["user_input"]
    assert normalized["blocks"]["agent_answer"]["text"] == "hallazgo_principal: ok"
    assert normalized["blocks"]["tool_actions"][0]["name"] == "free_sql"
    assert normalized["blocks"]["tool_actions"][0]["query_id"] == "otc_exposure_by_currency"
    assert normalized["blocks"]["sql"][0]["tool"] == "free_sql"


def test_compare_accepts_runresult_and_serialized_langgraph_result():
    result = _sample_result()
    serialized = result.to_dict()
    serialized["normalized"] = result.normalized()

    compared = lab.compare([result, serialized], keys=["run_ok", "engine", "framework", "mode", "tool_event_count", "usage"])

    assert compared["ok"] is True
    assert compared["runs"][0]["tool_event_count"] == 1
    assert compared["runs"][1]["framework"] == "bedrock"


def test_human_output_prints_stable_blocks(capsys):
    lab.human_result(_sample_result(), title="Demo", expected_tools=["free_sql"])
    out = capsys.readouterr().out

    assert "1) Entrada del usuario" in out
    assert "2) Runtime y usage" in out
    assert "3) Respuesta del agente/sistema" in out
    assert "Respuesta:" in out
    assert "4) Acciones ejecutadas" in out
    assert "5) SQL ejecutado" in out
    assert "6) Preview de datos" in out
    assert "7) Validación" in out
    assert "Evidencia normalizada desde tools" not in out
    assert "Tools esperadas: free_sql" in out
