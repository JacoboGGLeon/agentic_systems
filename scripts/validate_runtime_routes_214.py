"""Bounded real runtime campaign on the immutable dev2 wheel; no publication."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--bedrock-strands-only", action="store_true", help="Test only the not-yet-run Bedrock/Strands cell; never retry failed cells")
arguments = parser.parse_args()
cells = [("bedrock-runtime", "strands")] if arguments.bedrock_strands_only else [
    (route, framework) for route in ("python", "openai-runtime", "bedrock-runtime", "ollama-gpu")
    for framework in ("native", "openai-agents", "strands")]
SITE = ROOT / ".tmp/candidate214-dev2/site-packages"
WHEEL = ROOT / "revisions/2.1.4/candidate/agentic_systems-2.1.4.dev2-py3-none-any.whl"
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402
import agentic_systems as toolkit  # noqa: E402
from langgraph.graph import StateGraph, START, END  # noqa: E402
from examples.common_graph.application import build_system, CASE, check_result, RefundOutput  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
assert toolkit.__version__ == "2.1.4.dev2" and Path(toolkit.__file__).resolve().is_relative_to(SITE)
sha = hashlib.sha256(WHEEL.read_bytes()).hexdigest()
assert sha == json.loads((ROOT / "revisions/2.1.4/closeout.json").read_text(encoding="utf-8"))["wheel_sha256"]
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
os.environ["OTEL_SDK_DISABLED"] = "true"
from agents import set_tracing_disabled  # noqa: E402
set_tracing_disabled(True)

source = ROOT / "examples/agentic_systems_studio/src/agentic_systems_studio/budget.py"
spec = importlib.util.spec_from_file_location("runtime_campaign_budget", source)
budget_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget_module)
ledger_path = ROOT / ".tmp/campaign214-dev1/live-budget.json"
region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
gpu_model = "qwen3:4b-instruct-2507-q4_K_M"
routes = {
    "openai-runtime": {"model": os.getenv("OPENAI_MODEL_ID") or os.environ["OPENAI_MODEL"],
        "endpoint": "https://api.openai.com/v1", "input_usd_per_million": 0.4, "output_usd_per_million": 1.6},
    "bedrock-runtime": {"model": os.environ["BEDROCK_MODEL_ID"], "endpoint": f"https://bedrock-runtime.{region}.amazonaws.com",
        "input_usd_per_million": 1, "output_usd_per_million": 4},
    "ollama-gpu": {"model": gpu_model, "endpoint": "http://127.0.0.1:11434/v1",
        "input_usd_per_million": 0, "output_usd_per_million": 0},
}
assert routes["openai-runtime"]["model"] == "gpt-4.1-mini"
assert routes["bedrock-runtime"]["model"] == "qwen.qwen3-32b-v1:0"
budget = budget_module.CampaignBudget(ledger_path, routes, "214-dev2-runtimes", usd=1, requests=20)
evidence = ROOT / "revisions/2.1.4/runtime-evidence"
evidence.mkdir(exist_ok=True)
with budget.locked():
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["limits"] == {"usd": 1, "requests": 20}
    if ledger["routes"] != routes:
        # Explicit new user request authorizes additional routes; cap and attempts remain.
        before_sha = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
        ledger.setdefault("route_history", []).append({"after_attempt": len(ledger["attempts"]),
            "previous_ledger_sha256": before_sha, "previous_routes": ledger["routes"], "new_routes": routes,
            "authorization": "User requested six runtimes and Qwen-only non-OpenAI models, 2026-10-25",
            "created_at": datetime.now(timezone.utc).isoformat()})
        ledger["routes"] = routes
        temporary = ledger_path.with_suffix(".pending")
        temporary.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, ledger_path)
initial = budget.summary()
plan = {"version": toolkit.__version__, "wheel_sha256": sha, "initial_budget": initial, "routes": routes,
        "scheduled_cells": cells,
        "case": CASE, "orchestration": "langgraph", "frameworks": ["native", "openai-agents", "strands"],
        "oracle": "missing_units=1, refund=120 MXN, approved; packing-slip+customer-report; JSON, invariants; zero calls on resume",
        "blocked_routes": {"ollama-api-key": "Authenticated cloud catalog contains no Qwen model; Gemma excluded by explicit user preference",
                           "vllm-gpu": "Configured endpoint unavailable; no vLLM/WSL installed; user confirms no remote endpoint"},
        "pricing_note": "OpenAI reviewed price; Bedrock conservative ceiling 1/4 USD per MT, higher than published Qwen3 32B rates; local GPU costs zero API USD but counts requests",
        "pricing_sources": ["https://developers.openai.com/api/docs/models/gpt-4.1-mini", "https://aws.amazon.com/bedrock/pricing/"]}
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
destination = evidence / stamp
destination.mkdir()
(destination / "frozen-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
budget.install()  # Remains active, including late SDK workers, until process exit.
rows = []


def runtime_for(route):
    if route == "python":
        return None
    config = routes[route]
    provider = "ollama-runtime" if route == "ollama-gpu" else route
    key = os.environ["OPENAI_API_KEY"] if route == "openai-runtime" else os.environ["AWS_BEARER_TOKEN_BEDROCK"] if route == "bedrock-runtime" else "ollama-local"
    if route == "ollama-gpu":
        os.environ["OLLAMA_BASE_URL"] = config["endpoint"]
        os.environ["OLLAMA_MODEL"] = config["model"]
        os.environ["OLLAMA_API_KEY"] = key
    return toolkit.runtime(provider=provider, model=config["model"], endpoint=config["endpoint"],
        region=region if provider == "bedrock-runtime" else None, api_key=key,
        max_tokens=1024, max_turns=2, max_tool_calls=0, max_retries=0, timeout_s=90)


def gpu_inventory():
    # This GET observes memory placement; it cannot generate text or bypass a model cap.
    with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=5) as response:
        payload = json.loads(response.read())
    return [{k: value for k, value in row.items() if k in {"name", "model", "digest", "size", "size_vram", "context_length"}}
            for row in payload.get("models", [])]


def save():
    report = {**plan, "rows": rows, "budget": budget.summary(), "published": False}
    for path in (destination / "results.json", evidence / "latest.json"):
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destination / "budget.json").write_bytes(ledger_path.read_bytes())


try:
    blocked = set()
    for route, framework in cells:
        if route not in blocked:
            budget.phase = route + "/" + framework
            before = budget.summary()["attempts"]
            started = time.monotonic()
            program = build_system(framework, reasoner=runtime_for(route), interactive=True).compile()
            waiting = program.run(CASE, limits=toolkit.Limits(max_actions=100, timeout_s=150))
            prior_resume = budget.summary()["attempts"]
            final = program.resume(waiting, True) if waiting.status == "paused" else waiting
            after = budget.summary()["attempts"]
            captured = StateGraph(RefundOutput)
            captured.add_node("capture", lambda state: toolkit.RunResult(**final.to_dict()))
            captured.add_edge(START, "capture")
            captured.add_edge("capture", END)
            evaluation = toolkit.Eval("actual-runtime-result", toolkit.Agent("captured", graph=captured),
                ({"input": CASE, "expected": {"ok": True}},), checks=(lambda result, case: {"ok": check_result(result)},)).run()
            passed = check_result(final) and evaluation.ok and waiting.status == "paused" and after == prior_resume
            row = {"route": route, "framework": framework, "orchestration": "langgraph", "passed": passed,
                   "model": "python-runtime" if route == "python" else routes[route]["model"],
                   "elapsed_s": round(time.monotonic() - started, 3), "requests": after - before,
                   "requests_during_resume": after - prior_resume, "output": final.data,
                   "run_results": [waiting.to_dict(), final.to_dict(), evaluation.to_dict()],
                   "human_lineage": final.lineage(name=route).render(), "agent_lineage": final.lineage().to_prompt_context()}
            if route == "ollama-gpu":
                row["gpu_inventory"] = gpu_inventory()
                row["gpu_verified"] = any(m.get("name") == gpu_model and m.get("size_vram", 0) > 0 for m in row["gpu_inventory"])
                row["passed"] = row["passed"] and row["gpu_verified"]
            rows.append(row)
            save()
            print(json.dumps({k: row[k] for k in ("route", "framework", "passed", "requests", "requests_during_resume")}), flush=True)
            if route == "python" and not row["passed"]:
                raise RuntimeError("Deterministic control failed; live validation blocked")
            if route != "python" and not row["passed"]:
                # Stop this route after its first failure; no model substitution or blind retry.
                blocked.add(route)
finally:
    save()
print(json.dumps(budget.summary()), flush=True)
