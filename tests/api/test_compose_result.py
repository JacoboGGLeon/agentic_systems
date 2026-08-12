from __future__ import annotations



def test_compose_result_preserves_runtime_metadata_usage_and_tools():
    import agentic_systems as lab
    from agentic_systems.tools import ToolEvent

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


def test_compose_result_usage_edge_cases():
    import agentic_systems as lab

    class OddUsage:
        usage = ["not", "a", "mapping"]
        engine = "python-runtime"
        model = "python-runtime"
        mode = "eval"
        ok = True
        tool_events = []
        raw_responses = []
        messages = []

    bool_usage = lab.RunResult(
        text="bool",
        data={},
        engine="python-runtime",
        model="python-runtime",
        usage={"cached": True, "label": "first"},
    )
    fallback = lab.RunResult(text="fallback", data={}, engine="python-runtime", model="python-runtime")

    result = lab.compose_result(
        text="edge",
        data={"ok": True},
        results=[OddUsage(), fallback, bool_usage],
        mode="edge",
    )

    assert result.engine == "python-runtime"
    assert result.usage["cached"] is True
    assert result.usage["label"] == "first"


def test_compose_result_empty_results_and_explicit_runtime():
    import agentic_systems as lab

    result = lab.compose_result(
        text="empty",
        data={"ok": True},
        results=[],
        mode="empty",
        engine="openai-runtime",
        model="gpt-test",
    )

    assert result.ok is True
    assert result.engine == "openai-runtime"
    assert result.model == "gpt-test"
    assert result.meta["engines_used"] == ["openai-runtime"]

def test_compose_result_keeps_execution_engine_as_runtime_not_framework():
    import agentic_systems as lab

    result = lab.compose_result(
        text="workflow",
        data={"ok": True},
        results=[],
        mode="workflow",
        framework="agentic-systems",
        engine="python-runtime",
    )

    assert result.meta["framework"] == "agentic-systems"
    assert result.meta["runtime_engine"] == "python-runtime"
    assert result.meta["execution_engine"] == "python-runtime"
