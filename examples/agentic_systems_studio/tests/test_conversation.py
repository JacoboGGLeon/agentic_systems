from __future__ import annotations

from types import SimpleNamespace

import pytest
import agentic_systems as toolkit
from agentic_systems.tools import ToolEvent

from agentic_systems_studio.conversation import (
    ConversationConfig,
    ConversationalStudio,
    prepare_conversation_context,
    safe_calculate,
)


def test_conversation_config_uses_environment_without_secrets(monkeypatch):
    monkeypatch.setenv("AGENTIC_SYSTEMS_PROVIDER", "bedrock-runtime")
    monkeypatch.setenv("AGENTIC_SYSTEMS_FRAMEWORK", "strands")
    monkeypatch.setenv("AGENTIC_SYSTEMS_MODEL", "test-model")
    monkeypatch.setenv("AGENTIC_SYSTEMS_TIMEOUT_S", "45")

    config = ConversationConfig.from_environment()

    assert config.provider == "bedrock-runtime"
    assert config.framework == "strands"
    assert config.framework_value == "strands"
    assert config.model == "test-model"
    assert config.timeout_s == 45
    assert ConversationConfig(framework="native").framework_value is None


def test_conversational_tools_are_bounded_and_deterministic():
    calculation = safe_calculate.run({"expression": "17 * 19"})
    assert calculation.ok is True
    assert calculation.data["result"] == 323

    context = prepare_conversation_context.run(
        {
            "messages": [
                {"role": "system", "content": "private"},
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            "message": "next",
        }
    )
    assert context.ok is True
    assert context.data["history_turns"] == 2
    assert all(item["role"] != "system" for item in context.data["history"])


@pytest.mark.parametrize(
    "framework", ["native", "langgraph", "openai-agents", "strands"]
)
def test_conversational_studio_composes_real_run_results(framework):
    context_payload = {
        "message": "17 * 19",
        "history": [],
        "history_turns": 0,
        "policy": {"reasoning_is_private": True},
    }
    context_result = toolkit.RunResult(
        text="context",
        engine="python-runtime",
        model="python-runtime",
        mode="default",
        tool_events=[
            ToolEvent(
                id="context-1",
                name="prepare_conversation_context",
                input={},
                output=context_payload,
                ok=True,
            )
        ],
    )
    answer_result = toolkit.RunResult(
        text="323",
        engine="vllm-runtime",
        model="qwen-test",
        mode="default",
        usage={"total_tokens": 12},
    )
    studio = ConversationalStudio(
        config=ConversationConfig(provider="vllm-runtime", framework=framework),
        reasoning_system=object(),
        deterministic_system=object(),
        assistant=SimpleNamespace(run=lambda *_args: answer_result),
        context_agent=SimpleNamespace(run=lambda *_args: context_result),
    )

    result = studio.run("17 * 19")

    assert result.ok is True
    assert result.text == "323"
    assert result.engine == "vllm-runtime"
    assert result.meta["framework"] == framework
    assert result.meta["engines_used"] == ["python-runtime", "vllm-runtime"]
    assert result.data["context_summary"] == {
        "history_turns": 0,
        "policy": {"reasoning_is_private": True},
    }
