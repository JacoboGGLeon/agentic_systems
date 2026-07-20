
from __future__ import annotations

import asyncio
import importlib
import sys
import time
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ValidationError

from agentic_systems.agents import Agent, _coerce_output_data, _contract_name, _json_like
from agentic_systems.contracts import AgentContract, ContractPolicySpec, RunPolicy, resolve_policy, validate_contract_policy
from agentic_systems.core import runtime as runtime_core_module
from agentic_systems.core.runtime import RuntimeConfig, _auto_reason, _auto_unresolved_reason, _find_dotenv, _load_dotenv, _module_available, _provider_available, normalize_provider_priority, resolve_auto_provider
from agentic_systems.core.scheduler import (
    SchedulerConfig,
    SchedulerConfigError,
    SchedulerTimeoutError,
    execute_async,
    execute_sync,
    merge_policy_with_scheduler,
)
from agentic_systems.engines.names import BEDROCK_RUNTIME_ENGINE, OPENAI_RUNTIME_ENGINE, PYTHON_DIRECT_ENGINE
from agentic_systems.results import RunResult
import agentic_systems.factories as factories_module
import agentic_systems.utils as utils_module
from agentic_systems.system import AgenticSystem, _merge_skill_inputs, _resolve_auto_provider
from agentic_systems.tools import Tool

system_module = importlib.import_module("agentic_systems.system")

class EchoEngine:
    def __init__(self, ok=True, fail=False):
        self.ok = ok
        self.fail = fail

    def run(self, agent, input, policy, *, mode="default"):
        if self.fail:
            raise RuntimeError("sync boom")
        return RunResult(text="sync", data={"input": input}, ok=self.ok, engine="echo", mode=mode)


class SyncOnlyEngine:
    def run(self, agent, input, policy, *, mode="default"):
        return RunResult(text="threaded", data={"input": input}, ok=True, engine="sync-only", mode=mode)


def test_scheduler_config_policy_retries_timeouts_and_async_paths():
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(timeout_s=0)
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(max_retries=-1)
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(max_tool_calls=-1)
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(max_turns=0)
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(max_concurrency=0)
    with pytest.raises(SchedulerConfigError):
        SchedulerConfig(backoff_s=-0.1)
    with pytest.raises(TypeError):
        SchedulerConfig.coerce("bad")

    scheduler = SchedulerConfig(timeout_s=None, max_retries=1, max_turns=3, max_tool_calls=2, backoff_s=0)
    assert scheduler.policy_overrides() == {"max_turns": 3, "max_tool_calls": 2}
    assert merge_policy_with_scheduler(RunPolicy(max_turns=9, max_tool_calls=9), scheduler).max_turns == 3
    object_policy = object()
    assert merge_policy_with_scheduler(object_policy, SchedulerConfig(max_turns=None, max_tool_calls=None)) is object_policy

    calls = {"count": 0}

    def flaky_value():
        calls["count"] += 1
        return "bad" if calls["count"] == 1 else "ok"

    value, meta = execute_sync(flaky_value, SchedulerConfig(timeout_s=None, max_retries=1, backoff_s=0.001), is_success=lambda item: item == "ok")
    assert value == "ok"
    assert meta["attempts"] == 2

    err_calls = {"count": 0}

    def flaky_exception():
        err_calls["count"] += 1
        if err_calls["count"] == 1:
            raise RuntimeError("first")
        return "ok"

    assert execute_sync(flaky_exception, scheduler)[0] == "ok"

    with pytest.raises(RuntimeError):
        execute_sync(lambda: (_ for _ in ()).throw(RuntimeError("always")), SchedulerConfig(max_retries=1, timeout_s=None))

    with pytest.raises(SchedulerTimeoutError):
        execute_sync(lambda: time.sleep(0.05), SchedulerConfig(timeout_s=0.001, max_retries=0))

    async def async_checks():
        async_calls = {"count": 0}

        async def flaky_async():
            async_calls["count"] += 1
            return "bad" if async_calls["count"] == 1 else "ok"

        value, async_meta = await execute_async(flaky_async, SchedulerConfig(timeout_s=None, max_retries=1, backoff_s=0.001), is_success=lambda item: item == "ok")
        assert value == "ok"
        assert async_meta["attempts"] == 2

        async def async_error():
            raise RuntimeError("async boom")

        with pytest.raises(RuntimeError):
            await execute_async(async_error, SchedulerConfig(max_retries=0, timeout_s=None))

        async def async_sleep():
            await asyncio.sleep(0.05)

        with pytest.raises(SchedulerTimeoutError):
            await execute_async(async_sleep, SchedulerConfig(timeout_s=0.001, max_retries=0))

    asyncio.run(async_checks())


