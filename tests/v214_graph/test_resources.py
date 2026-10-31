import gc
import json
import sys
from pathlib import Path

import pytest
import agentic_systems as t
from test_graph_contracts import graph, assert_result


def test_loaded_skill_executes_typed_context_and_retains_relative_imports():
    from examples.common_graph.resources import loaded_skill_example
    report = loaded_skill_example()
    assert report["output"]["total"] == 116 and report["output"]["currency"] == "MXN"
    folder = Path(__file__).resolve().parents[2] / "examples/common_graph/skills/pricing"
    skill = t.load_skill(folder)
    operation = skill.tools[0]
    del skill
    gc.collect()
    output = t.Agent("loaded", graph(operation), context=t.Context({"tax_percent": 16, "currency": "MXN"}, sources=("policy",))).run({"subtotal": 10})
    # This graph's State does not declare subtotal/quote outputs, so use the resource schema instead.
    assert not output.ok
    from examples.common_graph.resources import QuoteState
    from langgraph.graph import StateGraph, START, END
    b = StateGraph(QuoteState)
    b.add_node("quote", operation)
    b.add_edge(START, "quote")
    b.add_edge("quote", END)
    output = t.Agent("loaded", b, context=t.Context({"tax_percent": 16, "currency": "MXN"}, sources=("policy",))).run({"subtotal": 10})
    assert output.ok and output.data["total"] == 11
    assert_result(output)


@pytest.mark.parametrize("kind", ["missing", "missing_builder", "wrong_builder"])
def test_invalid_skill_packages_are_rejected(tmp_path, kind):
    if kind != "missing":
        (tmp_path / "SKILL.md").write_text("# Fixture", encoding="utf-8")
        (tmp_path / "skill.py").write_text("value=1" if kind == "missing_builder" else "def build_skill():\n    return {}\n", encoding="utf-8")
    with pytest.raises((ValueError, TypeError)):
        t.load_skill(tmp_path)


def test_serving_declaration_is_offline_and_credentials_are_redacted():
    from examples.common_graph.resources import serving_example
    report = serving_example()
    assert report["runtime"]["provider"] == "vllm-runtime"
    assert report["server"]["endpoint"]["owned"] is False
    assert "example-local-token" not in json.dumps(report)


def test_model_server_start_health_stop_with_simulated_process_only(monkeypatch, tmp_path):
    import agentic_systems._engine.serving.vllm as implementation
    started, commands = [], []
    class Process:
        pid = 1234
        alive = True
        def poll(self):
            return None if self.alive else 0
        def terminate(self):
            self.alive = False
        def kill(self):
            self.alive = False
        def wait(self, timeout=None):
            self.alive = False
            return 0
    process = Process()
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b'{"data":[{"id":"fixture-model"}]}'
    class Opener:
        def open(self, *args, **kwargs):
            if not started:
                raise OSError("not started")
            return Response()
    monkeypatch.setattr(implementation.shutil, "which", lambda name: "fixture-vllm")
    monkeypatch.setattr(implementation.urllib.request, "build_opener", lambda *args: Opener())
    server = t.model_server(t.model_artifact("fixture-weights"), served_model_name="fixture-model", log_path=str(tmp_path / "server.log"), api_key="fixture-secret")
    def spawn(command, **kwargs):
        started.append(True)
        commands.append(command)
        return process
    server._resource._popen_factory = spawn
    assert server.health().status == "stopped"
    endpoint = server.start()
    assert endpoint.owned and endpoint.pid == 1234 and endpoint.model == "fixture-model"
    assert server.health().status == "healthy"
    assert commands[0][0] == "fixture-vllm"
    assert "fixture-secret" not in str(server.inspect())
    server.stop()
    assert not process.alive


@pytest.mark.parametrize("kwargs", [{"port": 0}, {"profile": "missing"}, {"extra_args": ("--port=99",)}])
def test_invalid_server_parameters(kwargs):
    with pytest.raises((ValueError, TypeError)):
        t.model_server(t.model_artifact("weights"), **kwargs)


def test_action_projects_nested_input_into_a_tool_node():
    from langgraph.graph import StateGraph, START, END
    from typing_extensions import TypedDict
    class Nested(TypedDict, total=False):
        order: dict
        value: int
    @t.tool
    def increment(value: int) -> dict:
        return {"value": value + 1}
    b = StateGraph(Nested)
    b.add_node("project", lambda state: increment.run(state["order"]))
    b.add_edge(START, "project")
    b.add_edge("project", END)
    output = t.Agent("nested", b).run({"order": {"value": 4}})
    assert output.ok and output.data["value"] == 5 and output.usage["inference_requests"] == 0
    assert_result(output)


def test_skill_init_failure_cleans_all_temporary_modules(tmp_path):
    (tmp_path / "SKILL.md").write_text("# Init failure", encoding="utf-8")
    (tmp_path / "skill.py").write_text("def build_skill(): return None", encoding="utf-8")
    (tmp_path / "__init__.py").write_text("raise RuntimeError('controlled init failure')", encoding="utf-8")
    before = {name for name in sys.modules if name.startswith("_loaded_skill_")}
    with pytest.raises(RuntimeError, match="controlled init"):
        t.load_skill(tmp_path)
    assert before == {name for name in sys.modules if name.startswith("_loaded_skill_")}
