from __future__ import annotations


def test_notebook_helpers_are_public_top_level_imports():
    from agentic_systems import (
        compose_result,
        configure_notebook_environment,
        eval_report_output,
        maybe_show_trace,
        run_result_output,
        show_json,
    )

    assert callable(compose_result)
    assert callable(configure_notebook_environment)
    assert callable(show_json)
    assert callable(run_result_output)
    assert callable(eval_report_output)
    assert callable(maybe_show_trace)


def test_compose_result_preserves_runtime_metadata_and_usage():
    import agentic_systems as lab
    from agentic_systems.tools.compat import ToolEvent

    direct = lab.RunResult(
        text="direct",
        data={"value": 1},
        engine="python-runtime",
        model="python-runtime",
        mode="eval",
        tool_events=[ToolEvent(id="tool-1", name="sumar", input={}, output={"data": {"result": 1}}, ok=True)],
    )
    lm = lab.RunResult(
        text="lm",
        data={"review": "ok"},
        engine="openai-runtime",
        model="gpt-test",
        mode="eval",
        usage={"requests": 1, "input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
    )

    result = lab.compose_result(
        text="composed",
        data={"answer": 42},
        results=[direct, lm],
        mode="multi-agentic-system",
        input="question",
    )

    normalized = result.normalized()
    assert normalized["runtime"]["engine"] == "openai-runtime"
    assert normalized["runtime"]["framework"] == "agentic-systems"
    assert normalized["usage"]["total_tokens"] == 12
    assert normalized["tools"][0]["name"] == "sumar"
    assert result.meta["engines_used"] == ["python-runtime", "openai-runtime"]
