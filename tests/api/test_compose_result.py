from __future__ import annotations

from ._load_legacy import export_legacy_tests

export_legacy_tests(
    globals(),
    'notebook_public_helpers',
    'compare_keys_and_usage',
    'agnostic_output_blocks',
)


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
