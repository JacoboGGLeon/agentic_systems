import importlib.metadata
import json
from pathlib import Path
import sys

import pytest
import agentic_systems as toolkit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "examples"))
from order_fulfillment import build_system, verify


def test_one_surface_and_no_compatibility_entrypoints():
    assert toolkit.__version__ == importlib.metadata.version("agentic-systems") == "2.1.3"
    assert "site-packages" in Path(toolkit.__file__).parts
    assert len(toolkit.__all__) == 18
    for name in ("agent", "system", "graph", "environment", "eval", "Route",
                 "AgenticSystem", "CompiledSystem", "Tool", "Skill", "RuntimeConfig"):
        assert not hasattr(toolkit, name), name
    for name in ("pipeline", "bind", "agent", "graph"):
        assert not hasattr(toolkit.Agent, name)
        assert not hasattr(toolkit.System, name)


@pytest.mark.parametrize("owner", [toolkit.Agent, toolkit.System])
@pytest.mark.parametrize("backend", ["native", "langgraph"])
@pytest.mark.parametrize("kind", ["sequence", "parallel", "decision"])
def test_same_flow_grammar_and_run_contract(owner, backend, kind):
    first = toolkit.Action("increment", lambda d: {"value": d["value"] + 1})
    second = toolkit.Action("double", lambda d: {"value": d["value"] * 2})
    if owner is toolkit.System:
        first = toolkit.Agent("incrementer", first)
        second = toolkit.Agent("doubler", second)
    if kind == "sequence":
        flow, expected = toolkit.Sequence((first, second)), 8
    elif kind == "parallel":
        flow = toolkit.Parallel((first, second), join=lambda rows: {"value": sum(d["value"] for d in rows.values())})
        expected = 10
    else:
        flow = toolkit.Graph(nodes=(("inc", first), ("double", second)),
                             edges=(("inc", lambda d: "double" if d["value"] >= 0 else "END"), ("double", "END")), start="inc")
        expected = 8
    unit = owner("owner", flow, backend=backend)
    direct, prepared = unit.run({"value": 3}), unit.compile().run({"value": 3})
    assert direct.ok and prepared.ok and direct.data == prepared.data == {"value": expected}
    assert direct.meta["kind"] == owner.__name__.lower()
    json.dumps(direct.to_dict(), allow_nan=False)
    if kind == "decision":
        assert unit.run({"value": -3}).data == {"value": -2}


@pytest.mark.parametrize("name", ["native", "langgraph", "openai-agents", "strands"])
def test_runtime_agents_keep_framework_without_an_alternative_constructor(name):
    @toolkit.tool
    def echo(value: int) -> dict:
        """Return an integer without model inference."""
        return {"value": value}
    agent = toolkit.Agent("operator", runtime=toolkit.runtime(provider="python-runtime"),
                          framework=toolkit.framework(name), skills=(toolkit.skill(name="echo", tools=[echo]),))
    result = agent.run({"tool": "echo", "input": {"value": 7}})
    assert result.ok and result.data["value"] == 7, result.to_dict()
    assert any(n.engine == "python-runtime" for n in result.walk())


def test_compile_never_creates_the_provider_or_calls_a_user_function(monkeypatch):
    import agentic_systems._grammar as implementation
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("should run only during execution")
    monkeypatch.setattr(implementation, "_make_actor", forbidden)
    actor = toolkit.Agent("configured", runtime=toolkit.runtime(provider="openai-runtime", model="configured-only"))
    actor.compile().inspect()
    flow = toolkit.Graph(nodes=(("step", toolkit.Action("step", forbidden)),),
                         edges=(("step", forbidden),), start="step")
    toolkit.Agent("flow", flow).compile().inspect()
    assert not calls


@pytest.mark.parametrize("backend", ["native", "langgraph"])
def test_challenge_environment_eval_and_failure_evidence(backend):
    report = verify(backend)
    assert report["sdk_version"] == "2.1.3" and report["cases_passed"] == 7
    assert report["evaluation"]["data"]["passed"] == 6
    assert len(report["environment"]["children"]) == 6
    assert not report["negative_control"]["ok"]


def test_no_ignored_alias_parameters_or_ambiguous_agent():
    with pytest.raises(ValueError):
        toolkit.Agent("ambiguous")
    with pytest.raises(ValueError):
        toolkit.Agent("ambiguous", toolkit.Action("a", lambda d:d), runtime=toolkit.runtime(provider="python-runtime"))
    with pytest.raises(TypeError):
        toolkit.runtime(provider="python-runtime", model_id="alias")
    with pytest.raises(ValueError):
        toolkit.runtime(provider="auto")
    unit = build_system()
    with pytest.raises(TypeError):
        unit.run({}, execution="legacy")
    with pytest.raises(TypeError):
        toolkit.Environment("env", unit, ({},)).run({"ignored": True})
    with pytest.raises(TypeError):
        toolkit.model_server("not-an-artifact")


def test_cli_api_lists_the_same_single_surface(capsys):
    from agentic_systems.cli import main
    assert main(["api"]) == 0
    assert json.loads(capsys.readouterr().out)["public_api"] == toolkit.__all__


def test_installed_scaffolder_emits_sdk_only_project_and_refuses_overwrite(tmp_path):
    from agentic_systems.scaffolding import create_project
    target = create_project(tmp_path / "app")
    assert (target / "src/order_fulfillment/system.py").is_file()
    assert not (target / "src/unified_grammar").exists()
    assert 'agentic-systems==2.1.3' in (target / "pyproject.toml").read_text()
    assert '.env.example' in [p.name for p in target.iterdir()]
    assert json.loads((target / "manifest.json").read_text())["sdk_version"] == "2.1.3"
    import ast
    runner = ast.parse((target / "execute_notebook.py").read_text())
    notebook_paths = [node.value for node in ast.walk(runner)
                      if isinstance(node, ast.Constant) and isinstance(node.value, str)
                      and node.value.endswith(".ipynb")]
    assert len(notebook_paths) == 1
    assert (target / notebook_paths[0]).is_file()
    with pytest.raises(FileExistsError):
        create_project(target)


def test_model_owner_preserves_child_engine_without_a_live_call(monkeypatch):
    import agentic_systems._grammar as implementation
    def prepared(owner):
        return implementation._Prepared("test-model", "model", "native",
            lambda value, context: toolkit.RunResult(data={"value": 7}, ok=True, engine="openai-runtime"))
    monkeypatch.setattr(implementation, "_model_body", prepared)
    actor = toolkit.Agent("configured", runtime=toolkit.runtime(provider="openai-runtime"))
    result = actor.run({})
    assert result.ok and result.engine == "openai-runtime"
