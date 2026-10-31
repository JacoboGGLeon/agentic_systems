"""Repeat only the two authorized Bedrock/Qwen cells, on the fixed dev3 wheel."""
import atexit
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / ".tmp/candidate214-dev3/site-packages"
EVIDENCE = ROOT / "revisions/2.1.4/json-markdown-fix"
WHEEL = EVIDENCE / "candidate/agentic_systems-2.1.4.dev3-py3-none-any.whl"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SITE))
from dotenv import load_dotenv  # noqa: E402
import agentic_systems as toolkit  # noqa: E402
from langgraph.graph import StateGraph, START, END  # noqa: E402
from examples.common_graph.application import CASE, RefundOutput, build_system, check_result  # noqa: E402

assert toolkit.__version__ == "2.1.4.dev3"
assert Path(toolkit.__file__).resolve().is_relative_to(SITE)
artifact = json.loads((EVIDENCE / "artifact.json").read_text(encoding="utf-8"))
assert hashlib.sha256(WHEEL.read_bytes()).hexdigest() == artifact["wheel_sha256"]
with zipfile.ZipFile(WHEEL) as archive:
    assert all((SITE / name).read_bytes() == archive.read(name)
               for name in archive.namelist() if name.startswith("agentic_systems/") and not name.endswith("/"))
suites = list(ET.parse(EVIDENCE / "offline-junit.xml").getroot().iter("testsuite"))
assert sum(int(s.attrib["tests"]) for s in suites) == 120
assert all(int(s.attrib.get(k, 0)) == 0 for s in suites for k in ("failures", "errors", "skipped"))
assert not (EVIDENCE / "live-plan.json").exists(), "This campaign is one-shot; never overwrite attempts"

load_dotenv(ROOT / ".env", override=False)
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
os.environ["OTEL_SDK_DISABLED"] = "true"
from agents import set_tracing_disabled  # noqa: E402
set_tracing_disabled(True)
ledger = ROOT / ".tmp/campaign214-dev1/live-budget.json"
before = json.loads(ledger.read_text(encoding="utf-8"))
snapshot = json.loads((EVIDENCE / "budget-before.json").read_text(encoding="utf-8"))
assert before["attempts"][:len(snapshot["attempts"])] == snapshot["attempts"]
assert before["limits"] == {"usd": 1, "requests": 20}
route = before["routes"]["bedrock-runtime"]
assert route["model"] == os.environ["BEDROCK_MODEL_ID"] == "qwen.qwen3-32b-v1:0"
region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
assert region == "us-east-2" and route["endpoint"] == f"https://bedrock-runtime.{region}.amazonaws.com"
key = os.environ["AWS_BEARER_TOKEN_BEDROCK"]

source = ROOT / "examples/agentic_systems_studio/src/agentic_systems_studio/budget.py"
spec = importlib.util.spec_from_file_location("json_fix_budget", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
budget = module.CampaignBudget(ledger, before["routes"], "214-dev3-json-fix", **before["limits"])
initial = budget.summary()
assert initial["remaining_requests"] >= 2

# A second cap scopes this request to two transmissions, within the existing
# persistent allocation. SDK retries and late workers cannot consume a third.
reserve = budget.reserve
transmission_lock = threading.Lock()
def reserve_two(url, body, *, bearer=False):
    with transmission_lock:
        if budget.summary()["attempts"] - initial["attempts"] >= 2:
            raise module.BudgetExceeded("Only two transmissions authorized for this repeat")
        return reserve(url, body, bearer=bearer)
budget.reserve = reserve_two
rows = []
plan = {**artifact, "initial_budget": initial, "model": route["model"], "region": region,
        "endpoint": route["endpoint"], "orchestration": "langgraph", "frameworks": ["openai-agents", "strands"],
        "max_transmissions_this_repeat": 2, "case": CASE,
        "oracle": "one missing unit; 120 MXN; approved; JSON schema; lineage invariants; no model call on resume",
        "runtime": {"max_tokens": 1024, "max_turns": 2, "max_tool_calls": 0, "max_retries": 0, "timeout_s": 90},
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "application_sha256": hashlib.sha256((ROOT / "examples/common_graph/application.py").read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "pricing": "Unchanged conservative ledger ceiling: input 1, output 4 USD per million tokens, plus margin; reservation is not invoice"}
(EVIDENCE / "live-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def save():
    (EVIDENCE / "live-results.json").write_text(json.dumps({**plan, "rows": rows,
        "budget": budget.summary(), "published": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EVIDENCE / "budget-after.json").write_bytes(ledger.read_bytes())

# CPython joins ThreadPoolExecutor workers before user atexit handlers. Hooks
# remain installed until exit; the final snapshot also includes late responses.
atexit.register(save)
budget.install()
try:
    for framework in plan["frameworks"]:
        budget.phase = "214-dev3-json-fix/" + framework
        count = budget.summary()["attempts"]
        started = time.monotonic()
        row = {"framework": framework, "provider": "bedrock-runtime", "model": route["model"],
               "wheel_sha256": artifact["wheel_sha256"], "passed": False}
        try:
            runtime = toolkit.runtime(provider="bedrock-runtime", model=route["model"], region=region,
                endpoint=route["endpoint"], api_key=key, **plan["runtime"])
            definition = build_system(framework, reasoner=runtime, interactive=True)
            row["inspection"] = definition.inspect()
            program = definition.compile()
            waiting = program.run(CASE, limits=toolkit.Limits(max_actions=100, timeout_s=150))
            at_resume = budget.summary()["attempts"]
            final = program.resume(waiting, True) if waiting.status == "paused" else waiting
            after = budget.summary()["attempts"]
            captured = StateGraph(RefundOutput)
            captured.add_node("actual-result", lambda state: toolkit.RunResult(**final.to_dict()))
            captured.add_edge(START, "actual-result")
            captured.add_edge("actual-result", END)
            evaluation = toolkit.Eval("real-refund-contract", toolkit.Agent("captured", graph=captured),
                ({"input": CASE, "expected": {"ok": True}},),
                checks=(lambda result, case: {"ok": check_result(result)},)).run()
            actor = [n for n in final.walk() if n.model == route["model"] and not n.children]
            row.update({"passed": (check_result(final) and final.data.get("status") == "approved" and evaluation.ok
                and waiting.status == "paused" and after == at_resume and after - count == 1),
                "output": final.data, "requests": after - count, "requests_during_resume": after - at_resume,
                "raw_actor_text": [n.text for n in actor],
                "run_results": [waiting.to_dict(), final.to_dict(), evaluation.to_dict()],
                "human_lineage": final.lineage(name="Qwen / " + framework).render(),
                "agent_lineage": final.lineage().to_prompt_context()})
        except Exception as exc:
            row["exception"] = {"type": type(exc).__name__, "message": str(exc).replace(key, "[REDACTED]")}
        row["elapsed_s"] = round(time.monotonic() - started, 3)
        rows.append(row)
        save()
        print(json.dumps({k: row.get(k) for k in ("framework", "passed", "requests", "requests_during_resume", "exception")}), flush=True)
finally:
    save()
print(json.dumps(budget.summary()), flush=True)
