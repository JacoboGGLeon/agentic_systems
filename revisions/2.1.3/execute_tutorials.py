"""Execute only the canonical 2.1.3 notebooks, each in a new local kernel."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
import agentic_systems as toolkit

ROOT = Path(__file__).resolve().parents[2]
HOME = Path(__file__).resolve().parent


def main():
    assert toolkit.__version__ == importlib.metadata.version("agentic-systems") == "2.1.3"
    assert "site-packages" in Path(toolkit.__file__).parts
    output = HOME / "evidence/tutorials"
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for source in sorted((ROOT / "tutorials").glob("[0-9][0-9]_*.ipynb")):
        notebook = nbformat.read(source, as_version=4)
        for cell in notebook.cells:
            if cell.cell_type == "code":
                cell.execution_count, cell.outputs = None, []
        manager = KernelManager(kernel_name="python3")
        manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        client = NotebookClient(notebook, km=manager, timeout=60,
                                resources={"metadata": {"path": str(ROOT)}})
        try:
            client.execute()
            nbformat.validate(notebook)
            nbformat.write(notebook, output / source.name)
        finally:
            if client.kc is not None:
                client.kc.stop_channels()
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
        rows.append({"notebook": source.name, "passed": True,
                     "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                     "executed_sha256": hashlib.sha256((output / source.name).read_bytes()).hexdigest(),
                     "code_cells": sum(c.cell_type == "code" for c in notebook.cells)})
        print(json.dumps(rows[-1]), flush=True)
    assert len(rows) == 10
    (HOME / "evidence/tutorials.json").write_text(json.dumps({
        "version": toolkit.__version__, "package_file": toolkit.__file__,
        "notebooks": rows, "inference_requests": 0,
        "external_providers": "configured-only-not-run",
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
