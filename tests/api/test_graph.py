from __future__ import annotations


def test_high_level_graph_api_builds_and_executes_state_nodes(monkeypatch):
    import agentic_systems as toolkit
    import agentic_systems.integrations.langgraph as bridge

    class FakeCompiled:
        def __init__(self, nodes):
            self.nodes = nodes

        def invoke(self, state):
            output = dict(state)
            for node in self.nodes.values():
                output.update(node(output))
            return output

    class FakeStateGraph:
        def __init__(self, state_schema):
            self.state_schema = state_schema
            self.nodes = {}
            self.edges = []

        def add_node(self, name, node):
            self.nodes[name] = node

        def add_edge(self, start, end):
            self.edges.append((start, end))

        def compile(self):
            return FakeCompiled(self.nodes)

    monkeypatch.setattr(bridge, "_import_langgraph_graph", lambda: ("__start__", "__end__", FakeStateGraph))

    graph = toolkit.graph(
        state=dict,
        nodes={"double": lambda state: {"value": state["value"] * 2}},
        edges=[("START", "double"), ("double", "END")],
        engine="langgraph",
    )

    assert graph.run({"value": 21}) == {"value": 42}


def test_portable_graph_exposes_public_boundary_and_topology_inspection():
    import agentic_systems as toolkit

    graph = toolkit.graph(
        nodes={"double": lambda state: {"value": state["value"] * 2}},
        edges=[("START", "double"), ("double", "END")],
        engine="portable",
        name="calculator_graph",
    )

    assert graph.inspect() == {
        "name": "calculator_graph",
        "engine": "portable",
        "schema_version": "agentic_systems.graph-boundary.v1",
        "kind": "agentic-systems-native",
        "framework": None,
        "graph_type": "GraphApp",
        "native_type": "_PortableGraph",
        "owns": [
            "portable_state_transition",
            "agent_invocation",
            "result_projection",
        ],
        "preserves": [
            "ok",
            "final",
            "data",
            "tool_events",
            "usage",
            "engine",
            "model",
            "mode",
            "validation",
            "errors",
        ],
        "nodes": ["double"],
        "edges": [["START", "double"], ["double", "END"]],
        "conditional_edge_count": 0,
    }