def test_runtime_config_coerce_dotenv_and_describe(monkeypatch, tmp_path):
    base = RuntimeConfig(provider="openai-runtime", model_id="m", region_name="r", scheduler={"timeout_s": 7})
    coerced = RuntimeConfig.coerce(base, model="m2", region="r2", engine="python-runtime")
    assert coerced.provider == PYTHON_DIRECT_ENGINE
    assert coerced.model_id == "m2"
    assert coerced.region_name == "r2"
    assert coerced.scheduler.timeout_s == 7
    assert RuntimeConfig.coerce(None).provider == BEDROCK_RUNTIME_ENGINE
    assert RuntimeConfig.coerce({"provider": "openai-runtime"}).provider == OPENAI_RUNTIME_ENGINE
    with pytest.raises(TypeError):
        RuntimeConfig.coerce("bad")

    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    env_file = tmp_path / ".env"
    env_file.write_text("# ignored\nOPENAI_API_KEY='from-dotenv'\nBADLINE\nAWS_REGION=us-test-1\n", encoding="utf-8")
    monkeypatch.chdir(nested)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    assert _find_dotenv(nested) == env_file
    assert _load_dotenv(nested) is True
    outside = tmp_path.parent / "outside_without_env"
    outside.mkdir(exist_ok=True)
    assert _load_dotenv(outside) is False
    assert RuntimeConfig(provider="auto", metadata={"resolution": {"selected_provider": OPENAI_RUNTIME_ENGINE, "mode": "test"}, "openai": {"configured": True}}).describe()["selected_provider"] == OPENAI_RUNTIME_ENGINE
    explicit = RuntimeConfig(provider="auto", metadata={"resolution": {"selected_provider": "python-runtime", "mode": "test"}, "bedrock": {"configured": True}}).describe()
    assert explicit["selected_provider"] == PYTHON_DIRECT_ENGINE
    assert explicit["configuration"]["bedrock"]["configured"] is True


def test_agent_core_branches_bind_describe_async_scheduler_and_validation():
    def add(a: int, b: int) -> dict:
        return {"result": a + b}

    add_tool = Tool(add, name="add")
    agent = Agent(name="direct", tools=[add_tool], skills=[], engine="python-runtime")
    assert "Agent `direct`" in agent.describe()
    assert _contract_name(BaseModel) == "BaseModel"
    assert _json_like(type("X", (), {})) == "X"
    assert _coerce_output_data(RunResult(text="hello"), None).final == {"text": "hello"}
    assert _coerce_output_data(RunResult(text="", data={"a": 1}), None).final == {"a": 1}

    with pytest.raises(ValueError):
        Agent(name=" ")
    with pytest.raises(TypeError):
        agent.bind(None)
    assert agent.bind(agent.system) is agent if agent.system is not None else True

    runtime = RuntimeConfig(provider="python-runtime", scheduler={"timeout_s": None, "max_retries": 0})
    runtime_agent = Agent(name="runtime", tools=[add_tool], runtime=runtime)
    assert runtime_agent.engine == PYTHON_DIRECT_ENGINE

    system = AgenticSystem(model="m", region="r", runtime={"provider": "python-runtime", "scheduler": {"timeout_s": None, "max_retries": 0}})
    system._engines[PYTHON_DIRECT_ENGINE] = EchoEngine()
    sys_agent = system.agent(name="sys", instructions="x", tools=[add_tool], engine="python-runtime")
    assert asyncio.run(sys_agent.arun({"tool": "add", "input": {"a": 1, "b": 2}})).ok is True
    assert sys_agent.bind(system) is sys_agent
    default_mode_result = sys_agent.run({"tool": "add", "input": {"a": 1, "b": 2}})
    assert default_mode_result.mode == "eval"


    system._engines[PYTHON_DIRECT_ENGINE] = SyncOnlyEngine()
    sync_only = system.agent(name="sync_only", instructions="x", tools=[add_tool], engine="python-runtime")
    assert asyncio.run(sync_only.arun("x")).text == "threaded"

    failing_system = AgenticSystem(model="m", region="r", runtime={"provider": "python-runtime", "scheduler": {"timeout_s": None, "max_retries": 0}})
    failing_system._engines[PYTHON_DIRECT_ENGINE] = EchoEngine(fail=True)
    failing_agent = failing_system.agent(name="fail", instructions="x", tools=[add_tool], engine="python-runtime")
    result = failing_agent.run({"tool": "add", "input": {"a": 1, "b": 2}})
    assert result.ok is False
    assert result.meta["scheduler_execution"]["timed_out"] is False

    async_result = asyncio.run(failing_agent.arun({"tool": "add", "input": {"a": 1, "b": 2}}))
    assert async_result.ok is False
    assert async_result.meta["scheduler_execution"]["timed_out"] is False


    class SlowAsyncEngine:
        async def arun(self, agent, input, policy, *, mode="default"):
            await asyncio.sleep(0.05)
            return RunResult(text="late", ok=True, engine="slow", mode=mode)

    slow_system = AgenticSystem(model="m", region="r", runtime={"provider": "python-runtime", "scheduler": {"timeout_s": 0.001, "max_retries": 0}})
    slow_system._engines[PYTHON_DIRECT_ENGINE] = SlowAsyncEngine()
    slow_agent = slow_system.agent(name="slow", instructions="x", tools=[add_tool], engine="python-runtime")
    slow_result = asyncio.run(slow_agent.arun("x"))
    assert slow_result.data["error"]["code"] == "scheduler_timeout"

    non_direct = Agent(name="cloud", engine="openai-runtime")
    with pytest.raises(RuntimeError):
        asyncio.run(non_direct.arun("x"))

    dup = Agent(name="dup", tools=[add_tool], engine="python-runtime")
    dup.tools = ("add", "add")
    validation = dup.validate()
    assert any(issue.code == "duplicate_agent_tool" for issue in validation.issues)

    def untyped(x):
        return []

    bad_tool = Tool(untyped, name="bad_tool")
    invalid_agent = Agent(name="invalid", tools=[], engine="python-runtime")
    invalid_agent._direct_tools = (bad_tool,)
    invalid_agent.tools = ("bad_tool",)
    invalid_validation = invalid_agent.validate()
    assert any(issue.code == "missing_parameter_annotation" for issue in invalid_validation.issues)

    contract_agent = Agent(name="contract", tools=[add_tool], engine="python-runtime", contract={"must_call": ["add"]}, policy={"max_tool_calls": 0} if False else None)
    contract_agent.policy = RunPolicy(max_tool_calls=1)
    assert contract_agent.validate().ok is True


