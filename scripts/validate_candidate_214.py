"""Exercise the installed development wheel and record bounded offline evidence."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
wheel, site = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sys.path.insert(0, str(site))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tutorials"))
from _offline import enforce_offline, blocked_attempts  # noqa: E402

enforce_offline()
import agentic_systems as toolkit  # noqa: E402
from grammar_coverage_214 import Coverage, write_report  # noqa: E402

assert toolkit.__version__ == "2.1.4.dev2"
assert Path(toolkit.__file__).resolve().is_relative_to(site), toolkit.__file__
with zipfile.ZipFile(wheel) as archive:
    assert not any("__pycache__" in name or name.endswith(".pyc") or name.endswith("/.env") for name in archive.namelist())
    assert all((site / name).read_bytes() == archive.read(name)
               for name in archive.namelist() if name.startswith("agentic_systems/") and not name.endswith("/"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


evidence = ROOT / "revisions/2.1.4"
evidence.mkdir(parents=True, exist_ok=True)
coverage = Coverage()
with coverage.example("context_memory_lineage/application.py"):
    from examples.context_memory_lineage import demonstrate
    reports = [demonstrate()]
with coverage.example("common_graph/application.py"):
    from examples.common_graph.application import demonstrate as graph_demo
    adapters = [graph_demo(name) for name in ("native", "openai-agents", "strands")]
with coverage.example("common_graph/resources.py"):
    from examples.common_graph.resources import loaded_skill_example, serving_example
    resources_report = {"load_skill": loaded_skill_example(), "serving": serving_example()}

kernel = json.loads((site.parent / "kernel-notebooks.json").read_text(encoding="utf-8"))
assert kernel["wheel_sha256"] == digest(wheel)
notebooks = kernel["rows"]
for row in notebooks:
    assert row["passed"] and digest(ROOT / row["path"]) == row["sha256"]
    captured = json.loads((site.parent / row["capture"]).read_text(encoding="utf-8"))
    assert captured["blocked_attempts"] == 0
    coverage.rows[row["path"]] = set(captured["grammar"]["combined"]["used"])
assert blocked_attempts() == 0
coverage_report = coverage.report()
(evidence / "grammar-coverage.json").write_text(json.dumps(coverage_report, indent=2) + "\n", encoding="utf-8")
write_report(coverage_report, ROOT / "docs/GRAMMAR_COVERAGE_214.md")

junit = ET.parse(site.parent / "offline-junit.xml").getroot()
suites = list(junit.iter("testsuite"))
tests = {key: sum(int(s.attrib.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
assert tests["failures"] == tests["errors"] == tests["skipped"] == 0

payload = {"version": toolkit.__version__, "installed_package": str(Path(toolkit.__file__).resolve()),
           "wheel": wheel.name, "wheel_sha256": digest(wheel), "reports": reports, "python_frameworks": adapters, "resources": resources_report}
results_path = evidence / "example-results.json"
results_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

sources = [ROOT / "pyproject.toml", *sorted((ROOT / "src/agentic_systems").rglob("*.py")),
           *sorted((ROOT / "tests/v214_graph").rglob("*.py")), ROOT / "examples/context_memory_lineage/application.py", *sorted((ROOT / "examples/common_graph").rglob("*.py")), *sorted((ROOT / "examples/common_graph/skills").rglob("*.md")),
           ROOT / "docs/CONTRACTS_214.md", ROOT / "docs/GRAMMAR_214.md"]
source_hashes = {p.relative_to(ROOT).as_posix(): digest(p) for p in sources}
validation = {"version": toolkit.__version__, "status": "langgraph-only-offline-passed", "published": False,
              "base_commit": "a20440cc6bf41b28c1b454bb87ba13cee6bad9d6",
              "source_state": "uncommitted development branch; source hashes identify this snapshot",
              "python": platform.python_version(), "installed_package": str(Path(toolkit.__file__).resolve()),
              "wheel": wheel.name, "wheel_sha256": digest(wheel), "tests": tests,
              "offline_guard_blocked_attempts": blocked_attempts(), "real_inference_requests": 0,
              "notebooks": notebooks,
              "orchestration": "langgraph", "python_frameworks": ["native", "openai-agents", "strands"],
              "grammar_coverage": coverage_report["combined"],
              "dependencies": {name: importlib.metadata.version(name) for name in ("langgraph", "openai-agents", "strands-agents")},
              "example_results_sha256": digest(results_path), "source_sha256": source_hashes,
              "not_validated": ["live language models on dev2", "real vLLM/GPU startup and inference", "MCP/A2A remote", "Studio", "persistent memory", "interactive reset/step", "entire 2.1.3 notebook catalog", "Python 3.10-3.13"]}
(evidence / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: validation[k] for k in ("version", "status", "wheel_sha256", "tests", "real_inference_requests", "python_frameworks")}, indent=2))
