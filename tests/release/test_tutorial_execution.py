from __future__ import annotations

import asyncio
from pathlib import Path
import sys

import nbformat
import pytest
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "tutorials"

DETERMINISTIC_NOTEBOOKS = (
    "core/00_runtime_scheduler.ipynb",
    "core/01_tool.ipynb",
    "core/02_skills.ipynb",
    "core/03_agent.ipynb",
    "core/04_results_lineage.ipynb",
    "core/05_system.ipynb",
    "core/06_graph_native.ipynb",
    "core/07_environment_eval.ipynb",
    "core/08_single_agentic_system.ipynb",
    "core/09_multi_agentic_system.ipynb",
    "core/10_multi_agent_graph.ipynb",
    "providers/00_auto.ipynb",
    "frameworks/00_langgraph.ipynb",
    "frameworks/01_openai_agents.ipynb",
    "frameworks/02_aws_strands.ipynb",
)

PROVIDER_NOTEBOOKS = (
    "providers/01_openai.ipynb",
    "providers/02_bedrock.ipynb",
    "providers/03_vllm.ipynb",
)


def _execute_notebook(client: NotebookClient):
    if sys.platform != "win32":
        return client.execute(cwd=str(ROOT))

    loop = asyncio.SelectorEventLoop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(client.async_execute(cwd=str(ROOT)))
    finally:
        asyncio.set_event_loop(None)
        loop.close()


def test_execution_inventory_covers_every_canonical_notebook():
    canonical = {
        path.relative_to(TUTORIALS).as_posix()
        for path in TUTORIALS.rglob("*.ipynb")
    }
    classified = set(DETERMINISTIC_NOTEBOOKS) | set(PROVIDER_NOTEBOOKS)
    assert classified == canonical
    assert not set(DETERMINISTIC_NOTEBOOKS) & set(PROVIDER_NOTEBOOKS)


@pytest.mark.parametrize("name", DETERMINISTIC_NOTEBOOKS)
def test_deterministic_notebook_executes_from_fresh_kernel(name, monkeypatch):
    for variable in (
        "RUN_OPENAI_LIVE",
        "RUN_VLLM_LIVE",
        "RUN_BEDROCK_LIVE",
        "RUN_LANGGRAPH_LIVE",
        "RUN_STRANDS_LIVE",
        "RUN_OPENAI_AGENTS_LIVE",
    ):
        monkeypatch.setenv(variable, "0")

    notebook = nbformat.read(TUTORIALS / name, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=120,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    executed = _execute_notebook(client)
    assert all(
        output.get("output_type") != "error"
        for cell in executed.cells
        for output in cell.get("outputs", [])
    )
