import asyncio
import builtins
import dataclasses
import os
import sys
import types
from pathlib import Path
from typing import Any, Dict
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from agentic_systems import (
    AgentContract,
    AgenticSystem,
    RunPolicy,
    RunResult,
)
from agentic_systems.agents import Agent, _coerce_input, _coerce_output_data, _try_parse_json_object
from agentic_systems.contracts import ValidationResult
from agentic_systems.engines.bedrock import _input_to_prompt
from agentic_systems.evals import run_eval
from agentic_systems.integrations.langgraph import AgenticGraph
from agentic_systems.results import _contains_subset
from agentic_systems.providers.base import ToolRegistryRuntime
from agentic_systems.providers.openai_runtime import OpenAIRuntimeProvider
from agentic_systems.skills import load_skill
from agentic_systems.system import InspectReport, _return_annotation_is_dict
from agentic_systems.tools.compat import Toolkit, assert_dict_tool_output, expand_tool_inputs, now_ms
from tests.api._controlled_bedrock_runtime import ControlledBedrockRuntime, attach_controlled_runtime
from agentic_systems.utils import _discover_repo_root, _to_jsonable, configure_notebook_environment, show_json


def build_system(strict=True, defaults=None):
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(model="demo-model", region="us-east-1", strict=strict, defaults=defaults)
from agentic_systems.tools.compat import ToolEvent


class EchoEngine:
    name = "bedrock"

    def run(self, agent, input, policy, *, mode="default"):
        if isinstance(input, BaseModel):
            payload = input.model_dump(mode="json")
        else:
            payload = input if isinstance(input, dict) else {"input": input}
        text = payload.get("text") or payload.get("input") or "ok"
        data = payload.get("data") or {"answer": str(text), "score": 1}
        return RunResult(text=str(text), data=data, ok=True, engine=self.name, model=agent.model, mode=mode)

    async def arun(self, agent, input, policy, *, mode="default"):
        return self.run(agent, input, policy, mode=mode)


class InputModel(BaseModel):
    input: str


class OutputModel(BaseModel):
    answer: str
    score: int = 1


def test_agent_input_output_coercion_helpers_cover_all_paths():
    model = InputModel(input="ready")
    assert _coerce_input("raw", None) == "raw"
    assert _coerce_input(model, InputModel) is model
    assert _coerce_input({"input": "dict"}, InputModel).input == "dict"
    assert _coerce_input("scalar", InputModel).input == "scalar"

    assert _try_parse_json_object("not json") == {"text": "not json"}
    assert _try_parse_json_object('["a"]') == {"value": ["a"]}
    assert _try_parse_json_object('{"answer":"yes"}') == {"answer": "yes"}

    result = RunResult(text='{"answer":"yes","score":2}')
    coerced = _coerce_output_data(result, OutputModel)
    assert coerced.data == {"answer": "yes", "score": 2}
    same = RunResult(text="x", data={"answer": "data", "score": 3})
    assert _coerce_output_data(same, OutputModel).data["answer"] == "data"
    untouched = RunResult(text="x")
    assert _coerce_output_data(untouched, None) is untouched


def test_agent_runtime_paths_as_node_as_tool_eval_and_loop_error():
    system = build_system()
    system._engines["bedrock"] = EchoEngine()
    agent = system.agent(name="echo", instructions="echo", input=InputModel, output=OutputModel)

    result = agent.run_sync("hello", mode="eval", config={"max_tokens": 10})
    assert result.data == {"answer": "hello", "score": 1}
    assert asyncio.run(agent.arun("async hello", mode="eval")).data["answer"] == "async hello"

    async def call_run_sync_inside_loop():
        assert agent.run_sync("loop-safe").text == "loop-safe"
        async_node = agent.as_async_node(input=lambda state: state["value"], output="answer")
        assert (await async_node({"value": "async node"}))["answer"] == "async node"

    asyncio.run(call_run_sync_inside_loop())

    missing_node = agent.as_node(input="missing")
    with pytest.raises(Exception, match="input key 'missing'"):
        missing_node({"prompt": "x"})

    callable_node = agent.as_node(
        input=lambda state: {"input": state["value"]},
        output=lambda run_result, state: {"custom": run_result.data["answer"], "kept": state["keep"]},
        trace=None,
    )
    assert callable_node({"value": "via callable", "keep": 7}) == {"custom": "via callable", "kept": 7}

    empty_update_node = agent.as_node(input=lambda state: "empty", output=None, trace=None)
    assert empty_update_node({}) == {}

    tool = agent.as_tool(name="tools.echo", description="Run echo")
    assert tool.__name__ == "tools_echo"
    assert tool.__doc__ == "Run echo"
    assert tool("from tool")["data"]["answer"] == "from tool"

    report = agent.eval([{"input": "case", "expected": {"text_contains": "case"}}])
    assert report.ok is True


