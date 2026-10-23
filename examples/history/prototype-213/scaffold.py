"""Generate a complete offline project for the 2.1.3 API revision candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HOME = Path(__file__).resolve().parent


def create_project(destination):
    destination = Path(destination).resolve()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Choose a new destination; existing projects are never overwritten")
    if destination.is_relative_to(HOME):
        raise ValueError("Generate outside the prototype source directory")
    destination.mkdir(parents=True)
    for source in (HOME / "scaffold_template").rglob("*"):
        if source.is_file() and "__pycache__" not in source.parts:
            target = destination / source.relative_to(HOME / "scaffold_template")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for source in (HOME / "order_challenge").rglob("*"):
        if source.is_file() and source.suffix in {".py", ".json"} and "__pycache__" not in source.parts:
            target = destination / "src/order_challenge" / source.relative_to(HOME / "order_challenge")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    support = destination / "src/unified_grammar"
    support.mkdir(parents=True)
    for name in ("__init__.py", "core.py", "offline.py"):
        shutil.copyfile(HOME / name, support / name)
    tests = destination / "tests"
    tests.mkdir()
    test_source = (HOME / "tests/test_order_challenge.py").read_text(encoding="utf-8")
    (tests / "test_contract.py").write_text(
        test_source.replace("unified_grammar.order_challenge", "order_challenge"), encoding="utf-8"
    )
    evidence = destination / "evidence"
    evidence.mkdir()
    (evidence / "README.md").write_text(
        "Generated template: no acceptance is claimed until app.py and tests execute.\n", encoding="utf-8"
    )
    document = HOME.parents[1] / "docs/SCAFFOLDER_213.md"
    if document.is_file():
        (destination / "docs").mkdir()
        shutil.copyfile(document, destination / "docs/SCAFFOLDER_213.md")
    license_path = HOME.parents[1] / "LICENSE"
    if license_path.is_file():
        shutil.copyfile(license_path, destination / "LICENSE")
    notebook = json.loads((HOME / "00_walkthrough.ipynb").read_text(encoding="utf-8"))
    setup = '''from pathlib import Path
import sys, json, html
from IPython.display import HTML, display
project_root = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "app.py").is_file())
sys.path.insert(0, str(project_root / "src"))
from unified_grammar.offline import enforce_offline
enforce_offline()
import agentic_systems as toolkit
from unified_grammar import Environment, Eval
assert toolkit.__version__ == "2.1.2"
BACKENDS = ("native", "langgraph")
def render_io(backend, payload, process, output, status="PASS"):
    headers = ("Backend", "Input", "Proceso observado", "Output", "Estado")
    values = (backend, payload, process, output, status)
    display(HTML("<table><tr>" + "".join(f"<th>{h}</th>" for h in headers)
                 + "</tr><tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in values)
                 + "</tr></table>"))
def observed_process(result):
    return "; ".join(f"{n.meta['name']}: {n.data}" for n in result.walk()
                     if n.meta.get("prototype_kind") == "action")
'''
    cells = [{"cell_type": "markdown", "id": "intro", "metadata": {},
              "source": ["# Proyecto generado — revisión de API 2.1.3\n", "Kernel dedicado, ejecución offline, baseline publicado 2.1.2."]},
             {"cell_type": "code", "id": "setup", "metadata": {}, "execution_count": None,
              "outputs": [], "source": setup.splitlines(keepends=True)}]
    for cell in notebook["cells"]:
        if "order-challenge" not in cell["metadata"].get("tags", []):
            continue
        copied = json.loads(json.dumps(cell))
        source = "".join(copied["source"]).replace("unified_grammar.order_challenge", "order_challenge")
        source = source.replace('source_root / "unified_grammar/evidence/challenge.json"',
                                'project_root / "evidence/challenge-notebook.json"')
        copied["source"] = source.splitlines(keepends=True)
        if copied["cell_type"] == "code":
            copied["execution_count"], copied["outputs"] = None, []
        cells.append(copied)
    if len(cells) < 8:
        raise ValueError("Build the challenge walkthrough before generating its project")
    notebook.update(cells=cells)
    (destination / "notebooks").mkdir()
    (destination / "notebooks/01_order_challenge.ipynb").write_text(
        json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "target_version": "2.1.3", "status": "offline-api-revision-candidate",
        "base_distribution": {"name": "agentic-systems", "version": "2.1.2",
                              "wheel_sha256": "2c14a8e6f871fcc455acbf899db851130c49a129ba988821d6656e90ebc3d47b"},
        "grammar_module": "unified_grammar", "declaration": "order_challenge.system:build_system",
        "backends": ["native", "langgraph"], "provider": "python-runtime",
        "inference_permitted": False, "validation": "not-run-generated-project",
        "copied_grammar_source_sha256": {
            name: hashlib.sha256((support / name).read_bytes()).hexdigest()
            for name in ("__init__.py", "core.py", "offline.py")
        },
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    hashes = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(destination).as_posix()}\n"
              for p in sorted(destination.rglob("*")) if p.is_file()]
    (destination / "SHA256SUMS.txt").write_text("".join(hashes), encoding="utf-8")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    print(create_project(arguments.destination))
