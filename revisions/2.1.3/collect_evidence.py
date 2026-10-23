"""Bind completed offline checks to the installed candidate wheel; no providers."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

import agentic_systems as toolkit

HOME = Path(__file__).resolve().parent
ROOT = HOME.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def passed_tests(path, expected):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    assert sum(int(s.get("tests", 0)) for s in suites) == expected
    assert all(int(s.get(key, 0)) == 0 for s in suites for key in ("failures", "errors", "skipped"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    assert toolkit.__version__ == importlib.metadata.version("agentic-systems") == "2.1.3"
    build = json.loads((args.build / "manifest.json").read_text())
    wheel = Path(build["wheel"])
    assert digest(wheel) == build["sha256"]
    installed = Path(toolkit.__file__).resolve().parent.parent
    assert "site-packages" in installed.parts
    with zipfile.ZipFile(wheel) as archive:
        files = [n for n in archive.namelist() if n.startswith("agentic_systems/") and not n.endswith("/")]
        assert files
        for name in files:
            assert (installed / name).read_bytes() == archive.read(name), name
        for retired in ("agents.py", "system.py", "factories.py", "api_contract.py", "core/agents.py"):
            assert "agentic_systems/" + retired not in files
        assert not any("/compat/" in n or "unified_grammar" in n for n in files)
    passed_tests(HOME / "evidence/tests.xml", 24)
    passed_tests(args.project / "evidence/tests.xml", 12)
    tutorials = json.loads((HOME / "evidence/tutorials.json").read_text())
    assert len(tutorials["notebooks"]) == 10
    for row in tutorials["notebooks"]:
        assert row["passed"]
        assert digest(ROOT / "tutorials" / row["notebook"]) == row["source_sha256"]
        assert digest(HOME / "evidence/tutorials" / row["notebook"]) == row["executed_sha256"]
    canonical = json.loads((ROOT / "examples/order_fulfillment/evidence/run.json").read_text(encoding="utf-8"))
    assert [r["cases_passed"] for r in canonical["reports"]] == [7, 7]
    generated = json.loads((args.project / "evidence/challenge.json").read_text(encoding="utf-8"))
    assert [r["cases_passed"] for r in generated["reports"]] == [7, 7]
    notebook = args.project / "notebooks/01_order_challenge.ipynb"
    code = [c for c in json.loads(notebook.read_text(encoding="utf-8"))["cells"] if c["cell_type"] == "code"]
    assert len(code) == 1 and all(c["execution_count"] is not None for c in code)
    assert not any(o["output_type"] == "error" for c in code for o in c["outputs"])
    artifacts = HOME / "artifacts"
    artifacts.mkdir(exist_ok=True)
    saved_wheel = artifacts / wheel.name
    shutil.copyfile(wheel, saved_wheel)
    generated_evidence = HOME / "evidence/generated-project"
    generated_evidence.mkdir(exist_ok=True)
    for source in (args.project / "evidence/challenge.json", args.project / "evidence/tests.xml", notebook):
        shutil.copyfile(source, generated_evidence / source.name)
    # Keep a pristine generated project: all notebooks unexecuted, status not-run.
    from agentic_systems.scaffolding import create_project
    clean = args.build / "generated-project"
    create_project(clean)
    shutil.make_archive(str(artifacts / "order_fulfillment_213"), "zip", root_dir=clean)
    manifest = {
        "version": "2.1.3", "status": "offline-validated-candidate-not-published",
        "wheel": "artifacts/" + wheel.name, "wheel_sha256": digest(saved_wheel),
        "installed_package_bytes_verified": len(files), "source_sha256": build["source_sha256"],
        "python": sys.version.split()[0],
        "dependencies": {name: importlib.metadata.version(name) for name in ("langgraph", "openai-agents", "strands-agents", "nbclient", "pytest")},
        "public_api": toolkit.__all__, "sdk_tests": 24, "tutorial_notebooks": 10,
        "tutorial_code_cells": sum(r["code_cells"] for r in tutorials["notebooks"]),
        "challenge_cases": 14, "generated_project_tests": 12, "generated_project_notebook_code_cells": 1,
        "backends": ["native", "langgraph"],
        "frameworks_python_runtime": ["native", "langgraph", "openai-agents", "strands"],
        "inference_requests": 0, "external_providers": "configured-only-not-run",
        "release_integration": "pending", "full_release_certification": "not-run",
    }
    manifest["evidence_sha256"] = {
        p.relative_to(HOME).as_posix(): digest(p)
        for p in sorted((HOME / "evidence").rglob("*"))
        if p.is_file() and p.name not in ("manifest.json", "REPORT.md")
    }
    manifest["scaffold_zip_sha256"] = digest(artifacts / "order_fulfillment_213.zip")
    (HOME / "evidence/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    catalog_path = ROOT / "examples/catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    for entry in catalog["entries"]:
        if entry["id"] not in ("order_fulfillment_213", "api_213_tutorials"):
            continue
        entry["readiness"] = "implemented; offline-validated against the local 2.1.3 wheel"
        scope = ("14 contracts (seven per backend), Environment, deterministic Eval and expected negative controls. "
                 if entry["id"] == "order_fulfillment_213" else
                 "Ten fresh-kernel notebooks, 39 code cells; four frameworks with Python Runtime. ")
        entry["validation"] = {
            "status": "offline-only", "wheel_sha256": manifest["wheel_sha256"],
            "scope": scope + "Exact non-editable wheel bytes verified. 24 SDK tests; generated project: 14 contracts, 12 tests and one notebook code cell. No external inference or release certification.",
            "evidence": [{"label": "Measured candidate report", "target": "revisions/2.1.3/evidence/REPORT.md"},
                         {"label": "Artifact and evidence hashes", "target": "revisions/2.1.3/evidence/manifest.json"}],
        }
        entry["next_action"] = "Promote this single API into the root build and release workflows, validate release gates, and obtain separate authorization before any external inference."
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in manifest.items() if k not in ("source_sha256", "evidence_sha256")}, indent=2))


if __name__ == "__main__":
    main()
