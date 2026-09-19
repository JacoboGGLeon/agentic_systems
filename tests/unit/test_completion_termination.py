import asyncio
from types import SimpleNamespace

import httpx
import pytest
from agents import ModelResponse
from agents.usage import Usage

from agentic_systems.integrations.adapters.openai_models import (
    ChatCompletionTermination,
    IncompleteModelResponse,
    ToolCallNormalizingModel,
)
from agentic_systems.integrations.adapters.openai_agents import _failure


@pytest.mark.parametrize("reason", ["length", "content_filter"])
def test_termination_is_retained_without_repeating_delegate(reason):
    observer = ChatCompletionTermination()
    calls = []

    async def respond(*args, **kwargs):
        calls.append(True)
        await observer.observe(
            httpx.Response(
                200,
                json={
                    "choices": [{"finish_reason": reason}],
                    "usage": {"completion_tokens": 17},
                },
            )
        )
        return ModelResponse(
            output=[], usage=Usage(requests=1, output_tokens=17), response_id=None
        )

    model = ToolCallNormalizingModel(
        SimpleNamespace(get_response=respond), [], observer
    )
    with pytest.raises(IncompleteModelResponse) as caught:
        asyncio.run(model.get_response())
    assert calls == [True]
    result = _failure(
        SimpleNamespace(engine="ollama-runtime", model="arbitrary"),
        "input",
        "eval",
        caught.value,
    )
    assert not result.ok
    assert result.meta["termination"]["reason"] == reason
    assert result.meta["termination"]["response_usage"] == {"completion_tokens": 17}
    assert observer.reason.get() is None


def test_observer_isolated_between_concurrent_requests():
    observer = ChatCompletionTermination()

    async def respond(reason):
        await observer.observe(
            httpx.Response(200, json={"choices": [{"finish_reason": reason}]})
        )
        await asyncio.sleep(0)
        return ModelResponse(output=[], usage=Usage(requests=1), response_id=None)

    model = ToolCallNormalizingModel(
        SimpleNamespace(get_response=respond), [], observer
    )

    async def run():
        return await asyncio.gather(
            model.get_response("length"),
            model.get_response("stop"),
            return_exceptions=True,
        )

    failed, completed = asyncio.run(run())
    assert isinstance(failed, IncompleteModelResponse)
    assert failed.termination["response_usage"] is None
    assert isinstance(completed, ModelResponse)
