"""Project generation from the installed SDK; no alternate runtime or facade."""
import hashlib
from importlib import resources
import json
from pathlib import Path


def _copy(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            _copy(item, target)
        else:
            target.write_bytes(item.read_bytes())


def create_project(destination):
    destination = Path(destination).resolve()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Choose a new directory; existing projects are never overwritten")
    templates = resources.files("agentic_systems").joinpath("_templates")
    destination.mkdir(parents=True)
    _copy(templates.joinpath("project"), destination)
    _copy(templates.joinpath("order_fulfillment"), destination / "src/order_fulfillment")
    (destination / "evidence").mkdir()
    manifest = {"sdk_version": "2.1.3", "api": "agentic_systems", "inference_permitted": False,
                "declaration": "order_fulfillment.system:build_system", "validation": "not-run"}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    notebook = {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
        "cells": [
            {"cell_type": "markdown", "id": "intro", "metadata": {}, "source": ["# Pedidos · API única 2.1.3\n", "Input → validación → precio/stock → política → decisión. Sin inferencia."]},
            {"cell_type": "code", "id": "run", "metadata": {}, "execution_count": None, "outputs": [],
             "source": ['from pathlib import Path\n', 'import sys\n',
                        'root = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "app.py").is_file())\n',
                        'sys.path.insert(0, str(root / "src"))\n',
                        'from order_fulfillment.offline import enforce_offline\n', 'enforce_offline()\n',
                        'import agentic_systems as toolkit\n', 'assert toolkit.__version__ == "2.1.3"\n',
                        'from order_fulfillment import verify\n',
                        'reports = [verify(backend) for backend in ("native", "langgraph")]\n',
                        'assert all(r["cases_passed"] == 7 for r in reports)\n',
                        'for report in reports:\n',
                        '    for case in report["cases"]:\n',
                        '        print(report["backend"], case["name"], case["output"])\n']},
        ],
    }
    (destination / "notebooks").mkdir()
    (destination / "notebooks/01_order_challenge.ipynb").write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")
    files = sorted(p for p in destination.rglob("*") if p.is_file())
    (destination / "SHA256SUMS.txt").write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(destination).as_posix()}\n" for p in files
    ), encoding="utf-8")
    return destination
