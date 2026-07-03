from __future__ import annotations

import io
from contextlib import redirect_stdout

import agentic_systems as lab
from agentic_systems import RunResult


def test_run_result_separates_final_answer_from_runtime_envelope() -> None:
    result = RunResult(
        text="Se generó la conciliación.",
        data={"rows": [{"cuenta": "100", "mes_actual": 10, "extra": "evidence"}]},
        usage={"requests": 1},
        engine="python-direct",
    )

    assert result.final == {"rows": [{"cuenta": "100", "mes_actual": 10, "extra": "evidence"}]}
    normalized = result.normalized()
    assert normalized["answer"]["final"] == result.final
    assert normalized["answer"]["data"] == result.data
    assert normalized["usage"] == {"requests": 1}


def test_output_schema_projects_requested_fields_without_mutating_evidence_data() -> None:
    schema = lab.output_schema(["cuenta", "mes_actual", "diferencia"], many=True)
    tool = lab.Tool(
        name="build_rows",
        strict=False,
        function=lambda rows: {"rows": rows, "evidence": {"source": "demo"}},
    )
    agent = lab.agent(name="reconciliation", engine="python-direct", output=schema, tools=[tool])

    result = agent.run({"tool": "build_rows", "input": {"rows": [{"cuenta": "100", "mes_actual": 10, "diferencia": 2, "debug": "x"}]}})

    assert result.final == {"rows": [{"cuenta": "100", "mes_actual": 10, "diferencia": 2}]}
    assert result.data["evidence"] == {"source": "demo"}
    assert result.data["rows"][0]["debug"] == "x"


def test_human_result_prints_final_answer_first() -> None:
    result = RunResult(text="Texto secundario", final={"answer": "estructurada", "score": 1}, data={"raw": True})
    stream = io.StringIO()

    with redirect_stdout(stream):
        lab.human_result(result, title="Demo final answer")

    output = stream.getvalue()
    assert "Demo final answer" in output
    assert '"answer": "estructurada"' in output
    assert '"score": 1' in output


def test_normalize_output_and_final_answer_accept_common_python_shapes() -> None:
    assert lab.normalize_output([{"a": 1}]) == {"rows": [{"a": 1}]}
    assert lab.normalize_output([1, 2]) == {"items": [1, 2]}
    assert lab.normalize_output("hola") == {"value": "hola"}
    assert lab.final_answer("hola") == {"value": "hola"}
    assert lab.final_answer(text="hola") == {"text": "hola"}
