"""Execution configuration uses validated models without expanding public grammar."""

import asyncio
import json
import threading
import time

import pydantic
import pytest
import agentic_systems as toolkit
from agentic_systems._engine.core.scheduler import SchedulerConfig, SchedulerTimeoutError, execute_sync, execute_async, merge_policy_with_scheduler
from agentic_systems._engine.contracts import RunPolicy
from agentic_systems._contracts import _validate_policy


@pytest.mark.parametrize("provider", ["python-runtime", "openai-runtime", "bedrock-runtime", "ollama-runtime", "vllm-runtime"])
def test_runtime_is_a_frozen_contract_with_scheduler_parity(provider):
    config = toolkit.runtime(provider=provider, max_turns=3, max_tool_calls=2, max_retries=1, timeout_s=5, max_concurrency=2)
    assert isinstance(config, pydantic.BaseModel)
    engine = config._to_engine()
    assert isinstance(engine.scheduler, pydantic.BaseModel)
    for key in SchedulerConfig.model_fields:
        assert getattr(config, key) == getattr(engine.scheduler, key)
    assert "properties" in config.model_json_schema()
    json.loads(config.model_dump_json())
    with pytest.raises(pydantic.ValidationError):
        config.max_turns = 100


@pytest.mark.parametrize("kwargs", [{"max_turns": True}, {"max_tool_calls": -1}, {"max_retries": "2"}, {"timeout_s": float("inf")}, {"timeout_s": 0}, {"backoff_s": float("nan")}, {"max_concurrency": 0}, {"provider": "auto"}, {"provider": "python-runtime", "api_key": "secret"}, {"provider": "openai-runtime", "region": "any"}])
def test_bad_runtime_fails_before_execution(kwargs):
    with pytest.raises(pydantic.ValidationError):
        toolkit.runtime(**{"provider": "python-runtime", **kwargs})


def test_runtime_secrets_are_not_contract_data_or_error_text():
    secret = "PRIVATE_CREDENTIAL_SHOULD_NOT_APPEAR"
    config = toolkit.runtime(provider="openai-runtime", api_key=secret)
    assert isinstance(config.api_key, pydantic.SecretStr)
    assert secret not in repr(config) + config.model_dump_json() + str(config.inspect())
    with pytest.raises(pydantic.ValidationError) as error:
        toolkit.runtime(provider="python-runtime", api_key=secret)
    assert secret not in str(error.value)


@pytest.mark.parametrize("name", ["native", "openai-agents", "strands"])
def test_framework_contract_and_native_objects(name):
    opaque = object()
    config = toolkit.framework(name, agent_kwargs={} if name == "native" else {"handoffs": [opaque]})
    assert isinstance(config, pydantic.BaseModel)
    json.loads(config.model_dump_json())
    if name != "native":
        assert config._to_engine().agent_kwargs["handoffs"][0] is opaque
    with pytest.raises(TypeError):
        config.agent_kwargs["model"] = "escape"


@pytest.mark.parametrize("kwargs", [{"name": "langgraph"}, {"name": "native", "agent_kwargs": {"handoffs": []}}, {"name": "strands", "run_kwargs": {"max_concurrency": 3}}, {"name": "openai-agents", "agent_kwargs": {"model_settings": {"max_tokens": 99}}}, {"name": "strands", "agent_kwargs": {"config": {"children": [{"model": "escape"}]}}}])
def test_framework_cannot_override_owned_controls(kwargs):
    with pytest.raises(pydantic.ValidationError):
        toolkit.framework(**kwargs)


@pytest.mark.parametrize("kwargs", [{"max_actions": True}, {"max_actions": 0}, {"timeout_s": "2"}, {"timeout_s": float("nan")}, {"max_tokens": 12}])
def test_global_limits_are_closed_and_strict(kwargs):
    unit = toolkit.System("deadline", toolkit.Graph(pydantic.create_model("DeadlineState", value=(int, ...))))
    with pytest.raises((TypeError, pydantic.ValidationError, ValueError)):
        unit.run({"value": 1}, **kwargs)


def test_policy_model_has_one_input_and_preserves_omitted_defaults():
    class UserPolicy(pydantic.BaseModel):
        repair: bool = False
        max_repairs: int = 0

    @toolkit.tool
    def echo(value: int) -> dict:
        return {"value": value}

    actor = toolkit.Agent("operator", runtime=toolkit.runtime(provider="python-runtime"), skills=(toolkit.skill(name="echo", tools=(echo,)),), policy=UserPolicy())
    assert isinstance(actor.policy, pydantic.BaseModel)
    assert _validate_policy(actor.policy) == {"repair": False, "max_repairs": 0}
    assert _validate_policy(None) == {}
    assert actor.run({"value": 3}).data == {"value": 3}
    for bad in ({"repair": "false"}, {"temperature": True}, {"temperature": float("inf")}, {"max_repairs": -1}, {"max_turns": 2}, {"tool_choice": "guess"}):
        with pytest.raises(pydantic.ValidationError):
            toolkit.Agent("invalid", runtime=toolkit.runtime(provider="python-runtime"), skills=actor.skills, policy=bad)


def test_scheduler_retries_and_timeout_keep_real_evidence():
    seen = []
    def flaky():
        seen.append(1)
        if len(seen) == 1:
            raise ConnectionError("transient")
        return "ready"

    value, meta = execute_sync(flaky, SchedulerConfig(max_retries=1))
    assert value == "ready" and meta["attempts"] == 2 and meta["retries"] == 1
    config = SchedulerConfig(timeout_s=0.005)
    completed = threading.Event()
    def slow():
        time.sleep(0.03)
        completed.set()
    with pytest.raises(SchedulerTimeoutError):
        execute_sync(slow, config)
    assert completed.wait(1), "A timeout does not claim to terminate a running worker"
    assert "_executor" not in config.model_dump_json()
    assert config._executor is not None
    config._executor.shutdown(wait=True)


def test_async_scheduler_and_stricter_loop_caps():
    async def operation():
        return 7
    value, meta = asyncio.run(execute_async(operation, SchedulerConfig(timeout_s=1)))
    assert value == 7 and meta["attempts"] == 1
    policy = RunPolicy(max_turns=2, max_tool_calls=1)
    merged = merge_policy_with_scheduler(policy, SchedulerConfig(max_turns=9, max_tool_calls=8))
    assert merged.max_turns == 2 and merged.max_tool_calls == 1
    assert not hasattr(toolkit, "Scheduler") and not hasattr(toolkit, "Policy")
