from __future__ import annotations

import ast
import json
from pathlib import Path

import agentic_systems as toolkit


def test_tool_api_supports_simple_decorator_and_pydantic_tool_contracts():
    from pydantic import BaseModel

    @toolkit.tool
    def sumar(a: int, b: int) -> dict:
        return {"operation": "sumar", "result": a + b}

    class TwoNumbers(BaseModel):
        a: int
        b: int

    class OperationResult(BaseModel):
        operation: str
        result: int

    def sumar_contract(data: TwoNumbers) -> OperationResult:
        return OperationResult(operation="sumar", result=data.a + data.b)

    explicit = toolkit.Tool(sumar_contract, name="sumar", input=TwoNumbers, output=OperationResult)

    assert sumar.run({"a": 17, "b": 25}).data == {"operation": "sumar", "result": 42}
    assert explicit.run({"a": 17, "b": 25}).data == {"operation": "sumar", "result": 42}
    assert explicit.input_schema is TwoNumbers
    assert explicit.output_schema is OperationResult


def test_fundamentals_notebooks_are_simple_runtime_blueprints():
    root = Path(__file__).resolve().parents[1]
    notebook_dir = root / "tutorials"
    expected = {
        "01_tool_api.ipynb": ["@toolkit.tool", "toolkit.Tool", "Pydantic"],
        "02_skill_api.ipynb": ["toolkit.Skill", "Skill.check", "skills=[math_skill]"],
        "03_agent_api.ipynb": ['engine="python-runtime"', 'provider="auto"', "Agente LM"],
        "04_human_result_api.ipynb": ["toolkit.RunResult", "toolkit.final_answer", "toolkit.human_result"],
        "07_integrations_openai_runtime_api.ipynb": ['provider="auto"', 'framework="openai-agents"', "await agent.arun"],
        "08_system_api.ipynb": ["toolkit.AgenticSystem", "system.tool", "system.skill", "system.agent", "system.inspect"],
        "09_graph_api.ipynb": ["toolkit.graph(", "toolkit.agent_node", "agent.as_node", "graph.run"],
        "10_environment_eval_api.ipynb": ["toolkit.AgenticEnvironment", "toolkit.run_eval", "reward_fn"],
    }
    paths = {path.name: path for path in notebook_dir.glob("*.ipynb")}

    assert set(expected) <= set(paths)

    forbidden = (
        "#@title",
        "agentic_systems.examples.fundamentals",
        "configure_tutorial_environment",
        "runtime_case_skill",
        "RUN_CLOUD",
        "RUN_OPENAI_RUNTIME",
        "executed\": false",
        "Cloud run disabled",
        "demo_case",
        "case =",
        "TASK =",
        "TOOLS_BY_STYLE",
        "steps =",
        "fields_from_tools",
        "ags.run_agent(",
        "ags.run_langgraph(",
        "ags.run_openai_runtime(",
        "build_langgraph_agent_graph",
        "import agentic_systems as ags",
    )
    for name, required_tokens in expected.items():
        text = paths[name].read_text(encoding="utf-8")
        nb_for_text = json.loads(text)
        code_text = "\n".join("".join(cell.get("source", [])) for cell in nb_for_text.get("cells", []))
        combined_text = text + "\n" + code_text
        for token in forbidden:
            assert token not in combined_text, f"{name} should stay simple and real; found {token!r}."
        assert "toolkit.human_result" in combined_text or "toolkit.human_results" in combined_text or "toolkit.print_human_result" in combined_text or "toolkit.show" in combined_text or "toolkit.human_result" in combined_text or "toolkit.human_results" in combined_text or "lab.print_human_result" in combined_text
        for token in required_tokens:
            assert token in combined_text, f"{name} should contain {token!r}."

        nb = json.loads(text)
        assert nb.get("cells", [])[0].get("cell_type") == "markdown"
        code = "\n".join(
            "".join(cell.get("source", []))
            for cell in nb.get("cells", [])
            if cell.get("cell_type") == "code"
        )
        assert "import agentic_systems as toolkit" in code
        if name == "04_human_result_api.ipynb":
            assert "toolkit.normalize_output" in code and "toolkit.output_schema" in code
            assert "toolkit.RunResult" in code and "toolkit.final_answer" in code
        elif name not in {"08_system_api.ipynb", "09_graph_api.ipynb", "10_environment_eval_api.ipynb"}:
            assert "@toolkit.tool" in code or "mas.make_tools" in code
        for index, cell in enumerate(nb.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            try:
                ast.parse(source)
            except SyntaxError as exc:  # pragma: no cover - assertion payload
                raise AssertionError(f"{name} cell {index} has invalid Python syntax: {exc}") from exc


def test_no_extra_fundamentals_wrapper_module_is_needed():
    root = Path(__file__).resolve().parents[1]
    assert not (root / "src" / "agentic_systems" / "examples" / "fundamentals.py").exists()



def test_high_level_graph_api_builds_state_nodes_edges(monkeypatch):
    import agentic_systems.integrations.langgraph as bridge

    class FakeCompiled:
        def __init__(self, nodes):
            self.nodes = nodes

        def invoke(self, state):
            out = dict(state)
            for node in self.nodes.values():
                out.update(node(out))
            return out

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

