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

# OPENAI_AGENTS_DEPENDENCY: resolve availability and installation from the registry.
framework_name = "openai-agents"
install_target = toolkit.dependency_target(framework_name, kind="framework")
if install_target is None:
    raise RuntimeError(f"{framework_name!r} has no registered install target.")
if importlib.util.find_spec("agents") is None:
    get_ipython().run_line_magic("pip", f'install -q "{install_target}"')
importlib.invalidate_caches()
if importlib.util.find_spec("agents") is None:
    raise ImportError(
        f"{framework_name!r} remains unavailable after installing "
        f'"{install_target}". Restart this kernel and run the notebook again.'
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
    target.source = target.source.replace(
        "from agents import (\n",
        "from agents import (  # noqa: E402\n",
        1,
    )
    target.source = target.source.replace(
        "from pydantic import BaseModel\n",
        "from pydantic import BaseModel  # noqa: E402\n",
        1,
    )
    target.source = target.source.replace(
        "\nimport agentic_systems as toolkit\n\nRUN_LIVE",
        "\nRUN_LIVE",
        1,
    )
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.execution_count = None
            cell.outputs = []
    nbformat.write(notebook, OPENAI_NOTEBOOK)
    print(OPENAI_NOTEBOOK.relative_to(ROOT))


if __name__ == "__main__":
    update_openai_agents()
