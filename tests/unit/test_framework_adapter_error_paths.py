from __future__ import annotations

import asyncio
import builtins
import inspect
from types import SimpleNamespace
from typing import Literal

import pytest
from pydantic import BaseModel

from agentic_systems import Agent, RunPolicy, RunResult, tool as public_tool
from agentic_systems.integrations.adapters import langgraph as lg
from agentic_systems.integrations.adapters import openai_agents as oa
from agentic_systems.integrations.adapters import openai_models as om
from agentic_systems.integrations.adapters import strands as sa
from agentic_systems.integrations.adapters import strands_scripted as ss
from agentic_systems.integrations.boundary import (
    FrameworkProfile,
    evaluate_framework_projection,
)
from agentic_systems.integrations.config import FrameworkConfig
from agentic_systems.tools.toolkit import Toolkit
from agentic_systems.integrations.adapters.native import NativeFrameworkAdapter


def _block_import(monkeypatch, blocked: str) -> None:
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name == blocked or name.startswith(f"{blocked}."):
            raise ImportError(f"blocked {blocked}")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)


def _agent(engine: str = "python-runtime"):
    return SimpleNamespace(
        engine=engine,
        model="model",
        name="agent",
        instructions="instructions",
        system=SimpleNamespace(),
        runtime_config=SimpleNamespace(metadata={}, region_name=None),
        framework_config=SimpleNamespace(agent_kwargs={}, run_kwargs={}),
        available_tools=lambda: [],
        _native_agent=None,
    )


def test_missing_framework_extras_report_exact_install_commands(monkeypatch):
    _block_import(monkeypatch, "agents")
    with pytest.raises(ImportError, match=r"agentic-systems\[openai-agents\]"):
        oa.OpenAIAgentsFrameworkAdapter().prepare(_agent(), object())

    monkeypatch.undo()
    _block_import(monkeypatch, "strands")
    with pytest.raises(ImportError, match=r"agentic-systems\[strands\]"):
        sa.StrandsFrameworkAdapter().prepare(_agent(), object())

    monkeypatch.undo()
    _block_import(monkeypatch, "langgraph")
    with pytest.raises(ImportError, match=r"agentic-systems\[langgraph\]"):
        lg.LangGraphFrameworkAdapter().prepare(_agent(), object())


def test_openai_adapter_configuration_and_operational_errors(monkeypatch):
    adapter = oa.OpenAIAgentsFrameworkAdapter()
    agent = _agent()
    adapter.prepare = lambda agent, engine: SimpleNamespace(model=object())

    from agents import Runner

    monkeypatch.setattr(
        Runner,
        "run_sync",
        lambda *args, **kwargs: (_ for _ in ()).throw(TypeError("bad kwarg")),
    )
    with pytest.raises(TypeError, match="bad kwarg"):
        adapter.run(agent, object(), "x", RunPolicy(), mode="eval")

    monkeypatch.setattr(
        Runner,
        "run_sync",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert adapter.run(agent, object(), "x", RunPolicy(), mode="eval").ok is False

    async def invalid(*args, **kwargs):
        raise ValueError("bad async kwarg")

    monkeypatch.setattr(Runner, "run", invalid)
    with pytest.raises(ValueError, match="bad async kwarg"):
        asyncio.run(adapter.arun(agent, object(), "x", RunPolicy(), mode="eval"))

    async def failed(*args, **kwargs):
        raise RuntimeError("async offline")

    monkeypatch.setattr(Runner, "run", failed)
    assert (
        asyncio.run(adapter.arun(agent, object(), "x", RunPolicy(), mode="eval")).ok
        is False
    )

    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="VLLM_BASE_URL"):
        oa._materialize_model(_agent("vllm-runtime"), object())
    with pytest.raises(ValueError, match="Unsupported Provider"):
        oa._materialize_model(_agent("unknown"), object())


def test_openai_runner_import_errors_are_lazy(monkeypatch):
    adapter = oa.OpenAIAgentsFrameworkAdapter()
    _block_import(monkeypatch, "agents")
    with pytest.raises(ImportError, match=r"agentic-systems\[openai-agents\]"):
        adapter.run(_agent(), object(), "x", RunPolicy(), mode="eval")
    with pytest.raises(ImportError, match=r"agentic-systems\[openai-agents\]"):
        asyncio.run(adapter.arun(_agent(), object(), "x", RunPolicy(), mode="eval"))


