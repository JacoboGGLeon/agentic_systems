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
    "00_runtime_api.ipynb",
    "00_runtime_scheduler_api.ipynb",
    "01_tool_api.ipynb",
    "02_skill_api.ipynb",
    "03_agent_api.ipynb",
    "04_human_result_api.ipynb",
    "05_lineage_memory_api.ipynb",
    "08_system_api.ipynb",
    "09_graph_api.ipynb",
    "10_environment_eval_api.ipynb",
    "11_single_agentic_system_api.ipynb",
    "12_multi_agentic_system_api.ipynb",
    "13_multi_agentic_graph_api.ipynb",
)

PROVIDER_NOTEBOOKS = (
    "00_runtime_bedrock_provider_api.ipynb",
    "00_runtime_openai_provider_api.ipynb",
    "00_runtime_vllm_provider_api.ipynb",
    "06_integrations_strands_api.ipynb",
    "07_integrations_openai_runtime_api.ipynb",
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
    canonical = {path.name for path in TUTORIALS.glob("*.ipynb")}
    classified = set(DETERMINISTIC_NOTEBOOKS) | set(PROVIDER_NOTEBOOKS)
    assert classified == canonical
    assert not set(DETERMINISTIC_NOTEBOOKS) & set(PROVIDER_NOTEBOOKS)


@pytest.mark.parametrize("name", DETERMINISTIC_NOTEBOOKS)
def test_deterministic_notebook_executes_from_fresh_kernel(name, monkeypatch):
    for variable in (
        "RUN_OPENAI_LIVE",
        "RUN_VLLM_LIVE",
        "RUN_BEDROCK_LIVE",
        "RUN_STRANDS_IDENTITY_LIVE",
        "RUN_OPENAI_STYLE_LIVE",
    ):
        monkeypatch.setenv(variable, "0")
    monkeypatch.setenv("AGENTIC_SYSTEMS_GRAPH_ENGINE", "portable")

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