def test_agent_validation_error_paths_direct_construction():
    system = build_system()
    with pytest.raises(ValueError, match="unknown_agent_tool"):
        Agent(system=system, name="bad", instructions="x", tools=("missing",))
    with pytest.raises(ValueError, match="contract_references_unknown_tool"):
        Agent(system=system, name="bad_contract", instructions="x", tools=(), contract={"must_call": ["missing"]})
    with pytest.raises(ValueError, match="langgraph_is_not_engine"):
        Agent(system=system, name="bad_engine", instructions="x", tools=(), engine="langgraph")

    openai_agent = Agent(system=system, name="openai_bridge", instructions="x", tools=(), engine="openai-runtime", framework="openai-agents")
    assert openai_agent.engine == "openai-runtime"
    assert openai_agent.framework == "openai-agents"
    with pytest.raises(ValueError, match="openai-agents"):
        Agent(system=system, name="bad_framework", instructions="x", tools=(), engine="openai-runtime", framework="openai-runtime")


def test_contract_policy_and_validation_error_paths():
    validation = ValidationResult(ok=True)
    validation.add("warn", "warning only", severity="warning")
    assert validation.ok is True
    validation.add("err", "error")
    with pytest.raises(ValueError, match="Validation failed"):
        validation.raise_if_failed()

    assert AgentContract(failure_policy=None).failure_policy == "no_unresolved"
    assert AgentContract(failure_policy=True).failure_policy == "no_unresolved"
    assert AgentContract(failure_policy=False).failure_policy == "allow"
    assert AgentContract(require_no_unresolved_tool_failures=False).failure_policy == "allow"
    allow = AgentContract(failure_policy="allow")
    assert allow.require_no_unresolved_tool_failures is False

    with pytest.raises(ValueError, match="Unknown run mode"):
        RunPolicy.for_mode("unknown")
    merged = RunPolicy(max_turns=1).merge(RunPolicy(max_tokens=33))
    assert merged.max_turns == 1 and merged.max_tokens == 33


def test_result_trace_validate_and_subset_paths():
    assert _contains_subset({"a": {"b": 2}}, {"a": {"b": 2}}) is True
    assert _contains_subset("not a dict", {"a": 1}) is False
    assert _contains_subset({"a": 1}, {"b": 1}) is False
    assert _contains_subset("hello world", "world") is True
    assert _contains_subset([{"x": 1}, {"x": 2}], [{"x": 2}]) is True
    assert _contains_subset({"x": 1}, [{"x": 1}]) is False
    assert _contains_subset([1], [2]) is False

    fail = ToolEvent(id="f1", name="lookup", ok=False, error={"message": "fail"})
    ok = ToolEvent(id="s1", name="lookup", ok=True, output={"data": {"id": 1, "name": "ok"}})
    forbidden = ToolEvent(id="x1", name="delete", ok=True, output={"data": {"id": 9}})
    result = RunResult(text="done", data={"status": "done"}, tool_events=[fail, ok, forbidden], raw_responses=[{"usage": {"inputTokens": 1, "output_tokens": 2, "totalTokens": 3}}])

    assert result.to_dict()["text"] == "done"
    assert result.compact_trace()["recovered_tool_error_count"] == 1
    assert result.trace("full")["compact"]["tool_event_count"] == 3
    with pytest.raises(ValueError, match="compact"):
        result.trace("bad")

    validation = result.validate(
        {
            "must_call": ["lookup"],
            "must_not_call": ["delete"],
            "output_contains": {"status": "missing"},
            "expected_tool_outputs": {
                "missing_tool": {"id": 1},
                "lookup": {"name": "missing"},
            },
        }
    )
    codes = {issue.code for issue in validation.issues}
    assert {"forbidden_tool_called", "expected_output_mismatch", "expected_tool_output_missing_tool", "expected_tool_output_mismatch"} <= codes

    unresolved = RunResult(text="bad", tool_events=[ToolEvent(id="u1", name="u", ok=False, error={"e": "x"})])
    assert unresolved.trace()["unresolved_failed_tool_count"] == 1
    assert "unresolved_tool_failure" in {issue.code for issue in unresolved.validate().issues}


