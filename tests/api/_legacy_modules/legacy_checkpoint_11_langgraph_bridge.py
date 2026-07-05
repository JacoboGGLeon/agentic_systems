from __future__ import annotations

import builtins
import sys
import types

import pytest

from agentic_systems import (
    Agent,
    AgenticGraph,
    build_langgraph_agent_graph,
    build_langgraph_agent_node,
    build_langgraph_planned_graph,
    build_planned_agent_graph,
    tool,
)
from agentic_systems.integrations import langgraph as langgraph_bridge
from agentic_systems.errors import GraphContractError


class FakeCompiledGraph:
    def __init__(self, nodes, edges, conditional=None):
        self.nodes = nodes
        self.edges = edges
        self.conditional = conditional or []

    def invoke(self, state):
        merged = dict(state)
        for _name, node in self.nodes:
            update = node(merged)
            if not isinstance(update, dict):
                raise TypeError("fake node must return dict")
            merged.update(update)
        return merged


class FakeStateGraph:
    def __init__(self, state_schema):
        self.state_schema = state_schema
        self.nodes = []
        self.edges = []
        self.conditional = []

    def add_node(self, name, node):
        self.nodes.append((name, node))

    def add_edge(self, start, end):
        self.edges.append((start, end))

    def add_conditional_edges(self, *args, **kwargs):
        self.conditional.append((args, kwargs))

    def compile(self, *args, **kwargs):
        return FakeCompiledGraph(self.nodes, self.edges, self.conditional)


def install_fake_langgraph(monkeypatch):
    package = types.ModuleType("langgraph")
    graph_module = types.ModuleType("langgraph.graph")
    graph_module.START = "__start__"
    graph_module.END = "__end__"
    graph_module.StateGraph = FakeStateGraph
    monkeypatch.setitem(sys.modules, "langgraph", package)
    monkeypatch.setitem(sys.modules, "langgraph.graph", graph_module)


@tool
def join_values(prefix: str, value: int) -> dict:
    """Join a text prefix and a numeric value."""

    return {"result": f"{prefix}-{value}"}


def build_direct_agent() -> Agent:
    return Agent(name="generic_local_agent", tools=[join_values], engine="python-direct")


def test_bridge_import_does_not_import_langgraph(monkeypatch):
    monkeypatch.delitem(sys.modules, "langgraph", raising=False)
    monkeypatch.delitem(sys.modules, "langgraph.graph", raising=False)

    import agentic_systems
    import agentic_systems.integrations.langgraph as bridge_module

    assert agentic_systems.AgenticGraph is AgenticGraph
    assert bridge_module.build_langgraph_agent_node is build_langgraph_agent_node
    assert "langgraph.graph" not in sys.modules


def test_bridge_raises_helpful_error_only_when_native_graph_is_requested(monkeypatch):
    monkeypatch.delitem(sys.modules, "langgraph", raising=False)
    monkeypatch.delitem(sys.modules, "langgraph.graph", raising=False)
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "langgraph.graph":
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match="optional 'langgraph'"):
        AgenticGraph(name="requires_native_graph")


def test_build_langgraph_agent_node_maps_generic_state_and_result():
    agent = build_direct_agent()
    node = build_langgraph_agent_node(
        agent,
        input=lambda state: {"tool": "join_values", "input": {"prefix": state["prefix"], "value": state["value"]}},
        output=lambda result, state: {"joined": result.data["result"], "source": state["source"]},
        trace="trace",
        result_key="raw_result",
        mode="eval",
    )

    update = node({"prefix": "case", "value": 7, "source": "unit-test"})

    assert update["joined"] == "case-7"
    assert update["source"] == "unit-test"
    assert update["raw_result"]["data"]["result"] == "case-7"
    assert update["trace"]["engine"] == "python-direct"


def test_build_langgraph_agent_node_validates_contracts():
    agent = build_direct_agent()
    node = build_langgraph_agent_node(agent, input="missing")
    with pytest.raises(GraphContractError, match="input key 'missing'"):
        node({"prompt": "x"})

    bad_output = build_langgraph_agent_node(agent, input=lambda _state: {"tool": "join_values", "input": {"prefix": "x", "value": 1}}, output=lambda *_: "not a dict")
    with pytest.raises(TypeError, match="output mapper"):
        bad_output({})


def test_graph_helper_supports_conditional_edges(monkeypatch):
    install_fake_langgraph(monkeypatch)

    def router(state):
        return state["route"]

    app = langgraph_bridge.graph(
        name="router",
        nodes={"orchestrator": lambda state: {"route": "worker"}, "worker": lambda state: {"done": True}},
        edges=[("START", "orchestrator"), ("worker", "END")],
        conditional_edges=[("orchestrator", router, {"worker": "worker", "stop": "END"})],
    )

    assert app.native.edges == [("__start__", "orchestrator"), ("worker", "__end__")]
    args, kwargs = app.native.conditional[0]
    assert args[0] == "orchestrator"
    assert args[1] is router
    assert args[2] == {"worker": "worker", "stop": "__end__"}
    assert kwargs == {}


