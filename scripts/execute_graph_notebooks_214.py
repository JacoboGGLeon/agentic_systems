"""Run each dev2 notebook in a fresh kernel, with application networking denied."""
import hashlib
import json
import os
from pathlib import Path
import sys

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT = Path(__file__).resolve().parents[1]
wheel, site = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
evidence = site.parent
rows = []
for relative in ("examples/context_memory_lineage/01_context_memory_lineage.ipynb", "examples/common_graph/01_common_graph.ipynb"):
    path = ROOT / relative
    notebook = nbformat.read(path, 4)
    original = notebook.cells[:]
    capture = evidence / (path.stem + "-kernel-evidence.json")
    bootstrap = nbformat.v4.new_code_cell(
        "import sys\nfrom pathlib import Path\n"
        + "sys.path.insert(0, " + repr(str(ROOT / "tutorials")) + ")\n"
        + "from _offline import enforce_offline, blocked_attempts\nenforce_offline()\n"
        + "import agentic_systems as __toolkit\nassert __toolkit.__version__ == '2.1.4.dev2'\n"
        + "assert Path(__toolkit.__file__).resolve().is_relative_to(Path(" + repr(str(site)) + "))\n"
        + "sys.path.insert(0, " + repr(str(ROOT / "scripts")) + ")\n"
        + "from grammar_coverage_214 import Coverage\n__coverage = Coverage()\n"
        + "__coverage.current = " + repr(relative) + "\n__coverage.rows[__coverage.current] = set()\n"
        + "sys.setprofile(__coverage.profile)\n")
    footer = nbformat.v4.new_code_cell(
        "sys.setprofile(None)\nimport json\n"
        + "assert blocked_attempts() == 0\n"
        + "__run_results = {name: value.to_dict() for name, value in tuple(globals().items()) if isinstance(value, __toolkit.RunResult)}\n"
        + "Path(" + repr(str(capture)) + ").write_text(json.dumps({'grammar': __coverage.report(), 'run_results': __run_results, 'blocked_attempts': blocked_attempts()}, ensure_ascii=False, indent=2), encoding='utf-8')\n")
    notebook.cells = [bootstrap, *original, footer]
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(site), str(ROOT))),
           "OPENAI_AGENTS_DISABLE_TRACING": "1", "OTEL_SDK_DISABLED": "true"}
    client = NotebookClient(notebook, km=manager, timeout=180, resources={"metadata": {"path": str(ROOT)}})
    error = None
    try:
        client.execute(env=env)
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)[-6000:]}
    finally:
        if client.kc is not None:
            client.kc.stop_channels()
        if manager.has_kernel:
            manager.shutdown_kernel(now=False)
    notebook.cells = notebook.cells[1:-1]
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    row = {"path": relative, "passed": error is None, "error": error,
           "code_cells_executed": sum(c.cell_type == "code" and c.execution_count is not None for c in notebook.cells),
           "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
           "execution": "fresh Jupyter kernel; validation bootstrap enforces offline audit guard before example imports",
           "capture": capture.name}
    rows.append(row)
    (evidence / "kernel-notebooks.json").write_text(json.dumps({"wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "rows": rows}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"notebook": relative, "passed": row["passed"], "cells": row["code_cells_executed"], "error": error}), flush=True)
    if error:
        raise RuntimeError("Notebook failure preserved; candidate is not accepted")
