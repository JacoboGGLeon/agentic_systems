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
