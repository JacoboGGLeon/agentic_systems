
from __future__ import annotations

import asyncio
import json
import sys
from types import ModuleType

import pytest

import agentic_systems.cli as cli_module
import agentic_systems.integrations.langgraph as lg
from agentic_systems.errors import GraphContractError
from agentic_systems.results import RunResult


class FakeCompiled:
    def __init__(self, graph):
        self.graph = graph
        self.invocations = []

    def invoke(self, state):
        self.invocations.append(state)
        current = dict(state)
        for name, node in self.graph.nodes:
            update = node(current)
            if isinstance(update, dict):
                current.update(update)
        return current

    async def ainvoke(self, state):
        return self.invoke(state)


class FakeStateGraph:
    instances = []

    def __init__(self, state_schema):
        self.state_schema = state_schema
        self.nodes = []
        self.edges = []
        self.conditional = []
        FakeStateGraph.instances.append(self)

    def add_node(self, name, node):
        self.nodes.append((name, node))

    def add_edge(self, start, end):
        self.edges.append((start, end))

    def add_conditional_edges(self, *args):
        self.conditional.append(args)

    def compile(self, *args, **kwargs):
        return FakeCompiled(self)


def install_fake_langgraph(monkeypatch):
    module = ModuleType("langgraph.graph")
    module.StateGraph = FakeStateGraph
    module.START = "__start__"
    module.END = "__end__"
    monkeypatch.setitem(sys.modules, "langgraph.graph", module)
    return module