def test_run_result_from_bedrock_runtime_dict_and_usage_aliases():
    raw = {
        "final_text": "ok",
        "messages": [{"role": "assistant"}],
        "tool_calls": [{"tool_use_id": "1", "tool_name": "t", "tool_input": {}, "tool_output": {"data": {"x": 1}}, "ok": True}],
        "raw_responses": [{"usage": {"input_tokens": 2, "outputTokens": 3, "totalTokens": 5}}],
    }
    result = RunResult.from_bedrock_runtime(raw, engine="bedrock", model="m")
    assert result.usage == {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5, "requests": 1}


def test_tool_event_non_dict_error_data_path():
    event = ToolEvent.from_runtime_record({
        "tool_use_id": "e1",
        "tool_name": "broken",
        "tool_input": {},
        "tool_output": {"data": "plain error"},
        "ok": False,
    })
    assert event.error == {"message": "plain error"}


def test_tools_and_toolkit_all_public_branches():
    class Model(BaseModel):
        value: int

    for value, fix in [
        ([1], "items"),
        ("x", "text"),
        (None, "ok"),
        (Model(value=1), "model_dump"),
        (3.14, "value"),
    ]:
        with pytest.raises(TypeError, match=fix):
            assert_dict_tool_output("sample", value)

    system = build_system(strict=False)
    with pytest.raises(ValueError, match="non-empty"):
        Toolkit(system, " ")

    toolkit = system.toolkit("demo")

    @toolkit.tool
    def one() -> list:
        """Strict false allows runtime values through."""
        return [1]

    def dotted() -> dict:
        """Already namespaced."""
        return {"ok": True}

    toolkit.add(dotted, name="external.dotted")
    assert len(toolkit) == 2
    assert list(iter(toolkit)) == ["demo.one", "external.dotted"]
    assert toolkit.ref().name == "demo"
    assert expand_tool_inputs(None) == ()
    assert expand_tool_inputs(toolkit) == toolkit.tool_names
    assert expand_tool_inputs("demo.one") == ("demo.one",)
    assert expand_tool_inputs([toolkit, "demo.one"]).count("demo.one") == 2
    with pytest.raises(TypeError, match="Unsupported tools"):
        expand_tool_inputs(123)
    assert now_ms() > 0


def test_system_public_branches_and_helpers(monkeypatch):
    system = build_system(strict=False, defaults={"max_tokens": None, "temperature": None})

    @system.tool(name="loose")
    def loose() -> list:
        """Loose mode tool."""
        return [1]

    assert system.execute_tool("loose", {}).data == {"items": [1]}
    assert system.skills == ()
    assert system.toolkit("same") is system.toolkit("same")
    assert system.export_tool_specs(["loose"])[0]["name"] == "loose"

    with pytest.raises(ValueError, match="LangGraph"):
        system.agent(name="g", instructions="x", engine="langgraph")
    with pytest.raises(KeyError, match="Unknown tools"):
        system.agent(name="missing", instructions="x", tools=["missing"])
    with pytest.raises(ValueError, match="Unknown runtime/provider"):
        system._engine("unknown")
    assert isinstance(system._engine("openai-runtime"), OpenAIRuntimeProvider)

    assert InspectReport(ok=True).raise_if_errors()["ok"] is True

    bad = InspectReport(ok=False, errors=[{"x": 1}])
    with pytest.raises(ValueError, match="inspect failed"):
        bad.raise_if_errors()

    def no_return(a: int):
        return {"a": a}

    def old_style() -> Dict[str, Any]:
        return {"ok": True}

    def broken_annotation() -> "MissingType":
        return {"ok": True}

    assert _return_annotation_is_dict(no_return) is False
    assert _return_annotation_is_dict(old_style) is True
    assert _return_annotation_is_dict(broken_annotation) is False

    # inspect warnings from runtime registry and errors from strict return validation
    strict_system = build_system(strict=True)

    @strict_system.tool
    def valid_tool() -> dict:
        """Valid tool."""
        return {"ok": True}

    def no_return_for_spec():
        return {"ok": True}

    spec = strict_system._runtime._tools["valid_tool"]
    strict_system._runtime._tools["valid_tool"] = dataclasses.replace(spec, func=no_return_for_spec)
    report = strict_system.inspect()
    assert report["ok"] is False
    assert report["errors"][0]["issue"] == "tool_return_annotation_must_be_dict"

    warning_system = build_system(strict=False)

    @warning_system.tool(name="warn_tool", description=" ")
    def warn_tool() -> dict:
        return {"ok": True}

    warning_report = warning_system.inspect()
    assert warning_report["warnings"][0]["source"] == "runtime_registry"

    class WarningAgent:
        name = "warning_agent"

        def validate(self):
            result = ValidationResult(ok=True)
            result.add("agent_warning", "only warning", severity="warning")
            return result

    warning_system._agents.append(WarningAgent())
    assert any(issue.get("code") == "agent_warning" for issue in warning_system.inspect()["warnings"])


