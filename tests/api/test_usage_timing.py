from __future__ import annotations

from types import SimpleNamespace

from agentic_systems import RunResult, run_result_summary
from agentic_systems.providers.bedrock_runtime import BedrockRuntime
from agentic_systems.results import RunResult as RunResultModel
from agentic_systems.utils import chain_history_summary


def test_run_result_summary_keeps_complete_usage_when_requested() -> None:
    result = RunResult(
        text="ok",
        ok=True,
        validation={"ok": True, "issues": []},
        usage={
            "requests": 2,
            "input_tokens": 100,
            "output_tokens": 25,
            "total_tokens": 125,
            "service_latency_ms": 900.0,
            "client_duration_ms": 950.5,
        },
    )

    summary = run_result_summary(result, include_usage=True)

    assert summary["usage"] == {
        "requests": 2,
        "input_tokens": 100,
        "output_tokens": 25,
        "total_tokens": 125,
        "service_latency_ms": 900.0,
        "client_duration_ms": 950.5,
    }
    assert "tokens" not in summary["usage"]


def test_usage_totals_aggregate_tokens_and_timing_from_raw_responses() -> None:
    runtime_result = SimpleNamespace(
        model_dump=lambda mode="json": {
            "final_text": "ok",
            "raw_responses": [
                {
                    "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
                    "service_latency_ms": 100,
                    "client_duration_ms": 110.25,
                },
                {
                    "usage": {"inputTokens": 20, "outputTokens": 7, "totalTokens": 27},
                    "service_latency_ms": 200,
                    "client_duration_ms": 220.75,
                },
            ],
        }
    )

    result = RunResultModel.from_bedrock_runtime(
        runtime_result,
        engine="bedrock-runtime",
        model="test-model",
        mode="eval",
    )

    assert result.usage == {
        "input_tokens": 30,
        "output_tokens": 12,
        "total_tokens": 42,
        "requests": 2,
        "service_latency_ms": 300.0,
        "client_duration_ms": 331.0,
    }


def test_bedrock_compact_response_metadata_keeps_latency_fields() -> None:
    response = {
        "ResponseMetadata": {"RequestId": "abc", "HTTPStatusCode": 200},
        "usage": {"inputTokens": 1, "outputTokens": 2, "totalTokens": 3},
        "metrics": {"latencyMs": 123},
        "agentic_systems": {"client_duration_ms": 130.5},
        "stopReason": "end_turn",
    }

    compact = BedrockRuntime._compact_response_metadata(response)

    assert compact["service_latency_ms"] == 123
    assert compact["client_duration_ms"] == 130.5


def test_chain_history_summary_includes_complete_usage() -> None:
    history = [
        {
            "name": "step_one",
            "kind": "complete",
            "output": {
                "ok": True,
                "text": "Cuarenta y dos.",
                "usage": {"requests": 1, "input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
            },
        }
    ]

    rows = chain_history_summary(history)

    assert rows[0]["usage"] == {"requests": 1, "input_tokens": 10, "output_tokens": 4, "total_tokens": 14}