def test_build_langgraph_agent_graph_compiles_native_graph(monkeypatch):
    install_fake_langgraph(monkeypatch)
    agent = build_direct_agent()

    app = build_langgraph_agent_graph(
        agent,
        node_name="generic_step",
        input=lambda state: {"tool": "join_values", "input": {"prefix": state["prefix"], "value": state["value"]}},
        output=lambda result, _state: {"answer": result.data["result"]},
        result_key="result",
        trace=None,
    )

    state = app.invoke({"prefix": "alpha", "value": 3})
    assert state["answer"] == "alpha-3"
    assert state["result"]["data"]["result"] == "alpha-3"
    assert app.edges == [("__start__", "generic_step"), ("generic_step", "__end__")]


def test_build_langgraph_planned_graph_wraps_internal_planned_graph(monkeypatch):
    install_fake_langgraph(monkeypatch)
    agent = build_direct_agent()
    planned_graph = build_planned_agent_graph({"worker": agent}, mode="eval", output=lambda result, _state: {"agent_text": result.data["result"]})
    app = build_langgraph_planned_graph(planned_graph, node_name="planned")

    state = app.invoke(
        {
            "row": {
                "step_id": "step-a",
                "agent": "worker",
                "input": {"tool": "join_values", "input": {"prefix": "planned", "value": 9}},
                "reason": "generic test route",
                "expected_tools": ["join_values"],
            }
        }
    )

    assert state["selected_agent"] == "worker"
    assert state["agent_text"] == "planned-9"
    assert state["plan"]["expected_tools"] == ["join_values"]
    assert app.edges == [("__start__", "planned"), ("planned", "__end__")]


def test_agentic_graph_wrapper_uses_bridge_node(monkeypatch):
    install_fake_langgraph(monkeypatch)
    agent = build_direct_agent()
    graph = AgenticGraph(name="wrapper_flow")
    graph.add_agent_node(
        "step",
        agent=agent,
        input=lambda state: {"tool": "join_values", "input": {"prefix": state["prefix"], "value": state["value"]}},
        output=lambda result, _state: {"answer": result.data["result"]},
        trace=None,
    )
    graph.edge("__start__", "step").edge("step", "__end__")

    state = graph.compile().invoke({"prefix": "wrapped", "value": 5})

    assert state["answer"] == "wrapped-5"


def test_agentic_graph_wrapper_normalizes_start_end_aliases(monkeypatch):
    install_fake_langgraph(monkeypatch)
    graph = AgenticGraph(name="alias_flow")
    graph.add_node("step", lambda _state: {"done": True})
    graph.edge("START", "step").edge("step", "END")

    compiled = graph.compile()

    assert compiled.edges == [("__start__", "step"), ("step", "__end__")]


def test_langgraph_tutorial_uses_mvp_graph_and_human_output():
    import json
    from pathlib import Path

    notebook = json.loads(Path("tutorials/09_graph_api.ipynb").read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert "toolkit.agent_node" in source or "lab.agent_node" in source
    assert "toolkit.graph" in source or "lab.graph" in source
    assert "graph.run" in source or "graph.invoke" in source
    assert "toolkit.human_result" in source or "lab.human_result" in source or "print_human_result" in source
    assert "LangGraph" in source
    assert "/home/sagemaker-user" not in source


def test_agent_output_envelope_keeps_answer_data_and_runtime_separate():
    from agentic_systems import agent_output

    agent = build_direct_agent()
    result = agent.run({"tool": "join_values", "input": {"prefix": "case", "value": 11}}, mode="eval")
    output = agent_output(result)

    assert output["schema_version"] == "agentic_systems.agent_output.v1"
    assert output["ok"] is True
    assert output["answer"] == ""
    assert output["data"]["result"] == "case-11"
    assert output["summary"]["kind"] == "structured_data"
    assert output["tools"][0]["name"] == "join_values"
    assert output["runtime"]["engine"] == "python-direct"




def test_agent_output_accepts_domain_fields_mapper_without_core_hardcoding():
    from agentic_systems import agent_output

    agent = build_direct_agent()
    result = agent.run({"tool": "join_values", "input": {"prefix": "case", "value": 12}}, mode="eval")

    def mapper(_result, context):
        return {"joined": context["data"]["result"], "tool_count": len(context["tools"])}

    output = agent_output(result, fields_mapper=mapper)

    assert output["answer"] == ""
    assert output["fields"] == {"result": "case-12", "joined": "case-12", "tool_count": 1}


def test_langgraph_bridge_default_output_is_agent_output_envelope():
    agent = build_direct_agent()
    node = build_langgraph_agent_node(
        agent,
        input=lambda state: {"tool": "join_values", "input": {"prefix": state["prefix"], "value": state["value"]}},
        trace=None,
        mode="eval",
    )

    update = node({"prefix": "default", "value": 4})

    assert set(update) == {"agent_output"}
    assert update["agent_output"]["answer"] == ""
    assert update["agent_output"]["data"]["result"] == "default-4"
    assert update["agent_output"]["tools"][0]["name"] == "join_values"

