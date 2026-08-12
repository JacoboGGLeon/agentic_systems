from __future__ import annotations

from agentic_systems import RunResult, run_result_view
from agentic_systems.tools import ToolEvent


def test_run_result_view_extracts_bullet_fields_without_case_hardcoding() -> None:
    result = RunResult(
        text="- alpha: 10\n- beta value: hello\n- ok: true",
        data={},
        ok=True,
        validation={"ok": True, "issues": []},
        engine="bedrock-runtime",
        mode="eval",
    )

    view = run_result_view(result)

    assert view["status"] == {"ok": True, "validation_ok": True, "issue_count": 0}
    assert view["fields"] == {"alpha": 10, "beta_value": "hello", "ok": True}
    assert view["runtime"]["engine"] == "bedrock-runtime"


def test_run_result_view_summarizes_long_tool_outputs_generically() -> None:
    long_text = "# Title\n" + "line\n" * 100
    result = RunResult(
        text="done",
        ok=True,
        validation={"ok": True, "issues": []},
        tool_events=[
            ToolEvent(
                id="tool-1",
                name="read_anything",
                input={"path": "/tmp/example.md"},
                output={"data": {"content": long_text, "result": "ok"}},
                ok=True,
            )
        ],
        engine="bedrock-runtime",
        mode="eval",
    )

    view = run_result_view(result, max_string_chars=40)

    assert view["tools"][0]["tool"] == "read_anything"
    assert view["tools"][0]["output"]["result"] == "ok"
    content = view["tools"][0]["output"]["content"]
    assert content["type"] == "string"
    assert content["chars"] == len(long_text)
    assert content["lines"] == long_text.count("\n") + 1
    assert content["preview"].endswith("…")


def test_run_result_view_can_hide_tools_and_usage() -> None:
    result = RunResult(text="ok", usage={"requests": 1}, validation={"ok": True, "issues": []})

    view = run_result_view(result, include_tools=False, include_usage=False)

    assert "tools" not in view
    assert "usage" not in view


def test_run_result_view_extracts_json_answer_fields_without_case_hardcoding() -> None:
    result = RunResult(
        text='{"resultado_numérico": 42, "terminación": 2, "color": "azul", "explicación breve": "ok"}',
        data={},
        ok=True,
        validation={"ok": True, "issues": []},
        engine="bedrock-runtime",
        mode="eval",
    )

    view = run_result_view(result)

    assert view["fields"] == {
        "resultado_numérico": 42,
        "terminación": 2,
        "color": "azul",
        "explicación_breve": "ok",
    }


def test_run_result_view_extracts_fenced_json_answer_fields() -> None:
    result = RunResult(
        text='```json\n{"alpha value": 10, "ok": true}\n```',
        ok=True,
        validation={"ok": True, "issues": []},
        engine="bedrock-runtime",
        mode="eval",
    )

    view = run_result_view(result)

    assert view["fields"] == {"alpha_value": 10, "ok": True}
