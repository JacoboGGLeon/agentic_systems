"""Execute the current course against an installed wheel; no provider inference."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
import agentic_systems as toolkit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / os.environ.get("AGENTIC_213_EVIDENCE_DIR", "revisions/2.1.3/implementation-evidence")


def main():
    assert toolkit.__version__ == importlib.metadata.version("agentic-systems") == "2.1.3"
    assert "site-packages" in Path(toolkit.__file__).parts
    destination = OUTPUT / "tutorials"
    destination.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted((ROOT / "tutorials").glob("[0-9][0-9]_*.ipynb")):
        notebook = nbformat.read(path, as_version=4)
        source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        source_code_cells = sum(c.cell_type == "code" for c in notebook.cells)
        for cell in notebook.cells:
            if cell.cell_type == "code":
                cell.execution_count, cell.outputs = None, []
        bootstrap = nbformat.v4.new_code_cell(
            "import sys as __harness_sys\nfrom pathlib import Path as __harness_Path\n"
            + "__harness_sys.path.insert(0, " + repr(str(ROOT / "tutorials")) + ")\n"
            + "from _offline import enforce_offline as __enforce_offline, blocked_attempts as __blocked_attempts\n__enforce_offline()\n"
            + "import agentic_systems as __harness_ag\nassert __harness_ag.__version__ == '2.1.3'\n"
            + "assert 'site-packages' in __harness_Path(__harness_ag.__file__).parts\n",
            metadata={"tags": ["validation-only", "hide-input"]})
        notebook.cells.insert(0, bootstrap)
        notebook.cells.append(nbformat.v4.new_code_cell("assert __blocked_attempts() == 0", metadata={"tags": ["validation-only", "hide-input"]}))
        manager = KernelManager(kernel_name="python3")
        manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        client = NotebookClient(notebook, km=manager, timeout=90, resources={"metadata": {"path": str(ROOT)}})
        try:
            client.execute()
            nbformat.validate(notebook)
            nbformat.write(notebook, destination / path.name)
        finally:
            if client.kc is not None:
                client.kc.stop_channels()
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source_sha256, "Notebook source changed during execution"
        row = {"notebook": path.name, "passed": True, "source_sha256": source_sha256,
               "executed_sha256": hashlib.sha256((destination / path.name).read_bytes()).hexdigest(),
               "code_cells": source_code_cells,
               "validation_only_cells": 2}
        rows.append(row)
        print(json.dumps(row), flush=True)
    assert len(rows) == 11
    (OUTPUT / "tutorials.json").write_text(json.dumps({"version": toolkit.__version__, "package_file": toolkit.__file__,
        "notebooks": rows, "inference_requests": 0, "external_providers": "configured-only-not-run"}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
