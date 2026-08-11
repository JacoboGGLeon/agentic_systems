import builtins
import os
import sys
import types

import pytest

from agentic_systems import (
    AgenticSystem,
)
from agentic_systems.integrations.langgraph import AgenticGraph


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


def build_system(strict=True, defaults=None):

    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return AgenticSystem(
        model="demo-model", region="us-east-1", strict=strict, defaults=defaults
    )


def test_agentic_graph_success_and_import_error(monkeypatch):
    install_fake_langgraph(monkeypatch)
    graph = AgenticGraph(name="flow", state=dict)
    system_graph = build_system().graph(name="system_flow")
    assert isinstance(system_graph.native, FakeStateGraph)
    assert isinstance(graph.native, FakeStateGraph)
    assert (
        graph.add_agent_node("agent", agent=FakeAgentForGraph(), input="request")
        is graph
    )
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
