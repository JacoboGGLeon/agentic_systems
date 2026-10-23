"""Execute the six-example walkthrough in a fresh kernel of this Python runtime."""

import json
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient


def main():
    home = Path(__file__).resolve().parent
    notebook = nbformat.read(home / "00_walkthrough.ipynb", as_version=4)
    # Do not inherit stale outputs as execution evidence.
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [
        sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"
    ]
    client = NotebookClient(
        notebook, km=manager, timeout=60,
        resources={"metadata": {"path": str(home)}},
    )
    try:
        client.execute()
        nbformat.validate(notebook)
        nbformat.write(notebook, home / "00_walkthrough.ipynb")
        nbformat.write(notebook, home / "evidence/executed-walkthrough.ipynb")
    finally:
        if client.kc is not None:
            client.kc.stop_channels()
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    print(json.dumps({
        "notebook": "passed",
        "code_cells": sum(c.cell_type == "code" for c in notebook.cells),
        "inference_requests": 0,
    }))


if __name__ == "__main__":
    main()
