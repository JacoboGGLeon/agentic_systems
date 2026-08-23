from __future__ import annotations

import importlib
import time

import pytest

import agentic_systems as lab
from agentic_systems.engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    OPENAI_RUNTIME_ENGINE,
    PYTHON_RUNTIME_ENGINE,
)
from agentic_systems.core import runtime as runtime_module
from agentic_systems.results import RunResult

system_module = importlib.import_module("agentic_systems.system")


def test_public_runtime_scheduler_factories_and_aliases() -> None:
    sched = lab.scheduler(
        timeout_s=10, max_retries=2, max_tool_calls=3, max_turns=4, max_concurrency=1
    )
    runtime = lab.runtime(
        provider="python-runtime", model="m1", region="r1", scheduler=sched
    )

    assert isinstance(sched, lab.SchedulerConfig)
    assert isinstance(runtime, lab.RuntimeConfig)
    assert runtime.provider == PYTHON_RUNTIME_ENGINE
    assert runtime.model_id == "m1"
    assert runtime.region_name == "r1"
    assert runtime.scheduler.max_retries == 2

    system_from_runtime = lab.AgenticSystem(runtime=runtime)
    assert system_from_runtime.model == "m1"
    assert system_from_runtime.region == "r1"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"timeout_s": 0},
        {"max_retries": -1},
        {"max_tool_calls": -1},
        {"max_turns": 0},
        {"max_concurrency": 0},
        {"backoff_s": -0.1},
    ],
)
def test_scheduler_rejects_invalid_limits(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        lab.scheduler(**kwargs)


def test_python_runtime_runtime_retries_failed_agent_run() -> None:
    state = {"calls": 0}

    @lab.tool(metadata={"retryable": True})
    def flaky(value: int) -> dict:
        state["calls"] += 1
        if state["calls"] == 1:
            raise RuntimeError("temporary failure")
        return {"result": value * 2}

    runtime = lab.runtime(
        provider="python-runtime",
        scheduler=lab.scheduler(
            timeout_s=2, max_retries=1, max_tool_calls=5, max_turns=6
        ),
    )
    agent = lab.agent(name="retry_agent", tools=[flaky], runtime=runtime)

    result = agent.run({"tool": "flaky", "input": {"value": 21}})

    assert result.ok is True
    assert result.data["result"] == 42
    assert state["calls"] == 2
    assert result.usage["scheduler"]["attempts"] == 2
    assert result.usage["scheduler"]["retries"] == 1


def test_python_runtime_does_not_retry_unclassified_failure() -> None:
    state = {"calls": 0}

    @lab.tool
    def permanent_failure(value: int) -> dict:
        state["calls"] += 1
        raise ValueError(f"invalid {value}")

    runtime = lab.runtime(
        provider="python-runtime",
        scheduler=lab.scheduler(timeout_s=2, max_retries=3),
    )
    result = lab.agent(
        name="permanent_failure_agent", tools=[permanent_failure], runtime=runtime
    ).run({"tool": "permanent_failure", "input": {"value": 21}})

    assert result.ok is False
    assert result.should_retry() is False
    assert state["calls"] == 1
    assert result.usage["scheduler"]["attempts"] == 1
    assert result.usage["scheduler"]["retries"] == 0


def test_python_runtime_runtime_times_out_slow_tool() -> None:
    @lab.tool
    def slow(value: int) -> dict:
        time.sleep(0.2)
        return {"result": value}

    runtime = lab.runtime(
        provider="python-runtime",
        scheduler=lab.scheduler(timeout_s=0.01, max_retries=0),
    )
    agent = lab.agent(name="timeout_agent", tools=[slow], runtime=runtime)

    result = agent.run({"tool": "slow", "input": {"value": 1}})

    assert result.ok is False
    assert result.data["error"]["code"] == "scheduler_timeout"
    assert result.usage["scheduler"]["timed_out"] is True
    assert result.meta["scheduler"]["timeout_s"] == 0.01


def test_scheduler_max_tool_calls_limits_python_runtime_plan() -> None:
    @lab.tool
    def add_one(value: int) -> dict:
        return {"value": value + 1}

    runtime = lab.runtime(
        provider="python-runtime",
        scheduler=lab.scheduler(max_tool_calls=1, timeout_s=2),
    )
    agent = lab.agent(name="limit_agent", tools=[add_one], runtime=runtime)

    result = agent.run(
        {
            "steps": [
                {"tool": "add_one", "input": {"value": 1}},
                {"tool": "add_one", "input": {"value": 2}},
            ]
        }
    )

    assert result.ok is False
    assert result.data["error"]["code"] == "max_tool_calls_exceeded"
    assert result.meta["scheduler"]["max_tool_calls"] == 1


def test_unbound_python_runtime_agent_has_no_scheduler_meta() -> None:
    @lab.tool
    def add(a: int, b: int) -> dict:
        return {"result": a + b}

    agent = lab.Agent(name="legacy_local", tools=[add], engine="python-runtime")
    result = agent.run({"tool": "add", "input": {"a": 1, "b": 2}})

    assert result.ok is True
    assert "scheduler" not in result.meta


def test_bedrock_provider_path_receives_scheduler_limited_policy_without_hydrating_bedrock() -> (
    None
):
    captured = {}

    class FakeBedrockEngine:
        name = BEDROCK_RUNTIME_ENGINE

        def run(self, agent, input, policy, *, mode="default") -> RunResult:
            captured["max_turns"] = policy.max_turns
            captured["max_tool_calls"] = policy.max_tool_calls
            return RunResult(
                text="ok",
                data={"ok": True},
                ok=True,
                engine=self.name,
                model=agent.model or "m",
                mode=mode,
            )

    runtime = lab.runtime(
        provider="bedrock-runtime",
        model="fake-model",
        region="us-east-1",
        scheduler=lab.scheduler(max_turns=3, max_tool_calls=2, timeout_s=2),
    )
    system = lab.AgenticSystem(model="fake-model", region="us-east-1", runtime=runtime)
    system._engines[BEDROCK_RUNTIME_ENGINE] = FakeBedrockEngine()
    agent = system.agent(
        name="cloud", instructions="Return ok.", tools=[], engine="bedrock-runtime"
    )

    result = agent.run("hello")

    assert result.ok is True
    assert captured == {"max_turns": 3, "max_tool_calls": 2}
    assert result.meta["runtime"]["provider"] == BEDROCK_RUNTIME_ENGINE
    assert result.meta["scheduler"]["max_turns"] == 3


def test_runtime_auto_prefers_openai_when_openai_signal_exists(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.setattr(
        runtime_module, "_module_available", lambda name: name == "openai"
    )

    runtime = lab.runtime(
        provider="auto",
        provider_priority=["openai-runtime", "bedrock-runtime", "vllm-runtime"],
    )
    system = lab.AgenticSystem(model="m", region="r", runtime=runtime)

    assert runtime.provider == "auto"
    assert (
        system._engine(runtime.provider).__class__.__name__ == "OpenAIRuntimeProvider"
    )


def test_runtime_auto_describe_resolves_openai_signal(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.setattr(
        runtime_module, "_module_available", lambda name: name == "openai"
    )

    summary = lab.runtime(provider="auto").describe()

    assert summary["selected_provider"] == OPENAI_RUNTIME_ENGINE
    assert summary["model"] == "gpt-test"
    assert summary["mode"] == "auto"
    assert summary["preferred_provider"] == OPENAI_RUNTIME_ENGINE
    assert "OPENAI" in summary["reason"]


def test_openai_runtime_reads_environment_config_without_leaking_secret(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-env-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.openai.test/v1")

    runtime = lab.runtime(provider="openai-runtime")
    summary = runtime.describe()

    assert runtime.model_id == "gpt-env-model"
    assert summary["model"] == "gpt-env-model"
    assert summary["configuration"]["openai"] == {
        "api_key_configured": True,
        "base_url": "https://example.openai.test/v1",
        "model_env_vars": ["OPENAI_MODEL"],
    }
    assert "secret-test-key" not in str(summary)


def test_runtime_auto_falls_back_to_bedrock_when_aws_signal_exists(monkeypatch) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "y")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    runtime = lab.runtime(provider="auto", region="us-east-1")
    system = lab.AgenticSystem(model="m", region="us-east-1", runtime=runtime)

    assert runtime.provider == "auto"
    assert system._engine(runtime.provider).__class__.__name__ == "BedrockEngine"


def test_runtime_auto_describe_resolves_bedrock_signal(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setattr(
        runtime_module, "_module_available", lambda name: name == "boto3"
    )

    summary = lab.runtime(provider="auto", region="us-east-1").describe()

    assert summary["selected_provider"] == BEDROCK_RUNTIME_ENGINE
    assert summary["mode"] == "auto"
    assert summary["preferred_provider"] == BEDROCK_RUNTIME_ENGINE
    assert "AWS" in summary["reason"]


def test_runtime_auto_does_not_treat_region_as_bedrock_credentials(monkeypatch) -> None:
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "")
    monkeypatch.setenv("AWS_PROFILE", "")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("VLLM_BASE_URL", "")
    monkeypatch.setenv("OLLAMA_BASE_URL", "")
    monkeypatch.setenv("OLLAMA_MODEL", "")
    monkeypatch.setattr(
        runtime_module, "_aws_shared_credentials_present", lambda: False
    )
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "")
    monkeypatch.setenv("AWS_ROLE_ARN", "")
    monkeypatch.setenv("AWS_WEB_IDENTITY_TOKEN_FILE", "")
    monkeypatch.setenv("AWS_CONTAINER_CREDENTIALS_FULL_URI", "")
    monkeypatch.setenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "")
    monkeypatch.setattr(
        runtime_module, "_module_available", lambda name: name in {"boto3", "openai"}
    )

    summary = lab.runtime(provider="auto").describe()

    assert summary["selected_provider"] == OPENAI_RUNTIME_ENGINE
    assert summary["fallback_provider"] is None


def test_runtime_auto_describe_reports_unresolved_without_backend_signal(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "")
    monkeypatch.setenv("AWS_PROFILE", "")
    monkeypatch.setenv("AWS_REGION", "")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "")
    monkeypatch.setattr(runtime_module, "_module_available", lambda name: False)

    summary = lab.runtime(provider="auto").describe()

    assert summary["selected_provider"] == "auto"
    assert summary["mode"] == "auto-unresolved"
    assert "VLLM_BASE_URL" in summary["reason"]
    assert "OPENAI_API_KEY" in summary["reason"]
    assert "AWS" in summary["reason"]


def test_runtime_auto_accepts_bedrock_api_key_with_region(monkeypatch) -> None:
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "secret-bedrock-key")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("VLLM_BASE_URL", "")
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setattr(
        runtime_module, "_aws_shared_credentials_present", lambda: False
    )
    monkeypatch.setattr(
        runtime_module, "_module_available", lambda name: name == "boto3"
    )

    summary = lab.runtime(provider="auto").describe()

    assert summary["selected_provider"] == BEDROCK_RUNTIME_ENGINE
    assert summary["configuration"]["bedrock"] == {
        "aws_region": "us-east-1",
        "aws_profile_configured": False,
        "bedrock_api_key_configured": True,
        "credentials_configured": True,
    }
    assert "secret-bedrock-key" not in str(summary)


def test_runtime_auto_errors_without_backend_signal(monkeypatch) -> None:
    for key in (
        "VLLM_BASE_URL",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "AWS_BEARER_TOKEN_BEDROCK",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(runtime_module, "_module_available", lambda name: False)

    with pytest.raises(ValueError, match="provider='auto' could not resolve a backend"):
        system_module._resolve_auto_provider(model=None, region=None)