def test_bedrock_input_prompt_all_branches():
    class Dumpable(BaseModel):
        value: int

    class NotJson:
        def __str__(self):
            return "not-json"

    assert _input_to_prompt(None) == ""
    assert _input_to_prompt("hello") == "hello"
    assert '"value": 1' in _input_to_prompt(Dumpable(value=1))
    assert _input_to_prompt({"x": {1, 2}}) == "{'x': {1, 2}}"
    assert _input_to_prompt(NotJson()) == "not-json"


def test_openai_runtime_provider_with_fake_runtime():
    runtime = ToolRegistryRuntime(model_id="model-x")

    @runtime.tool(name="t", description="Echo tool")
    def t(x: int) -> dict[str, int]:
        return {"result": x + 1}

    class FakeResponse:
        def __init__(self, choices):
            self.choices = choices
            self.usage = SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15)

    class FakeMessage:
        def __init__(self, content="", tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls or []

    class FakeToolCall:
        def __init__(self, call_id, name, arguments):
            self.id = call_id
            self.function = SimpleNamespace(name=name, arguments=arguments)

    class FakeClient:
        def __init__(self):
            self.calls = 0
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                tool_call = FakeToolCall("call_1", "t", "{\"x\": 41}")
                return FakeResponse([SimpleNamespace(message=FakeMessage(tool_calls=[tool_call]))])
            return FakeResponse([SimpleNamespace(message=FakeMessage(content="openai final"))])

    class FakeAsyncClient:
        def __init__(self, sync_client):
            self.sync_client = sync_client
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        async def create(self, **kwargs):
            return self.sync_client.create(**kwargs)

    fake_system = SimpleNamespace(_runtime=runtime, model="model-x")
    agent = SimpleNamespace(name="oa", instructions="inst", tools=("t",), model=None, contract=AgentContract(), system=fake_system, framework="openai-agents")
    client = FakeClient()
    engine = OpenAIRuntimeProvider(fake_system, client=client, async_client=FakeAsyncClient(client))
    result = engine.run(agent, {"x": 1}, RunPolicy(), mode="audit")
    assert result.text == "openai final"
    assert result.engine == "openai-runtime"
    assert result.meta["framework"] == "openai-agents"
    assert result.meta["execution_engine"] == "openai-runtime"
    assert result.tool_events[0].name == "t"
    assert result.tool_events[0].output["result"] == 42
    async_result = asyncio.run(engine.arun(agent, {"x": 2}, RunPolicy(), mode="audit"))
    assert async_result.text == "openai final"


class FakeStateGraph:
    def __init__(self, state):
        self.state = state
        self.calls = []

    def add_node(self, *args):
        self.calls.append(("node", args))

    def add_edge(self, *args):
        self.calls.append(("edge", args))

    def add_conditional_edges(self, *args, **kwargs):
        self.calls.append(("conditional", args, kwargs))

    def compile(self, *args, **kwargs):
        return {"compiled": True, "calls": self.calls, "args": args, "kwargs": kwargs}


class FakeAgentForGraph:
    def as_node(self, **kwargs):
        return ("agent_node", kwargs)


def install_fake_langgraph(monkeypatch):
    package = types.ModuleType("langgraph")
    graph_module = types.ModuleType("langgraph.graph")
    graph_module.StateGraph = FakeStateGraph
    monkeypatch.setitem(sys.modules, "langgraph", package)
    monkeypatch.setitem(sys.modules, "langgraph.graph", graph_module)


def test_agentic_graph_success_and_import_error(monkeypatch):
    install_fake_langgraph(monkeypatch)
    graph = AgenticGraph(name="flow", state=dict)
    system_graph = build_system().graph(name="system_flow")
    assert isinstance(system_graph.native, FakeStateGraph)
    assert isinstance(graph.native, FakeStateGraph)
    assert graph.add_agent_node("agent", agent=FakeAgentForGraph(), input="request") is graph
    assert graph.add_node("raw", lambda state: state) is graph
    assert graph.edge("a", "b") is graph
    assert graph.conditional_edges("a", lambda state: "b") is graph
    compiled = graph.compile(debug=True)
    assert compiled["compiled"] is True

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "langgraph.graph":
            raise ImportError("no langgraph")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match="optional 'langgraph'"):
        AgenticGraph(name="missing")