def test_strands_adapter_configuration_and_operational_errors(monkeypatch):
    adapter = sa.StrandsFrameworkAdapter()
    agent = _agent()

    class Native:
        model = object()

        def __call__(self, *args, **kwargs):
            raise TypeError("bad kwarg")

        async def invoke_async(self, *args, **kwargs):
            raise ValueError("bad async kwarg")

    native = Native()
    adapter.prepare = lambda agent, engine: native
    with pytest.raises(TypeError, match="bad kwarg"):
        adapter.run(agent, object(), "x", RunPolicy(), mode="eval")
    with pytest.raises(ValueError, match="bad async kwarg"):
        asyncio.run(adapter.arun(agent, object(), "x", RunPolicy(), mode="eval"))

    native.__class__.__call__ = lambda self, *args, **kwargs: (_ for _ in ()).throw(
        RuntimeError("offline")
    )
    assert adapter.run(agent, object(), "x", RunPolicy(), mode="eval").ok is False

    async def failed(self, *args, **kwargs):
        raise RuntimeError("async offline")

    native.__class__.invoke_async = failed
    assert (
        asyncio.run(adapter.arun(agent, object(), "x", RunPolicy(), mode="eval")).ok
        is False
    )

    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="VLLM_BASE_URL"):
        sa._materialize_model(_agent("vllm-runtime"), object())
    with pytest.raises(ValueError, match="Unsupported Provider"):
        sa._materialize_model(_agent("unknown"), object())


class InputSchema(BaseModel):
    value: int


@public_tool(input=InputSchema)
def schema_backed_tool(payload: InputSchema) -> dict:
    return {"value": payload.value}


def test_strands_tool_executes_the_public_schema_instead_of_the_raw_signature():
    native_tool = sa._strands_tool(schema_backed_tool)

    assert inspect.signature(native_tool).parameters.keys() == {"value"}
    assert native_tool(value=7) == {"value": 7}


def test_model_tool_and_json_contracts():
    def function(value: int = 1):
        return value

    native_tool = sa._strands_tool(
        SimpleNamespace(
            name="schema_tool",
            function=function,
            description="",
            input_schema=InputSchema,
        )
    )
    assert native_tool.tool_name == "schema_tool"

    def typed_function(
        failed_criteria: list[Literal["clarity", "no_technical_noise"]],
        accepted: bool,
    ):
        return failed_criteria, accepted

    inferred = sa._tool_input_json_schema(
        SimpleNamespace(name="typed_tool", input_schema=None),
        typed_function,
    )
    assert inferred["additionalProperties"] is False
    assert inferred["properties"]["accepted"]["type"] == "boolean"
    assert inferred["properties"]["failed_criteria"]["type"] == "array"
    assert inferred["properties"]["failed_criteria"]["items"]["enum"] == [
        "clarity",
        "no_technical_noise",
    ]
    assert sa._jsonable(3) == 3
    assert oa._output_data({"value": 1}, "ignored") == {"value": 1}
    assert (
        om._plan_calls(
            {"tool": "lookup", "input": {}}, [SimpleNamespace(name="lookup")]
        )[0]["tool"]
        == "lookup"
    )
    assert ss._plan_calls("raw", [{"name": "lookup"}]) == [
        {"tool": "lookup", "input": {"input": "raw"}}
    ]

    from agentic_systems.integrations.adapters import bedrock_openai as bo

    assert bo._content_text(3) == "3"


def test_native_async_falls_back_to_worker_thread():
    result = RunResult(text="ok", engine="python-runtime", model="model")
    engine = SimpleNamespace(run=lambda *args, **kwargs: result)
    agent = SimpleNamespace(_native_agent=None)
    actual = asyncio.run(
        NativeFrameworkAdapter().arun(
            agent,
            engine,
            "input",
            RunPolicy(),
            mode="eval",
        )
    )
    assert actual is result
    assert actual.native_result is result


def test_strands_openai_key_is_forwarded_without_logging_values(monkeypatch):
    captured = {}
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "strands.models.openai.OpenAIModel",
        lambda **kwargs: captured.update(kwargs) or object(),
    )
    model = sa._materialize_model(_agent("openai-runtime"), object())
    assert model is not None
    assert captured == {
        "model_id": "model",
        "client_args": {"api_key": "test-key"},
    }


def test_agent_rejects_unknown_framework_and_direct_cloud_execution():
    with pytest.raises(ValueError, match="Unknown framework"):
        Agent(name="bad", framework="unknown", engine="python-runtime")
    agent = Agent(name="cloud", engine="openai-runtime")
    with pytest.raises(RuntimeError, match="Bind the agent"):
        agent.prepare()


def test_direct_python_prepare_materializes_the_canonical_engine():
    agent = Agent(name="direct", engine="python-runtime")
    assert agent.prepare().native_agent.__class__.__name__ == "PythonRuntimeEngine"


def test_framework_config_boundary_and_toolkit_contracts():
    config = FrameworkConfig(agent_kwargs=None, run_kwargs=None)
    assert config.to_dict()["name"] == "native"
    assert config is FrameworkConfig.coerce(config)

    toolkit = Toolkit(SimpleNamespace(), "ops")
    assert repr(toolkit) == "Toolkit(name='ops', tools=[])"

    profile = FrameworkProfile(
        framework="missing",
        integration_kind="native-adapter",
        adapter_module=None,
        native_object_access=False,
        detail="adapter unavailable",
    )
    report = evaluate_framework_projection(
        profile,
        source_result=RunResult(text="x"),
        projected_state={},
        result_key="result",
    )
    assert report.ok is False