def test_cli_plain_and_json_paths(monkeypatch, capsys):
    monkeypatch.setattr(cli_module, "_load_dotenv", lambda: True)
    monkeypatch.setattr(cli_module, "_optional_dependency", lambda name: name != "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("AWS_REGION", "us-test-1")
    monkeypatch.setenv("AWS_PROFILE", "profile")

    assert cli_module.main(["version"]) == 0
    assert cli_module.__version__ in capsys.readouterr().out

    assert cli_module.main(["doctor"]) == 0
    doctor_plain = capsys.readouterr().out
    assert "Agentic Systems" in doctor_plain
    assert "OPENAI_API_KEY: set" in doctor_plain
    assert "openai: missing" in doctor_plain

    assert cli_module.main(["doctor", "--json"]) == 0
    doctor_json = json.loads(capsys.readouterr().out)
    assert doctor_json["dotenv_loaded"] is True
    assert doctor_json["environment"]["has_aws_profile"] is True

    class FakeRuntime:
        def describe(self):
            return {"selected_provider": "python-runtime", "mode": "explicit"}

    monkeypatch.setattr(cli_module, "runtime", lambda **kwargs: FakeRuntime())
    assert cli_module.main(["runtime", "--provider", "python-runtime"]) == 0
    runtime_plain = capsys.readouterr().out
    assert "Runtime Resolution" in runtime_plain
    assert "python-runtime" in runtime_plain
    assert cli_module.main(["runtime", "--provider", "python-runtime", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "explicit"

    assert cli_module.main(["public-api"]) == 0
    assert capsys.readouterr().out.strip()
    assert cli_module.main(["public-api", "--all", "--json"]) == 0
    assert isinstance(json.loads(capsys.readouterr().out), list)

    assert cli_module.main(["api", "--tier", "public", "--contains", "runtime"]) == 0
    api_plain = capsys.readouterr().out
    assert "tier: public" in api_plain
    assert "runtime" in api_plain.lower()
    assert cli_module.main(["api", "--tier", "recommended", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["tier"] == "recommended"


def test_langgraph_node_helpers_and_graph_app(monkeypatch):
    install_fake_langgraph(monkeypatch)
    assert lg._edge_endpoint("START", start="S", end="E") == "S"
    assert lg._edge_endpoint("END", start="S", end="E") == "E"
    assert lg._normalize_conditional_path_map(None, start="S", end="E") is None
    with pytest.raises(TypeError):
        lg._normalize_conditional_path_map([], start="S", end="E")
    with pytest.raises(ValueError):
        lg._validate_node_name(" ")
    with pytest.raises(GraphContractError):
        lg._read_state_input({}, "missing")

    result = RunResult(text="ok", data={"answer": "ok"}, meta={"input": "q"})
    assert lg._result_text(result) == "ok"
    mapped = lg._map_node_update(result, {"prompt": "q"}, output="answer", trace="trace", result_key="result")
    assert mapped["answer"] == "ok"
    assert mapped["result"]["normalized"]["answer"]["text"] == "ok"
    assert mapped["trace"]["text"] == "ok"
    with pytest.raises(TypeError):
        lg._map_node_update(result, {}, output=lambda result, state: "bad", trace=None, result_key=None)

    class Agent:
        name = "agent"
        def run(self, prompt, mode="default", config=None):
            return RunResult(text=f"sync:{prompt}", data={"prompt": prompt}, mode=mode)

        async def arun(self, prompt, mode="default", config=None):
            return RunResult(text=f"async:{prompt}", data={"prompt": prompt}, mode=mode)

    sync_node = lg.build_langgraph_agent_node(Agent(), output="text", result_key="result", trace="trace", mode="eval")
    assert sync_node({"prompt": "hello"})["text"] == "sync:hello"
    async_node = lg.build_langgraph_agent_node(Agent(), async_node=True, output="text")
    assert asyncio.run(async_node({"prompt": "hello"}))["text"] == "async:hello"

    class NodeFactoryAgent:
        def as_node(self, **kwargs):
            return lambda state: {"factory": kwargs["mode"]}
        def as_async_node(self, **kwargs):
            return lambda state: {"async_factory": kwargs["mode"]}

    assert lg.build_langgraph_agent_node(NodeFactoryAgent(), mode="factory")({}) == {"factory": "factory"}
    assert lg.build_langgraph_agent_node(NodeFactoryAgent(), async_node=True, mode="afactory")({}) == {"async_factory": "afactory"}
    with pytest.raises(TypeError):
        lg.build_langgraph_agent_node(object())
    with pytest.raises(TypeError):
        lg.build_langgraph_agent_node(object(), async_node=True)

    app = lg.graph(
        nodes={"n": lambda state: {"ran": True}},
        edges=[("START", "n"), ("n", "END")],
        conditional_edges=[("n", lambda state: "done", {"done": "END"})],
        name="demo",
    )
    assert app.run({"prompt": "x"})["ran"] is True
    assert app.invoke({"prompt": "x"})["ran"] is True
    assert asyncio.run(app.arun({"prompt": "x"}))["ran"] is True
    assert app.lineage({"answer": "ok"}).name == "demo"

    no_invoke = lg.GraphApp(native=object(), engine="langgraph")
    with pytest.raises(TypeError):
        no_invoke.run({})
    with pytest.raises(ValueError):
        lg.graph(engine="bad")
    with pytest.raises(TypeError):
        lg.graph(conditional_edges=[("n", "not-callable")])
    with pytest.raises(TypeError):
        lg.graph(conditional_edges=[("bad",)])


def test_langgraph_builders_and_agentic_graph(monkeypatch):
    install_fake_langgraph(monkeypatch)

    class Agent:
        name = "worker"
        def run(self, prompt, mode="default", config=None):
            return RunResult(text=f"done:{prompt}")

    native = lg.build_langgraph_agent_graph(Agent(), compile_graph=False)
    assert native.edges[0][0] == "__start__"
    compiled = lg.build_langgraph_agent_graph(Agent(), compile_graph=True)
    assert isinstance(compiled, FakeCompiled)

    class Planned:
        def invoke(self, state):
            return {"planned": state.get("x", 1)}

    planned_native = lg.build_langgraph_planned_graph(Planned(), compile_graph=False)
    assert planned_native.nodes[0][0] == "planned_step"
    planned_compiled = lg.build_langgraph_planned_graph(planned_graph=Planned(), compile_graph=True)
    assert planned_compiled.invoke({"x": 3})["planned"] == 3
    with pytest.raises(TypeError):
        lg.build_langgraph_planned_graph()
    with pytest.raises(TypeError):
        lg.build_langgraph_planned_graph(planned_graph=object())
    with pytest.raises(TypeError):
        lg.build_langgraph_planned_graph(planned_graph=Planned(), agents={"a": Agent()})
    with pytest.raises(TypeError):
        lg.build_langgraph_planned_graph(planned_graph=Planned(), x=1)

    builder = lg.AgenticGraph(state=dict, name="builder")
    assert builder.add_node("a", lambda state: {"a": True}) is builder
    assert builder.add_agent_node("agent", agent=Agent(), output="out") is builder
    assert builder.edge("START", "a") is builder
    assert builder.conditional_edges("a", lambda state: "END") is builder
    assert isinstance(builder.compile(), FakeCompiled)



def test_langgraph_lineage_projection_helpers_cover_business_shapes():
    assert lg._short_text("x" * 20, max_chars=8).endswith("...")
    assert lg._public_payload_summary({"a": 1, "_hidden": 2, "meta": {}, "b": None}) == "a: 1; b: None"
    assert lg._tool_output_payload({"output": {"data": {"result": 7}}}) == {"result": 7}
    facts = lg._tool_facts({"name": "query", "ok": True, "input": {"q": 1}, "output": {"rows": [{"a": 1}, {"a": 2}], "route": "sqlite"}})
    assert facts["tool"] == "query"
    assert facts["row_count"] == 2
    assert facts["sample_rows"] == [{"a": 1}, {"a": 2}]

    class Normalized:
        def normalized(self):
            return {"answer": {"text": "normalized"}}

    class TraceOnly:
        def trace(self, mode):
            assert mode == "compact"
            return {"answer": "trace"}

    class ToDictOnly:
        def to_dict(self):
            return {"answer": "dict"}

    class DumpOnly:
        def model_dump(self, mode="json"):
            return {"answer": "dump"}

    assert lg._mapping(Normalized())["answer"]["text"] == "normalized"
    assert lg._mapping(TraceOnly())["answer"] == "trace"
    assert lg._mapping(ToDictOnly())["answer"] == "dict"
    assert lg._mapping(DumpOnly())["answer"] == "dump"
    assert lg._mapping("scalar") == {"value": "scalar"}

    assert lg._answer_from_payload({"answer": {"data": {"summary": "nested summary"}}}) == "nested summary"
    assert lg._answer_from_payload({"answer": {"resultado": 42, "color": "azul"}}) == "resultado: 42; color: azul"
    assert lg._answer_from_payload({"value": 3}) == "value: 3"

    class ToolDump:
        def model_dump(self, mode="json"):
            return {"name": "dumped", "output": {"result": 1}}

    tools = lg._run_tools({"normalized": {"tools": [ToolDump()]}})
    assert tools[0]["name"] == "dumped"
    assert lg._run_tools({"blocks": {"tool_actions": [{"name": "block"}]}})[0]["name"] == "block"
    assert lg._tool_summary({"name": "direct", "summary": "done"}) == "done"
    assert lg._tool_summary({"name": "out", "output": {"error": "bad"}}) == "bad"
    assert lg._tool_summary({"name": "calc", "output": {"operation": "sum", "result": 3}}) == "calc: sum -> 3"
    assert lg._tool_summary({"name": "calc", "output": {"result": 3}}) == "calc: resultado 3"
    assert lg._tool_summary({"name": "classify", "output": {"number": 2, "text": "dos"}}) == "dos"
    assert "row(s)" in lg._tool_summary({"name": "rows", "output": {"row_count": 5}})
    assert lg._tool_summary({"name": "noop"}) == "noop executed."

    state = {
        "prompt": "Pregunta",
        "plan": {"route": "worker", "reason": "because"},
        "result": {"answer": {"data": {"summary": "answer from trace"}}, "validation": {"ok": False, "node": "worker"}},
        "worker_trace": {"tools": [{"name": "calc", "output": {"operation": "sum", "result": 42}}], "runtime": {"engine": "python-runtime"}, "ok": True},
        "graph_validation": {"ok": False, "node": "graph"},
    }
    memory = lg.lineage_from_langgraph_state(state, name="lg", goal="g", metadata={"m": 1})
    assert memory.name == "lg"
    assert memory.ok is False
    assert memory.metadata["m"] == 1
    assert any(step.kind == "tool" for step in memory.steps)
    assert any(step.kind == "validation" for step in memory.steps)

    memory_no_trace_validation = lg.lineage_from_langgraph_state({"user_prompt": "q", "graph_validation": {"ok": True}, "answer": {"summary": "ok"}})
    assert memory_no_trace_validation.ok is True
    assert any(step.step_id == "graph_validation" for step in memory_no_trace_validation.steps)

    with pytest.raises(TypeError):
        lg.lineage_from_langgraph_state("bad")
    assert lg.lineage_from_langgraph_result({"answer": "ok"}).answer == "ok"



def test_langgraph_last_residual_branches(monkeypatch):
    install_fake_langgraph(monkeypatch)

    class DumpScalar:
        def model_dump(self, mode="json"):
            return "scalar"

    class DictScalar:
        def to_dict(self):
            return "scalar"

    assert lg._json_result(DumpScalar()) == "scalar"
    assert lg._mapping(DumpScalar()) == {"value": "scalar"}
    assert lg._mapping(DictScalar()) == {"value": "scalar"}
    assert lg._run_tools({"tool_events": [{"name": "event"}]})[0]["name"] == "event"
    assert lg._answer_from_payload({"answer": {"data": {"error": "bad"}}}) == "bad"
    assert lg._tool_summary({"name": "nt", "output": {"number": 1}}) == "nt executed."

    trace_only = {"prompt": "q", "worker_trace": {"answer": "from trace"}}
    memory = lg.lineage_from_langgraph_state(trace_only)
    assert memory.answer == "from trace"

    plan_memory = lg.lineage_from_langgraph_state({"prompt": "q", "plan": {"reason": "only reason"}, "answer": "a"})
    assert any(step.summary == "only reason" for step in plan_memory.steps)

    class RunOnlyNative:
        def __init__(self):
            self.called = False
        def invoke(self, state):
            self.called = True
            return {"answer": "invoked"}

    app = lg.GraphApp(native=RunOnlyNative(), engine="langgraph", name="raw_app")
    assert asyncio.run(app.arun({"prompt": "x"}))["answer"] == "invoked"
    assert app.lineage("raw-state").answer == "invoked"

    app2 = lg.graph(nodes={"n": lambda state: {"ok": True}}, conditional_edges=[("n", lambda state: "END")])
    assert app2.run({})["ok"] is True

    class MiniAgent:
        def run(self, prompt, mode="default", config=None):
            return RunResult(text="ok")

    planned = lg.build_langgraph_planned_graph(agents={"a": MiniAgent()}, compile_graph=True)
    assert isinstance(planned, FakeCompiled)

    class BadPlanned:
        def invoke(self, state):
            return "bad"

    bad_graph = lg.build_langgraph_planned_graph(planned_graph=BadPlanned(), compile_graph=True)
    with pytest.raises(TypeError):
        bad_graph.invoke({})



def test_langgraph_final_small_residuals():
    class DumpWithNormalized:
        def model_dump(self, mode="json"):
            return {"raw": True}
        def normalized(self):
            return {"ok": True}

    assert lg._json_result(DumpWithNormalized())["normalized"] == {"ok": True}
    assert lg._json_result(object()).__class__ is object
    assert lg._tool_summary({"name": "nested", "output": {"data": {"number": 2, "text": "dos"}}}) == "nested: 2 -> dos"

    class Agent:
        def run(self, prompt, mode="default", config=None):
            return RunResult(text="ok")

    node = lg.agent_node(Agent(), output="text")
    assert node({"prompt": "q"})["text"] == "ok"
