from __future__ import annotations

import io
from contextlib import redirect_stdout

import agentic_systems as lab
from agentic_systems.results import RunResult
from agentic_systems.tools.compat import ToolEvent
from tutorials.skills.accountability_otc import multi_agent_system as accountability_mas


def _sample_run_result() -> RunResult:
    return RunResult(
        text="",
        data={
            "summary": "Demo: 1 fila(s).",
            "route": "demo_route",
            "query": {"query_id": "demo_query"},
            "sql": "SELECT 1 AS value",
            "table": {"columns": ["value"], "rows": [{"value": 1}], "n_rows": 1},
        },
        ok=True,
        tool_events=[
            ToolEvent(
                id="tool-1",
                name="demo_tool",
                input={"query_id": "demo_query"},
                output={
                    "data": {
                        "summary": "Demo: 1 fila(s).",
                        "route": "demo_route",
                        "query": {"query_id": "demo_query"},
                        "sql": "SELECT 1 AS value",
                        "table": {"columns": ["value"], "rows": [{"value": 1}], "n_rows": 1},
                    }
                },
                ok=True,
            )
        ],
        usage={"requests": 1},
        engine="python-runtime",
        mode="tool",
        meta={"input": {"query_id": "demo_query"}},
    )


def test_print_human_result_accepts_already_normalized_run_schema():
    normalized = _sample_run_result().normalized()
    stream = io.StringIO()

    with redirect_stdout(stream):
        lab.print_human_result(normalized, title="Demo", expected_tools=lab.expect.exactly("demo_tool"))

    output = stream.getvalue()
    assert "demo_tool (route=demo_route, query_id=demo_query, rows=1)" in output
    assert "SELECT 1 AS value" in output
    assert "value" in output
    assert "Resultado: OK" in output


def test_accountability_tool_output_keeps_normalized_tool_details_and_clean_answer():
    result = _sample_run_result()
    state = {
        "user_prompt": "demo",
        "route": "demo_tool",
        "plan": {"route": "demo_tool"},
        "tool_input": {"query_id": "demo_query"},
    }

    updated = accountability_mas._tool_output(result, state)

    assert updated["final_answer"] == "Demo: 1 fila(s)."
    assert updated["tool_result"]["schema_version"] == "agentic_systems.run.v1"
    assert updated["tool_result"]["blocks"]["sql"] == [{"tool": "demo_tool", "sql": "SELECT 1 AS value"}]
    assert updated["tool_result"]["blocks"]["tables"][0]["rows"] == [{"value": 1}]
