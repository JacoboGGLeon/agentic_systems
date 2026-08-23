"""Keep optional framework tutorials self-bootstrapping in fresh notebooks."""

from __future__ import annotations

from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
OPENAI_NOTEBOOK = ROOT / "tutorials" / "frameworks" / "01_openai_agents.ipynb"


def update_openai_agents() -> None:
    notebook = nbformat.read(OPENAI_NOTEBOOK, as_version=4)
    target = next(
        cell
        for cell in notebook.cells
        if cell.cell_type == "code" and "from agents import (" in cell.source
    )
    marker = "OPENAI_AGENTS_DEPENDENCY"
    setup = """import importlib.util
import os

import agentic_systems as toolkit

os.environ.setdefault("OPENAI_AGENTS_DISABLE_TRACING", "1")

# OPENAI_AGENTS_DEPENDENCY: resolve the install target from the canonical registry.
if importlib.util.find_spec("agents") is None:
    install_target = toolkit.dependency_target(
        "openai-agents", kind="framework"
    )
    if install_target is None:
        raise RuntimeError("OpenAI Agents has no registered install target.")
    get_ipython().run_line_magic(
        "pip", f'install -q "{install_target}"'
    )
importlib.invalidate_caches()
if importlib.util.find_spec("agents") is None:
    raise ImportError(
        'OpenAI Agents is unavailable. Install "agentic-systems[openai-agents]" '
        "and restart the kernel."
    )

"""
    if marker in target.source:
        dependency_end = target.source.index("from agents import (")
        target.source = setup + target.source[dependency_end:]
    else:
        existing = target.source.replace(
            'import os\n\nos.environ.setdefault("OPENAI_AGENTS_DISABLE_TRACING", "1")\n\n',
            "",
            1,
        )
        target.source = setup + existing
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.execution_count = None
            cell.outputs = []
    nbformat.write(notebook, OPENAI_NOTEBOOK)
    print(OPENAI_NOTEBOOK.relative_to(ROOT))


if __name__ == "__main__":
    update_openai_agents()
