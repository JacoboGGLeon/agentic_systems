"""Tutorial output helpers remain public and notebooks stay output-first."""

from __future__ import annotations

import json
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _tutorials() -> list[Path]:
    return sorted((_repo_root() / "tutorials").glob("*.ipynb"))


def _notebook_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _notebook_source(path: Path) -> str:
    nb = json.loads(path.read_text(encoding="utf-8"))
    chunks: list[str] = []
    for cell in nb.get("cells", []):
        source = cell.get("source", [])
        chunks.append("".join(source) if isinstance(source, list) else str(source))
    return "\n".join(chunks)


def test_output_helpers_are_public_imports():
    from agentic_systems import eval_report_output, eval_report_summary, maybe_show_trace, run_result_output, run_result_summary

    assert callable(run_result_output)
    assert callable(run_result_summary)
    assert callable(eval_report_output)
    assert callable(eval_report_summary)
    assert callable(maybe_show_trace)


def test_tutorials_do_not_inline_output_helper_implementations():
    forbidden = [
        "def result_output(",
        "def _tool_event_output(",
        "def _result_dict_output(",
        "def eval_report_output(",
        "def maybe_show_trace(",
    ]
    for path in _tutorials():
        text = _notebook_text(path)
        for needle in forbidden:
            assert needle not in text, f"{path.name} inlines {needle}; use public library helpers instead."


def test_tutorials_keep_engine_and_mode_semantics_clear():
    for path in _tutorials():
        text = _notebook_source(path)
        assert 'mode="local"' not in text
        assert "mode='local'" not in text
        assert 'engine="bedrock"' not in text
        if "02_agentic_systems_agent" in path.name:
            assert 'engine="bedrock-runtime"' in text or 'framework="bedrock"' in text or "AgenticSystem" in text


def test_tutorials_end_with_human_output_view():
    for path in _tutorials():
        text = _notebook_source(path)
        assert "toolkit.human_result" in text or "toolkit.show" in text or "lab.human_result" in text or "lab.show" in text


def test_all_notebook_cells_have_ids_after_checkpoint_09_cleanup():
    for path in _tutorials():
        nb = json.loads(path.read_text(encoding="utf-8"))
        for index, cell in enumerate(nb.get("cells", [])):
            assert cell.get("id"), f"{path.name} cell {index} is missing a notebook cell id."