def test_eval_report_pass_and_fail_paths():
    class EvalAgent:
        def __init__(self, result):
            self.result = result

        def run_sync(self, input, mode="eval", config=None):
            return self.result

    passing = run_eval(EvalAgent(RunResult(text="hello world", data={"risk": "low"})), [
        {"name": "ok", "input": {"x": 1}, "expected": {"text_contains": "world", "data_contains": {"risk": "low"}, "must_call": [], "expected_tool_outputs": {}}}
    ])
    assert passing.to_dict()["passed"] == 1
    assert passing.raise_if_failed() is passing

    failing = run_eval(EvalAgent(RunResult(text="nope", data={"risk": "high"})), [
        {"input": "x", "expected": {"text_contains": "missing", "data_contains": {"risk": "low"}}}
    ])
    assert failing.ok is False
    with pytest.raises(AssertionError, match="case_1"):
        failing.raise_if_failed()


def test_skill_loader_error_paths(tmp_path, monkeypatch):
    system = build_system()
    with pytest.raises(Exception, match="does not exist"):
        load_skill(system, tmp_path / "missing")

    no_md = tmp_path / "no_md"
    no_md.mkdir()
    with pytest.raises(Exception, match="missing SKILL.md"):
        load_skill(system, no_md)

    no_py = tmp_path / "no_py"
    no_py.mkdir()
    (no_py / "SKILL.md").write_text("# Title\n", encoding="utf-8")
    with pytest.raises(Exception, match="missing skill.py"):
        load_skill(system, no_py)

    no_register = tmp_path / "no_register"
    no_register.mkdir()
    (no_register / "SKILL.md").write_text("# Title\n", encoding="utf-8")
    (no_register / "skill.py").write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(Exception, match="register"):
        load_skill(system, no_register)

    none_register = tmp_path / "none_register"
    none_register.mkdir()
    (none_register / "SKILL.md").write_text("\n", encoding="utf-8")
    (none_register / "skill.py").write_text("def register(system):\n    return None\n", encoding="utf-8")
    loaded = load_skill(system, none_register)
    assert loaded.manifest.description == ""

    bad_return = tmp_path / "bad_return"
    bad_return.mkdir()
    (bad_return / "SKILL.md").write_text("# Bad\n", encoding="utf-8")
    (bad_return / "skill.py").write_text("def register(system):\n    return []\n", encoding="utf-8")
    with pytest.raises(Exception, match="must return a dict"):
        load_skill(system, bad_return)

    spec_none = tmp_path / "spec_none"
    spec_none.mkdir()
    (spec_none / "SKILL.md").write_text("# Spec none\n", encoding="utf-8")
    (spec_none / "skill.py").write_text("def register(system):\n    return {}\n", encoding="utf-8")
    monkeypatch.setattr("agentic_systems.skills.importlib.util.spec_from_file_location", lambda *a, **k: None)
    with pytest.raises(Exception, match="Cannot import"):
        load_skill(system, spec_none)


