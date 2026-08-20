from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "tutorials"
CLI_ROOT = TUTORIALS / "cli"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _stream_text(output: dict) -> str:
    text = output.get("text", "")
    if isinstance(text, list):
        return "".join(text)
    return str(text)



def _python_notebooks() -> set[str]:
    return {
        path.relative_to(TUTORIALS).as_posix()
        for path in TUTORIALS.rglob("*.ipynb")
        if path.relative_to(TUTORIALS).parts[0] != "cli"
    }


def test_cli_curriculum_is_1_to_1_with_python_curriculum() -> None:
    paths = sorted(CLI_ROOT.rglob("*.ipynb"))
    assert len(paths) == 21

    mappings = []
    orders = []
    for path in paths:
        metadata = _load(path)["metadata"]["agentic_systems"]
        assert metadata["cli_curriculum"] is True
        assert metadata["rich_output_required"] is True
        assert metadata["outputs_preserved"] is True
        mappings.append(metadata["python_notebook"])
        orders.append(metadata["curriculum_order"])

    assert set(mappings) == _python_notebooks()
    assert sorted(orders) == list(range(21))


def test_cli_notebooks_use_real_cli_and_preserve_integral_rich_outputs() -> None:
    for path in sorted(CLI_ROOT.rglob("*.ipynb")):
        notebook = _load(path)
        code = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        )
        assert 'CLI = [sys.executable, "-m", "agentic_systems.cli"]' in code
        assert "subprocess.run(" in code
        assert "import agentic_systems as toolkit" not in code
        assert "toolkit." not in code

        outputs = [
            output
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
            for output in cell.get("outputs", [])
        ]
        assert outputs, path
        assert all(output.get("output_type") != "error" for output in outputs)
        streams = "\n".join(
            _stream_text(output)
            for output in outputs
            if output.get("output_type") == "stream"
        )
        assert "$ " in streams, path
        assert "+" in streams and "|" in streams, path
        assert "--json" in streams, path


def test_cli_matrix_notebooks_preserve_5_by_4_cardinality() -> None:
    matrix = _load(CLI_ROOT / "frameworks" / "03_provider_framework_matrix.ipynb")
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in matrix["cells"]
        if cell.get("cell_type") == "code"
    )
    assert 'assert payload["combination_count"] == 20' in source
    assert 'assert payload["passed"] == 20' in source
    assert 'args.append("--require-pass")' in source


def test_cli_tutorial_generator_check_is_non_destructive() -> None:
    tracked = CLI_ROOT / "frameworks" / "03_provider_framework_matrix.ipynb"
    before = tracked.read_bytes()
    completed = subprocess.run(
        [sys.executable, "scripts/generate_cli_tutorials.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert tracked.read_bytes() == before