def test_system_core_branches_bedrock_hydration_auto_and_merge(monkeypatch):
    system = AgenticSystem(model="m", region="r")
    with pytest.raises(TypeError):
        system._register_tool_object(object())

    def broken() -> dict:
        raise RuntimeError("tool broken")

    broken_tool = Tool(broken, name="broken")
    system._register_tool_object(broken_tool)
    broken_result = system._runtime.execute_tool("broken", {})
    assert broken_result.ok is False
    assert "tool broken" in str(broken_result.data)

    runtime_module = types.ModuleType("agentic_systems.providers.bedrock_runtime")

    class FakeBedrockRuntime:
        def __init__(self, **kwargs):
            self.region_name = kwargs["region_name"]
            self.max_tokens_default = kwargs["max_tokens_default"]
            self.temperature_default = kwargs["temperature_default"]
            self._tools = {}
            self.runtime = "runtime"
            self.bedrock = "bedrock"
            self.sts = "sts"

        def run_direct(self):
            return "ok"

    runtime_module.BedrockRuntime = FakeBedrockRuntime
    monkeypatch.setitem(sys.modules, "agentic_systems.providers.bedrock_runtime", runtime_module)
    system._runtime.runtime = "previous-runtime"
    system._runtime.bedrock = "previous-bedrock"
    system._runtime.sts = "previous-sts"
    hydrated = system._ensure_bedrock_runtime()
    assert hydrated.region_name == "r"
    assert hydrated.runtime == "previous-runtime"
    assert system._ensure_bedrock_runtime() is hydrated

    system2 = AgenticSystem(model="m", region="r")
    system2._engines["bedrock"] = "legacy"
    assert system2._engine("bedrock-runtime") == "legacy"

    monkeypatch.setenv("OPENAI_API_KEY", "key")
    assert _resolve_auto_provider("m", None, (OPENAI_RUNTIME_ENGINE,)) == OPENAI_RUNTIME_ENGINE
    for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "AWS_REGION", "AWS_DEFAULT_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE", "VLLM_BASE_URL"):
        monkeypatch.setenv(key, "")
    monkeypatch.setattr(runtime_core_module, "_module_available", lambda name: False)
    with pytest.raises(ValueError):
        _resolve_auto_provider(None, None)

    assert normalize_provider_priority("openai-runtime,openai-runtime,bedrock-runtime") == (OPENAI_RUNTIME_ENGINE, BEDROCK_RUNTIME_ENGINE)
    assert normalize_provider_priority(None, allow_python_fallback=True)[-1] == PYTHON_DIRECT_ENGINE
    with pytest.raises(ValueError, match="provider_priority"):
        normalize_provider_priority(["auto"])
    assert resolve_auto_provider(None, [PYTHON_DIRECT_ENGINE]) == PYTHON_DIRECT_ENGINE
    assert RuntimeConfig(provider="auto", allow_python_fallback=True).describe()["selected_provider"] == PYTHON_DIRECT_ENGINE
    assert _auto_reason("unexpected-runtime") == "provider selected by configured priority"
    assert "python-runtime fallback" in _auto_unresolved_reason([PYTHON_DIRECT_ENGINE])
    assert _module_available("definitely_missing_agentic_systems_module") is False
    monkeypatch.setattr(runtime_core_module.importlib.util, "find_spec", lambda name: (_ for _ in ()).throw(ValueError("bad spec")))
    assert _module_available("broken") is False

    assert _merge_skill_inputs("one", None) == ["one"]
    assert _merge_skill_inputs(None, ["two"]) == ["two"]
    assert _merge_skill_inputs("one", ["two"]) == ["one", "two"]
    assert _merge_skill_inputs("one", "two") == ["one", "two"]
    assert _provider_available("unknown-runtime", None) is False
    assert factories_module._default_runtime_model("unknown-runtime", None) is None
    assert factories_module._default_runtime_region(BEDROCK_RUNTIME_ENGINE)
    monkeypatch.setattr(system_module.importlib.util, "find_spec", lambda name: (_ for _ in ()).throw(ValueError("bad spec")))
    assert system_module._module_available("broken") is False
    monkeypatch.setattr(utils_module.json, "loads", lambda value: (_ for _ in ()).throw(ValueError("bad json")))
    assert utils_module._looks_like_json_object("{bad}") is False
    monkeypatch.setattr(utils_module.re, "fullmatch", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad regex")))
    assert utils_module._coerce_field_value("123") == "123"
    assert _merge_skill_inputs("one", ["two"]) == ["one", "two"]
    assert _merge_skill_inputs("one", "two") == ["one", "two"]
    assert _provider_available("unknown-runtime", None) is False
    assert factories_module._default_runtime_model("unknown-runtime", None) is None
    assert factories_module._default_runtime_region(BEDROCK_RUNTIME_ENGINE)
    monkeypatch.setattr(system_module.importlib.util, "find_spec", lambda name: (_ for _ in ()).throw(ValueError("bad spec")))
    assert system_module._module_available("broken") is False
    monkeypatch.setattr(utils_module.json, "loads", lambda value: (_ for _ in ()).throw(ValueError("bad json")))
    assert utils_module._looks_like_json_object("{bad}") is False
    monkeypatch.setattr(utils_module.re, "fullmatch", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad regex")))
    assert utils_module._coerce_field_value("123") == "123"


def test_contract_policy_core_branches():
    with pytest.raises(ValidationError):
        RunPolicy(max_turns=0)
    with pytest.raises(ValidationError):
        RunPolicy(max_tool_calls=0)
    with pytest.raises(ValidationError):
        RunPolicy(max_repairs=-1)
    with pytest.raises(ValidationError):
        RunPolicy(temperature=3)
    with pytest.raises(ValidationError):
        RunPolicy(tool_choice=" ")
    with pytest.raises(ValidationError):
        AgentContract(tool_expectation=123)
    assert resolve_policy(mode="fast", agent_policy={"max_turns": 5}, run_config={"max_turns": 2}).max_turns == 2

    spec = ContractPolicySpec(name="spec", contract={"must_call": ["a"]}, policy={"max_tool_calls": 1}, tags=["t"], metadata={"m": 1})
    assert ContractPolicySpec.coerce(spec) is spec
    assert ContractPolicySpec.coerce({"name": "dict-spec"}).name == "dict-spec"
    assert spec.agent_kwargs()["contract"].must_call == ["a"]
    assert spec.describe()["name"] == "spec"
    assert spec.to_dict()["name"] == "spec"
    with pytest.raises(ValidationError):
        ContractPolicySpec(name=" ")

    ok = validate_contract_policy(
        AgentContract(must_call=["a"], tool_expectation={"all_of": ["a"], "exactly": ["a"], "min_count": 1, "any_of": ["a"]}),
        RunPolicy(max_tool_calls=1),
        available_tools={"a"},
    )
    assert ok.ok is True

    bad = validate_contract_policy(
        AgentContract(must_call=["missing"], must_not_call=["forbidden"], tool_expectation={"all_of": ["missing"], "min_count": 3}),
        RunPolicy(max_tool_calls=1),
        available_tools={"a"},
    )
    codes = {issue.code for issue in bad.issues}
    assert "contract_references_unknown_tool" in codes
    assert "policy_tool_budget_too_small" in codes
