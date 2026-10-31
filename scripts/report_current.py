"""Report the installed API and reconcile current learning evidence by source hash."""

import ast
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import nbformat
import agentic_systems as toolkit

ROOT = Path(__file__).resolve().parents[1]
E = Path(os.environ["AGENTIC_VALIDATION_EVIDENCE"]).resolve()
UPSTREAM = {"Graph", "START", "END", "Command", "Send"}
CORE = set(toolkit.__all__) - UPSTREAM - {"__version__"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(value):
    try:
        return re.sub(r"0x[0-9a-fA-F]+", "<address>", str(inspect.signature(value)))
    except (TypeError, ValueError):
        return "See upstream documentation"


def main():
    installation = json.loads((E / "installation.json").read_text(encoding="utf-8"))
    assert toolkit.__version__ == installation["version"]
    wheel = ROOT / installation["wheel"]
    assert digest(wheel) == installation["wheel_sha256"]
    from agentic_systems._configuration import _Runtime, _Framework, _Artifact, _Server
    from agentic_systems._tools import _Tool, _Skill
    classes = {"runtime": _Runtime, "framework": _Framework, "model_artifact": _Artifact,
               "model_server": _Server, "tool": _Tool, "skill": _Skill, "load_skill": _Skill}
    surface = {}
    lines = [f"# API observada del wheel · {toolkit.__version__}", "",
             "15 conceptos propios, cinco reexportaciones originales de LangGraph y __version__. Métodos nativos de Pydantic/LangGraph pertenecen a esas bibliotecas y no son constructores nuevos. Graph requiere un owner para obtener RunResult; compile del owner valida el subconjunto integrado de LangGraph.", ""]
    for name in sorted(CORE):
        value = getattr(toolkit, name)
        cls = classes.get(name, value if inspect.isclass(value) else None)
        methods, properties = {}, []
        if cls is not None:
            for parent in reversed(cls.__mro__):
                if not parent.__module__.startswith("agentic_systems"):
                    continue
                for key, method in parent.__dict__.items():
                    if key.startswith("_"):
                        continue
                    if isinstance(method, property):
                        properties.append(key)
                    elif inspect.isfunction(method):
                        methods[key] = signature(method)
        surface[name] = {"signature": signature(value), "methods": methods, "properties": sorted(set(properties))}
        lines += ["## " + name, "", "```python", name + signature(value), "```", ""]
        lines += ["- " + key + sig for key, sig in sorted(methods.items())]
        if properties:
            lines += ["- Properties: " + ", ".join(sorted(set(properties)))]
        lines.append("")
    from agentic_systems._grammar import _Compiled
    returned = {"compile()": _Compiled, "RunResult.lineage()": type(toolkit.RunResult().lineage()),
                "RunResult.check_invariants()": type(toolkit.RunResult().check_invariants())}
    lines += ["## Objetos devueltos y protocolo de nodo", "",
              "No se construyen directamente. run/arun devuelven RunResult; __call__(state) en Tools/Agents/Systems es el protocolo de nodo que entrega una actualización al Graph.", ""]
    for label, cls in returned.items():
        methods = {key: signature(value) for key, value in cls.__dict__.items()
                   if not key.startswith("_") and inspect.isfunction(value)}
        surface[label] = {"methods": methods, "construction": "returned-object-only"}
        lines += ["### " + label, "", *["- " + key + sig for key, sig in sorted(methods.items())], ""]
    (ROOT / "docs/API_214_SURFACE.md").write_text("\n".join(lines), encoding="utf-8")
    (E / "api.json").write_text(json.dumps(surface, indent=2), encoding="utf-8")

    latest = {}
    result_file = sorted((E / "closure/notebook-runs").glob("*/results.json"))[-1]
    # One complete final run; never fill missing cases from an older wheel.
    for row in json.loads(result_file.read_text(encoding="utf-8")):
        assert row["profile"] == "offline"
        latest[row["path"]] = (result_file, row)
    notebook_rows = []
    used_core = set()
    for path, (result_file, row) in sorted(latest.items()):
        notebook = nbformat.read(ROOT / path, 4)
        source = "\n".join(c.source for c in notebook.cells if c.cell_type == "code")
        assert row["passed"] and hashlib.sha256(source.encode()).hexdigest() == row["code_sha256_before_parameterization"], path
        capture_path = result_file.parents[2] / row["capture"]
        capture = json.loads(capture_path.read_text(encoding="utf-8"))
        words = set(capture["grammar"]["combined"]["used"])
        used_core |= words & CORE
        calls = [{"call": ast.unparse(node.func), "line": node.lineno,
                  "positional_arguments": len(node.args), "keywords": [key.arg or "**kwargs" for key in node.keywords]}
                 for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)]
        notebook_rows.append({"path": path, "offline_passed": True, "source_code_sha256": hashlib.sha256(source.encode()).hexdigest(),
                              "core_words_observed": sorted(words & CORE), "upstream_words_observed": sorted(words & UPSTREAM),
                              "calls_and_parameters_declared": sorted(calls, key=lambda call: call["line"]),
                              "skipped_cells": row["skipped_cells"], "capture": capture_path.relative_to(ROOT).as_posix(),
                              "imports_declared": [ast.unparse(node) for node in ast.walk(ast.parse(source))
                                                   if isinstance(node, (ast.Import, ast.ImportFrom))]})
    expected = {p.relative_to(ROOT).as_posix() for p in (ROOT / "tutorials").rglob("*.ipynb")} | {
        p.relative_to(ROOT).as_posix() for p in (ROOT / "examples").rglob("*.ipynb") if "history" not in p.parts}
    assert set(latest) == expected, "Every current notebook needs final-wheel evidence"
    inventory = {"version": toolkit.__version__, "wheel_sha256": installation["wheel_sha256"], "core_denominator": len(CORE),
                 "core_observed": sorted(used_core), "notebooks": notebook_rows}
    (ROOT / "docs/NOTEBOOK_INVENTORY_214.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# Notebooks · {toolkit.__version__}", "", f"{len(notebook_rows)} notebooks ejecutados con el wheel final instalado. Las celdas live/local omitidas no están validadas. Las llamadas y parámetros del JSON son sintácticos; el vocabulario core se midió durante ejecución.", "", "| Notebook | Core observado | Celdas omitidas |", "|---|---|---:|"]
    for row in notebook_rows:
        lines.append(f"| [{row['path']}](../{row['path']}) | {', '.join(row['core_words_observed'])} | {len(row['skipped_cells'])} |")
    (ROOT / "docs/NOTEBOOK_INVENTORY_214.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    examples = json.loads((E / "closure/examples-offline.json").read_text(encoding="utf-8"))
    for row in examples["rows"]:
        if row.get("passed") is True:
            assert digest(ROOT / row["path"]) == row["source_sha256"], row["path"]
        else:
            assert row["status"] == "separate-local-protocol-profile"
    suites = ET.parse(E / "installed-suite-closure.xml").getroot()
    tests = {key: sum(int(s.get(key, 0)) for s in suites.iter("testsuite")) for key in ("tests", "failures", "errors", "skipped")}
    coverage = json.loads((E / "installed-coverage-closure.json").read_text())
    summary = {"version": toolkit.__version__, "wheel_sha256": installation["wheel_sha256"], "tests": tests,
               "core_statement_coverage": coverage["totals"]["percent_covered"],
               "coverage_scope": "SDK facade and orchestration; private _engine and templates omitted by the existing policy",
               "notebooks": len(notebook_rows), "examples_passed": sum(row.get("passed") is True for row in examples["rows"]),
               "local_protocol_profile": "prior dev7 evidence; not repeated in this closure",
               "core_observed": sorted(used_core), "core_denominator": len(CORE),
               "inference_requests": 0, "published": False, "remote_ci": "pending", "live_acceptance": "pending"}
    (E / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