def test_notebook_utils_show_json_environment_and_controlled_runtime(tmp_path, capsys, monkeypatch):
    repo = tmp_path / "repo"
    src = repo / "src"
    tutorials = repo / "tutorials"
    src.mkdir(parents=True)
    tutorials.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    root = configure_notebook_environment(repo)
    assert root == repo
    assert str(src) in sys.path
    assert os.environ.get("AWS_ACCESS_KEY_ID") != "test"
    assert os.environ.get("AWS_SECRET_ACCESS_KEY") != "test"

    assert _discover_repo_root(tutorials) == repo
    assert _discover_repo_root(src) == repo
    orphan = tmp_path / "orphan"
    orphan.mkdir()
    assert _discover_repo_root(orphan) == orphan

    result = RunResult(text="ok", data={"nested": [1]})
    assert _to_jsonable(result)["text"] == "ok"
    assert _to_jsonable({"r": result})["r"]["data"] == {"nested": [1]}
    assert _to_jsonable((result,))[0]["text"] == "ok"

    class Dictable:
        def to_dict(self):
            return {"kind": "dictable"}

    assert _to_jsonable(Dictable()) == {"kind": "dictable"}
    assert _to_jsonable("plain") == "plain"

    show_json(result, title="Result")
    output = capsys.readouterr().out
    assert "=== Result ===" in output
    assert '"text": "ok"' in output

    runtime = ControlledBedrockRuntime(tool_name="lookup", tool_input={"id": "1"})
    tool_response = runtime.converse(toolConfig={"tools": []}, messages=[])
    assert tool_response["stopReason"] == "tool_use"
    assert tool_response["output"]["message"]["content"][0]["toolUse"]["name"] == "lookup"

    final_response = runtime.converse(messages=[{"role": "user", "content": [{"toolResult": {"toolUseId": "1"}}]}])
    assert final_response["stopReason"] == "end_turn"
    assert final_response["output"]["message"]["content"][0]["text"] == runtime.final_text

    synthesis_response = runtime.converse(
        toolConfig={"tools": []},
        messages=[{"role": "user", "content": [{"text": "BedrockRuntime final synthesis instruction"}]}],
    )
    assert synthesis_response["stopReason"] == "end_turn"

    system = build_system()
    attached = attach_controlled_runtime(system, runtime)
    assert attached is runtime
    assert system._runtime.runtime is runtime
    default_attached = attach_controlled_runtime(system)
    assert isinstance(default_attached, ControlledBedrockRuntime)

    mapped = ControlledBedrockRuntime(tool_input_mapper=lambda kwargs: {"id": kwargs.get("id", "x")})
    assert mapped._resolve_tool_input({"id": "mapped"}) == {"id": "mapped"}
    scalar_mapped = ControlledBedrockRuntime(tool_input_mapper=lambda kwargs: "scalar")
    assert scalar_mapped._resolve_tool_input({}) == {"value": "scalar"}


def test_agent_sync_run_inside_loop_reraises_engine_error():
    class BrokenEngine:
        def run(self, agent, input, policy, *, mode="default"):
            raise RuntimeError("controlled sync failure")

    system = build_system()
    system._engines["bedrock"] = BrokenEngine()
    agent = system.agent(name="broken", instructions="fail")

    async def call_inside_loop():
        with pytest.raises(RuntimeError, match="controlled sync failure"):
            agent.run("x")

    asyncio.run(call_inside_loop())


def test_bedrock_engine_arun_openai_prompt_and_async_environment_branches():
    class RuntimeForBedrock:
        region_name = "us-east-1"

        def run_direct(self, prompt, **kwargs):
            return {"final_text": f"bedrock:{prompt}", "tool_calls": [], "raw_responses": []}

    fake_system = SimpleNamespace(_runtime=RuntimeForBedrock(), model="model-x")
    agent = SimpleNamespace(instructions="inst", tools=(), model=None, contract=AgentContract())
    from agentic_systems.engines.bedrock import BedrockEngine

    arun_result = asyncio.run(BedrockEngine(fake_system).arun(agent, "async", RunPolicy(), mode="debug"))
    assert arun_result.text == "bedrock:async"
    assert arun_result.mode == "debug"

    from agentic_systems.providers.openai_runtime import _input_to_prompt as openai_input_to_prompt

    assert openai_input_to_prompt("already text") == "already text"

    from agentic_systems import AgenticEnvironment

    class AsyncGraph:
        async def ainvoke(self, state):
            return {**state, "async": True}

    env = AgenticEnvironment(records=[{"case_id": "a"}], graph=AsyncGraph())
    env.reset(seed=11)
    observation, reward, terminated, truncated, info = asyncio.run(env.astep())
    assert observation is None
    assert terminated is True and truncated is False
    assert info["graph_state"]["async"] is True

    class SyncGraphOnly:
        def invoke(self, state):
            return "sync-output"

    env = AgenticEnvironment(records=[{"case_id": "b"}], graph=SyncGraphOnly())
    env.reset(seed=12)
    *_, info = asyncio.run(env.astep())
    assert info["graph_state"] == {"output": "sync-output"}

    class NoInvokeAsync:
        pass

    env = AgenticEnvironment(records=[{"case_id": "c"}], graph=NoInvokeAsync())
    env.reset(seed=13)
    with pytest.raises(TypeError, match="ainvoke"):
        asyncio.run(env.astep())
