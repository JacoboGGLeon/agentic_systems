"""Run canonical examples against an installed wheel, with application I/O blocked."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tutorials"))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "scripts"))
from _offline import enforce_offline, blocked_attempts  # noqa: E402

enforce_offline()
import agentic_systems as toolkit  # noqa: E402
import capture_runresults_213 as capture  # noqa: E402
capture.install()

assert toolkit.__version__ == "2.1.3" and "site-packages" in Path(toolkit.__file__).parts
names = ("tool_contracts", "portable_skills", "flow_semantics", "execution_lifecycle", "results_lineage",
         "episode_memory", "evaluation_checks", "provider_framework_conformance", "model_serving", "package_install", "agent_contracts",
         "grammar_tour", "framework_interop", "api_walkthrough", "order_fulfillment")
reports = []
for name in names:
    capture.clear()
    source = ROOT / "examples" / name / "example.py"
    base = os.environ.get('AGENTIC_213_EVIDENCE_DIR')
    evidence = ROOT / base / 'example-results' / name if base else source.parent / 'evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    try:
        report = importlib.import_module(name + ".example").run()
    finally:
        capture.save(evidence / 'runresults.json', 'examples/' + name)
    entry = {"example": name, "passed": True, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "report": report}
    previous = evidence / 'run.json'
    if previous.exists():
        archive = evidence / 'previous'
        archive.mkdir(exist_ok=True)
        target = archive / (hashlib.sha256(previous.read_bytes()).hexdigest() + '.json')
        if not target.exists():
            target.write_bytes(previous.read_bytes())
    (evidence / "run.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reports.append(entry)
    print(json.dumps({"example": name, "passed": True}), flush=True)
assert blocked_attempts() == 0
destination = ROOT / os.environ.get("AGENTIC_213_EVIDENCE_DIR", "revisions/2.1.3/implementation-evidence")
destination.mkdir(exist_ok=True)
(destination / "examples.json").write_text(json.dumps({"version": toolkit.__version__, "inference_requests": 0,
    "blocked_attempts": blocked_attempts(), "reports": reports}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
