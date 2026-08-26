from __future__ import annotations

import agentic_systems as toolkit

from agentic_systems.integrations.adapters.strands import _strands_usage
from agentic_systems.results import RunResult
from agentic_systems.usage import merge_usage, normalize_usage


@toolkit.tool
def echo_usage(value: int) -> dict[str, int]:
    return {"value": value}


class FakeStrandsMetrics:
    def get_summary(self) -> dict:
        return {
            "total_cycles": 2,
            "total_duration": 0.125,
            "accumulated_usage": {
                "inputTokens": 13,
                "outputTokens": 7,
                "totalTokens": 20,
            },
            "accumulated_metrics": {"latencyMs": 81.5},
        }


def test_usage_aliases_are_canonical_and_backward_compatible() -> None:
    usage = normalize_usage(
        {"prompt_tokens": 11, "completion_tokens": 4, "total_tokens": 15}
    )

    assert usage["input_tokens"] == 11
    assert usage["output_tokens"] == 4
    assert usage["prompt_tokens"] == 11
    assert usage["completion_tokens"] == 4


def test_usage_accumulates_every_provider_request() -> None:
    usage = merge_usage(
        {"requests": 1, "prompt_tokens": 3, "completion_tokens": 2},
        {"requests": 1, "prompt_tokens": 5, "completion_tokens": 4},
    )

    assert usage["requests"] == 2
    assert usage["input_tokens"] == 8
    assert usage["output_tokens"] == 6
    assert usage["total_tokens"] == 14


def test_normalized_result_exposes_provider_and_stable_nullable_usage() -> None:
    result = RunResult(
        text="ok",
        engine="ollama-runtime",
        usage={"prompt_tokens": 3, "completion_tokens": 2},
    )

    assert result.usage["input_tokens"] == 3
    normalized = result.normalized()
    assert normalized["runtime"]["provider"] == "ollama-runtime"
    assert normalized["runtime"]["engine"] == "ollama-runtime"
    assert normalized["usage"]["input_tokens"] == 3
    assert normalized["usage"]["output_tokens"] == 2
    assert normalized["usage"]["total_tokens"] == 5
    assert "service_latency_ms" not in normalized["usage"]


def test_strands_public_metrics_are_not_dropped() -> None:
    usage = _strands_usage(FakeStrandsMetrics())

    assert usage["requests"] == 2
    assert usage["input_tokens"] == 13
    assert usage["output_tokens"] == 7
    assert usage["total_tokens"] == 20
    assert usage["service_latency_ms"] == 81.5
    assert usage["client_duration_ms"] == 125.0


def test_scheduler_supplies_client_duration_without_service_latency() -> None:
    runtime = toolkit.runtime(
        provider="python-runtime",
        scheduler=toolkit.scheduler(timeout_s=5, max_retries=0),
    )
    system = toolkit.system(runtime=runtime)
    agent = system.agent(
        name="usage",
        instructions="Run the deterministic Tool.",
        tools=[echo_usage],
    )

    result = agent.run({"tool": "echo_usage", "input": {"value": 7}})

    assert result.ok is True
    assert result.usage["client_duration_ms"] >= 0
    assert "service_latency_ms" not in result.usage
    assert "service_latency_ms" not in result.normalized()["usage"]
