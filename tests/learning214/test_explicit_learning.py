"""Teaching must expose the construction a developer is meant to learn."""
import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKS = sorted((ROOT / "tutorials").rglob("*.ipynb")) + sorted(
    p for p in (ROOT / "examples").rglob("*.ipynb") if "history" not in p.parts
)


def hidden_builders(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        if not (module.startswith("examples.") or module.startswith("agentic_systems_studio.")):
            continue
        for name in node.names:
            if name.name in {"run", "build", "demonstrate", "verify", "build_system", "build_conversational_system", "handoffs"}:
                yield module + "." + name.name


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_notebook_declares_its_toolkit_units(path):
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
    tree = ast.parse(code)
    assert not list(hidden_builders(tree))
    declarations = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                    and isinstance(n.value, ast.Name) and n.value.id == "toolkit"}
    assert declarations & {"tool", "Agent", "System", "Environment", "Eval", "model_artifact"}, path
    assert not any(isinstance(n, ast.FunctionDef) and n.name == "show" for n in ast.walk(tree))
    assert "2.1.4.dev4" not in code


def test_example_entrypoints_do_not_delegate_their_demonstration():
    for path in (ROOT / "examples").rglob("example.py"):
        if "history" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not list(hidden_builders(tree)), path


def test_documented_execution_controls_are_executable():
    from examples.execution_controls.example import run
    report = run()
    assert report["output"]["ok"] and not report["negative"]["ok"]
    assert report["runtime"]["max_retries"] == 0
    assert report["runtime"]["timeout_s"] < report["timeout_s"]
    assert report["inference_requests"] == 0
