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
    "api/14_api_contract_matrix.ipynb",
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
    "frameworks/03_provider_framework_matrix.ipynb",
    "frameworks/02_aws_strands.ipynb",
)

PROVIDER_NOTEBOOKS = (
    "providers/01_openai.ipynb",
    "providers/02_bedrock.ipynb",
    "providers/03_vllm.ipynb",
    "providers/04_ollama.ipynb",
)

EXAMPLE_ROOT = ROOT / "examples" / "agentic_systems_studio" / "notebooks"
EXAMPLE_NOTEBOOKS = (
    "00_conversational_system.ipynb",
    "01_launch_studio.ipynb",
)
LIVE_NOTEBOOKS = (
    ("providers/01_openai.ipynb", "RUN_OPENAI_LIVE"),
    ("providers/02_bedrock.ipynb", "RUN_BEDROCK_LIVE"),
    ("providers/04_ollama.ipynb", "RUN_OLLAMA_LIVE"),
    ("frameworks/00_langgraph.ipynb", "RUN_LANGGRAPH_LIVE"),
    ("frameworks/01_openai_agents.ipynb", "RUN_OPENAI_AGENTS_LIVE"),
    ("frameworks/02_aws_strands.ipynb", "RUN_STRANDS_LIVE"),
)


LIVE_NOTEBOOK_GATE = "AGENTIC_SYSTEMS_RUN_LIVE_NOTEBOOKS"


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
        path.relative_to(TUTORIALS).as_posix() for path in TUTORIALS.rglob("*.ipynb")
    }
    classified = set(DETERMINISTIC_NOTEBOOKS) | set(PROVIDER_NOTEBOOKS)
    assert classified == canonical
    assert not set(DETERMINISTIC_NOTEBOOKS) & set(PROVIDER_NOTEBOOKS)


@pytest.mark.parametrize("name", DETERMINISTIC_NOTEBOOKS)
def test_deterministic_notebook_executes_from_fresh_kernel(name, monkeypatch):
    for variable in (
        "RUN_OPENAI_LIVE",
        "RUN_VLLM_LIVE",
        "RUN_OLLAMA_LIVE",
        "RUN_BEDROCK_LIVE",
        "RUN_MATRIX_LIVE",
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


@pytest.mark.parametrize("name", PROVIDER_NOTEBOOKS)
def test_provider_notebook_executes_as_not_run_from_fresh_kernel(
    name, monkeypatch, tmp_path
):
    for variable in (
        "RUN_OPENAI_LIVE",
        "RUN_VLLM_LIVE",
        "RUN_OLLAMA_LIVE",
        "RUN_BEDROCK_LIVE",
    ):
        monkeypatch.setenv(variable, "0")
    isolated_dotenv = tmp_path / ".env"
    isolated_dotenv.write_text(
        "RUN_OPENAI_LIVE=0\nRUN_VLLM_LIVE=0\nRUN_OLLAMA_LIVE=0\nRUN_BEDROCK_LIVE=0\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTIC_SYSTEMS_DOTENV", str(isolated_dotenv))

    notebook = nbformat.read(TUTORIALS / name, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=120,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    executed = _execute_notebook(client)
    outputs = [output for cell in executed.cells for output in cell.get("outputs", [])]

    assert all(output.get("output_type") != "error" for output in outputs)
    assert "not-run" in repr(outputs)


def test_example_execution_inventory_covers_every_studio_notebook():
    actual = {path.name for path in EXAMPLE_ROOT.glob("*.ipynb")}
    assert set(EXAMPLE_NOTEBOOKS) == actual


@pytest.mark.parametrize("name", EXAMPLE_NOTEBOOKS)
def test_studio_example_notebook_executes_from_fresh_kernel(
    name, monkeypatch, tmp_path
):
    import socket

    monkeypatch.setenv("AGENTIC_SYSTEMS_NOTEBOOK_TEST", "1")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = tmp_path / ".env"
    environment.write_text(
        "\n".join(
            (
                "AGENTIC_SYSTEMS_PROVIDER=python-runtime",
                "AGENTIC_SYSTEMS_FRAMEWORK=native",
                "RUN_STUDIO_LIVE=0",
                "RUN_SEMANTIC_MATRIX_LIVE=0",
                f"AGENTIC_SYSTEMS_STUDIO_PORT={port}",
                "AGENTIC_SYSTEMS_STUDIO_PROXY_PREFIX=/jupyterlab/default/proxy",
                "",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTIC_SYSTEMS_ENV_FILE", str(environment))

    notebook = nbformat.read(EXAMPLE_ROOT / name, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=180,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    executed = _execute_notebook(client)
    outputs = [output for cell in executed.cells for output in cell.get("outputs", [])]
    assert all(output.get("output_type") != "error" for output in outputs)
    if name == "01_launch_studio.ipynb":
        assert "Health check: ok" in repr(outputs)


@pytest.mark.parametrize(("name", "flag"), LIVE_NOTEBOOKS)
def test_live_notebook_executes_when_explicitly_enabled(name, flag):
    import os

    if os.getenv(LIVE_NOTEBOOK_GATE) != "1" or os.getenv(flag) != "1":
        pytest.skip(
            f"Set {LIVE_NOTEBOOK_GATE}=1 and {flag}=1 to execute this live notebook."
        )

    notebook = nbformat.read(TUTORIALS / name, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=300,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    executed = _execute_notebook(client)
    outputs = [output for cell in executed.cells for output in cell.get("outputs", [])]
    assert all(output.get("output_type") != "error" for output in outputs)
    assert "not-run" not in repr(outputs)
