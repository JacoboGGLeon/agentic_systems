from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
import agentic_systems as toolkit
from agentic_systems.tools import ToolEvent

from agentic_systems_studio.conversation import (
    ConversationConfig,
    build_conversational_system,
    ConversationalStudio,
    prepare_conversation_context,
    safe_calculate,
)
from agentic_systems_studio.environment import load_studio_environment


def test_conversation_config_uses_canonical_dotenv_without_secrets(
    monkeypatch, tmp_path
):
    environment = tmp_path / ".env"
    environment.write_text(
        "AGENTIC_SYSTEMS_PROVIDER=bedrock-runtime\n"
        "AGENTIC_SYSTEMS_FRAMEWORK=strands\n"
        "AGENTIC_SYSTEMS_MODEL=test-model\n"
        "AGENTIC_SYSTEMS_TIMEOUT_S=45\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTIC_SYSTEMS_ENV_FILE", str(environment))
    monkeypatch.setenv("AGENTIC_SYSTEMS_PROVIDER", "stale-runtime-value")
    monkeypatch.setenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "/managed/role")

    config = ConversationConfig.from_environment()

    assert config.provider == "bedrock-runtime"
    assert config.framework == "strands"
    assert config.framework_value == "strands"
    assert config.model == "test-model"
    assert config.timeout_s == 45
    assert os.environ["AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"] == "/managed/role"
    assert ConversationConfig(framework="native").framework_value is None


def test_load_studio_environment_reports_the_resolved_contract(monkeypatch, tmp_path):
    environment = tmp_path / ".env"
    environment.write_text("RUN_STUDIO_LIVE=1\n", encoding="utf-8")
    monkeypatch.setenv("AGENTIC_SYSTEMS_ENV_FILE", str(environment))
    monkeypatch.setenv("RUN_STUDIO_LIVE", "0")

    resolved = load_studio_environment()

    assert resolved == environment.resolve()
    assert os.environ["RUN_STUDIO_LIVE"] == "1"


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


def test_context_agent_run_uses_public_default_mode_and_public_data():
    studio = build_conversational_system(
        ConversationConfig(provider="openai-runtime", model="offline-contract-model")
    )

    result = studio.context_agent.run(
        {
            "tool": "prepare_conversation_context",
            "input": {"messages": [], "message": "hola"},
        }
    )

    assert result.ok is True
    assert result.data["message"] == "hola"
    assert result.data["history_turns"] == 0


def test_conversational_studio_inspect_uses_public_report_projection():
    studio = build_conversational_system(
        ConversationConfig(provider="openai-runtime", model="offline-contract-model")
    )

    report = studio.inspect()

    assert report["deterministic_system"]["ok"] is True
    assert report["reasoning_system"]["ok"] is True
    assert report["configuration"]["provider"] == "openai-runtime"
    assert len(report["agents"]) == 2


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
        data=context_payload,
        tool_events=[
            ToolEvent(
                id="context-1",
                name="prepare_conversation_context",
                input={},
                output={"data": context_payload},
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
