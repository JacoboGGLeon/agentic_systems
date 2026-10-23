"""Verify installed bytes and a project generated outside the source tree.

This orchestrates child processes; the generated application and notebook
install their offline audit guards before importing execution code.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
import agentic_systems as toolkit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / os.environ.get("AGENTIC_213_EVIDENCE_DIR", "revisions/2.1.3/implementation-evidence")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_child(arguments, directory, log):
    completed = subprocess.run([sys.executable, *arguments], cwd=directory,
                               text=True, capture_output=True, encoding="utf-8",
                               errors="replace")
    log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"Child validation failed: {log}")
    return completed


def main(wheel):
    wheel = Path(wheel).resolve()
    assert toolkit.__version__ == importlib.metadata.version("agentic-systems") == "2.1.3"
    installed = Path(toolkit.__file__).resolve().parent
    assert "site-packages" in installed.parts
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel) as archive:
        expected = {name.removeprefix("agentic_systems/"): archive.read(name)
                    for name in archive.namelist() if name.startswith("agentic_systems/") and not name.endswith("/")}
    actual = {p.relative_to(installed).as_posix(): p.read_bytes() for p in installed.rglob("*")
              if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    assert actual.keys() == expected.keys(), "Installed package file set differs from wheel"
    assert all(actual[name] == value for name, value in expected.items()), "Installed package bytes differ"
    base = run_child(["-I", "-c", "import sys, agentic_systems as a; "
                      "assert a.__version__ == '2.1.3'; "
                      "assert not {'openai', 'agents', 'strands', 'langgraph', 'boto3'} & sys.modules.keys(); "
                      "print('Base import: optional SDKs remain lazy')"], ROOT, OUTPUT / "base-import.log")
    with tempfile.TemporaryDirectory(prefix="agentic-213-acceptance-") as temporary:
        outside = Path(temporary)
        assert ROOT != outside and ROOT not in outside.parents
        project = outside / "generated"
        run_child(["-m", "agentic_systems.cli", "new", str(project)], outside, OUTPUT / "scaffold-generation.log")
        sums = (project / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
        for line in sums:
            value, relative = line.split("  ", 1)
            assert digest(project / relative) == value
        archive_path = OUTPUT / "generated-project.zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(project.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(project).as_posix())
        run_child(["app.py", "--both"], project, OUTPUT / "scaffold-app.log")
        run_child(["test_offline.py", "--junitxml=" + str(OUTPUT / "scaffold-tests.xml")], project, OUTPUT / "scaffold-tests.log")
        notebook = nbformat.read(project / "notebooks/01_order_challenge.ipynb", as_version=4)
        manager = KernelManager(kernel_name="python3")
        manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        client = NotebookClient(notebook, km=manager, timeout=90, resources={"metadata": {"path": str(project)}})
        try:
            client.execute()
            nbformat.validate(notebook)
            nbformat.write(notebook, OUTPUT / "scaffold-notebook.ipynb")
        finally:
            if client.kc is not None:
                client.kc.stop_channels()
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
        challenge = json.loads((project / "evidence/challenge.json").read_text(encoding="utf-8"))
        assert sum(r["cases_passed"] for r in challenge["reports"]) == 14
        shutil.copyfile(project / "evidence/challenge.json", OUTPUT / "scaffold-challenge.json")
    payload = {"version": toolkit.__version__, "wheel_sha256": digest(wheel),
               "installed_package": str(installed), "installed_files_equal_wheel": len(expected),
               "base_import_lazy": base.returncode == 0, "project_outside_repository": True,
               "project_checksum_entries_verified": len(sums), "project_cases_passed": 14,
               "project_notebook_code_cells": sum(c.cell_type == "code" for c in notebook.cells),
               "pristine_project_zip_sha256": digest(archive_path), "inference_requests": 0,
               "scope": "offline; local Jupyter kernel transport only; no real serving or provider inference"}
    (OUTPUT / "packaging.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True)
    main(parser.parse_args().wheel)
