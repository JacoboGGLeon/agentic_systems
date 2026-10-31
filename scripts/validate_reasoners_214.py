"""Explicitly authorized OpenAI campaign: USD 1 AND 20 transport requests."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
wheel, site = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sys.path.insert(0, str(site))
sys.path.insert(0, str(ROOT))

import agentic_systems as toolkit  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

assert toolkit.__version__ == "2.1.4.dev1" and Path(toolkit.__file__).resolve().is_relative_to(site)
load_dotenv(ROOT / ".env", override=False)
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
os.environ["OTEL_SDK_DISABLED"] = "true"
from agents import set_tracing_disabled  # noqa: E402
set_tracing_disabled(True)

budget_source = ROOT / "examples/agentic_systems_studio/src/agentic_systems_studio/budget.py"
spec = importlib.util.spec_from_file_location("campaign_budget", budget_source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from examples.common_graph.application import build_system, CASE, check_result  # noqa: E402
from grammar_coverage_214 import Coverage, write_report  # noqa: E402

model = os.getenv("OPENAI_MODEL_ID") or os.getenv("OPENAI_MODEL")
endpoint = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
assert model == "gpt-4.1-mini", "Pricing must be reviewed before another configured model is used"
assert endpoint == "https://api.openai.com/v1" and os.getenv("OPENAI_API_KEY")
routes = {"openai-runtime": {"model": model, "endpoint": endpoint,
                           "input_usd_per_million": 0.4, "output_usd_per_million": 1.6}}
directory = ROOT / ".tmp/campaign214-dev1"
directory.mkdir(parents=True, exist_ok=True)
ledger = directory / "live-budget.json"
if not ledger.exists():
    with ledger.open("x", encoding="utf-8") as stream:
        json.dump({"schema_version": "agentic_systems.campaign-214-budget.v1",
                   "authorization": "User authorized USD 1 and 20 requests including failures, retries and evaluators, 2026-10-25",
                   "created_at": datetime.now(timezone.utc).isoformat(), "limits": {"usd": 1, "requests": 20},
                   "routes": routes, "attempts": [],
                   "pricing_source": "https://developers.openai.com/api/docs/models/gpt-4.1-mini",
                   "reservation_note": "Conservative UTF-8-byte input token ceiling + framing, output limit and 25% margin; no refunds, not billed cost."}, stream, indent=2)
budget = module.CampaignBudget(ledger, routes, "214-pilot", usd=1, requests=20)
budget.install()  # Deliberately remains installed for late workers until process exit.
reasoner = toolkit.runtime(provider="openai-runtime", model=model, endpoint=endpoint,
    api_key=os.environ["OPENAI_API_KEY"], max_tokens=512, max_turns=2, max_tool_calls=0,
    max_retries=0, timeout_s=45)
coverage = Coverage()
report_path = ROOT / "revisions/2.1.4/live-results.json"
existing = json.loads(report_path.read_text()) if report_path.exists() else None
attempts = existing.get("attempts", []) if existing else []
snapshot = {"wheel": wheel.name, "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    "budget_implementation_sha256": hashlib.sha256(budget_source.read_bytes()).hexdigest(),
    "source_sha256": hashlib.sha256((ROOT / "examples/common_graph/application.py").read_bytes()).hexdigest(),
    "routes": routes, "input": CASE, "oracle": "R-17; missing_units=1; refund=120 MXN; packing-slip + customer-report sources; valid JSON and invariants",
    "matrix": [{"backend": b, "framework": f} for b in ("native", "langgraph") for f in ("native", "openai-agents", "strands")]}
frozen = directory / ("frozen-plan-" + str(len(attempts) + 1) + ".json")
with frozen.open("x", encoding="utf-8") as stream:
    json.dump(snapshot, stream, ensure_ascii=False, indent=2)


def execute(backend, framework, phase):
    budget.phase = phase
    before = budget.summary()["attempts"]
    started = time.monotonic()
    with coverage.example("common_graph/OpenAI-real"):
        definition = build_system(backend, framework, reasoner=reasoner, interactive=backend == "langgraph")
        program = definition.compile()
        first = program.run(CASE, limits=toolkit.Limits(max_actions=30, timeout_s=100))
        before_resume = budget.summary()["attempts"]
        output = program.resume(first, True) if first.status == "paused" else first
        after_resume = budget.summary()["attempts"]
        # Evaluate the actual captured result without a second candidate/model call.
        captured = toolkit.Agent("captured-result", toolkit.Action("capture", lambda d: toolkit.RunResult(**output.to_dict())))
        evaluation = toolkit.Eval("captured-refund-contract", captured,
            ({"input": CASE, "expected": {"ok": True}},), checks=(lambda result, case: {"ok": check_result(result)},)).run()
    passed = check_result(output) and evaluation.ok and before_resume == after_resume
    if backend == "langgraph":
        passed = passed and first.status == "paused" and output.data.get("status") == "approved"
    else:
        passed = passed and first.status == "completed" and output.data.get("status") == "pending_review"
    row = {"phase": phase, "backend": backend, "framework": framework, "provider": "openai-runtime", "model": model,
           "passed": passed, "elapsed_s": round(time.monotonic() - started, 3),
           "transport_requests": after_resume - before, "requests_during_resume": after_resume - before_resume,
           "input": CASE, "process": ["normalize", "OpenAI interpretation", "Python price + policy", "review/approve"],
           "usage": output.usage,
           "output": output.data, "run_results": [first.to_dict(), output.to_dict(), evaluation.to_dict()],
           "lineage": output.lineage(name="R-17").to_dict(), "human_lineage": output.lineage(name="R-17").render(),
           "memory": definition.memory.read()}
    print(json.dumps({k: row[k] for k in ("phase", "backend", "framework", "passed", "transport_requests", "requests_during_resume")}), flush=True)
    return row


current = {"frozen_plan": str(frozen.relative_to(ROOT)), **snapshot, "rows": []}
attempts.append(current)


def save():
    summary = {"version": toolkit.__version__, "published": False, "attempts": attempts,
               "budget": budget.summary(), "status": "passed" if len(current["rows"]) == 7 and all(r["passed"] for r in current["rows"]) else "incomplete-or-failed"}
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "revisions/2.1.4/live-budget.json").write_bytes(ledger.read_bytes())
    combined = coverage.report()
    (ROOT / "revisions/2.1.4/live-grammar-coverage.json").write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
    offline = json.loads((ROOT / "revisions/2.1.4/grammar-coverage.json").read_text())
    for name, row in combined["examples"].items():
        offline["examples"][name] = row
    used = sorted({word for row in offline["examples"].values() for word in row["used"]})
    offline["combined"] = {"used": used, "count": len(used), "total": len(offline["public_root_words"]),
                           "unused": sorted(set(offline["public_root_words"]) - set(used))}
    (ROOT / "revisions/2.1.4/grammar-coverage.json").write_text(json.dumps(offline, indent=2) + "\n", encoding="utf-8")
    write_report(offline, ROOT / "docs/GRAMMAR_COVERAGE_214.md")


try:
    pilot = execute("native", "native", "214-pilot")
    current["rows"].append(pilot)
    save()
    if not pilot["passed"]:
        raise RuntimeError("Pilot failed; acceptance was not run")
    for route in snapshot["matrix"]:
        current["rows"].append(execute(**route, phase="214-acceptance"))
        save()
finally:
    save()
assert len(current["rows"]) == 7 and all(row["passed"] for row in current["rows"]), "Failures retained; do not declare the matrix validated"
print(json.dumps(budget.summary()), flush=True)
