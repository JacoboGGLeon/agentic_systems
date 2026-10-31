"""Dev5 acceptance on one installed wheel, using the authorized USD5/150 ledger."""
import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from bedrock_key_format_214 import inspect_key

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "revisions/2.1.4/contracts-dev5"
SITE = ROOT / ".tmp/candidate214-dev5-build02/site-packages"
WHEEL = E / "builds/02/agentic_systems-2.1.4.dev5-py3-none-any.whl"
sys.path[:0] = [str(SITE), str(ROOT), str(ROOT / "examples/agentic_systems_studio/src")]
os.environ.update(OPENAI_AGENTS_DISABLE_TRACING="1", OTEL_SDK_DISABLED="true")
from dotenv import load_dotenv, dotenv_values  # noqa: E402
import agentic_systems as toolkit  # noqa: E402
from agentic_systems_studio.budget import ensure_budget  # noqa: E402
from agentic_systems_studio.lab import probes  # noqa: E402
from agentic_systems_studio import ConversationConfig, build_conversational_system  # noqa: E402
from examples.common_graph.application import CASE, build_system, check_result  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
# A user-confirmed rotation in the local env file must replace a stale inherited token.
fresh_token = dotenv_values(ROOT / ".env").get("AWS_BEARER_TOKEN_BEDROCK")
if fresh_token:
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = fresh_token
assert toolkit.__version__ == "2.1.4.dev5" and Path(toolkit.__file__).resolve().is_relative_to(SITE)
wheel_hash = hashlib.sha256(WHEEL.read_bytes()).hexdigest()
os.environ.update(AGENTIC_BUDGET_FILE=str(E / "campaign-budget.json"),
    AGENTIC_TEST_VERSION="2.1.4.dev5", AGENTIC_VALIDATION_SITE=str(SITE),
    AGENTIC_VALIDATION_EVIDENCE=str(E))
budget = ensure_budget()  # Never uninstalled while timed-out workers may still run.
routes = budget.routes
keys = {"openai-runtime": os.environ["OPENAI_API_KEY"],
        "bedrock-runtime": os.environ["AWS_BEARER_TOKEN_BEDROCK"],
        "ollama-cloud": os.environ["OLLAMA_API_KEY"], "ollama-gpu": "ollama-local"}
frameworks = ("native", "openai-agents", "strands")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--phase", choices=("notebooks", "advanced", "refund", "studio", "business", "applications", "interop", "bedrock", "pilot", "pending", "all"), default="all")
parser.add_argument("--routes", nargs="+", choices=tuple(routes), default=list(routes))
args = parser.parse_args()
out = E / "online" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "-" + args.phase)
out.mkdir(parents=True)
rows = []
blocked_routes = {}
plan = {"version": toolkit.__version__, "wheel_sha256": wheel_hash, "routes": routes,
        "frameworks": frameworks, "phase": args.phase, "limits": budget.limits,
        "selected_routes": args.routes,
        "scope": "12 provider-notebook routes; handoff; MCP/A2A; refund pause/resume; Studio controller; 15 rotating Tool projections and mandatory Bedrock null case"}
(out / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")


def serialize(value):
    if isinstance(value, toolkit.RunResult):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(k): serialize(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serialize(v) for v in value]
    return value


def select(route):
    config = routes[route]
    provider = "ollama-runtime" if route.startswith("ollama-") else route
    prefix = {"openai-runtime": "OPENAI", "bedrock-runtime": "BEDROCK", "ollama-runtime": "OLLAMA"}[provider]
    os.environ.update({prefix + "_MODEL": config["model"], prefix + "_MODEL_ID": config["model"],
                       prefix + "_BASE_URL": config["endpoint"]})
    if route.startswith("ollama-"):
        os.environ["OLLAMA_API_KEY"] = keys[route]
    if route == "ollama-gpu":
        os.environ.update(OLLAMA_GPU_MODEL=config["model"], OLLAMA_GPU_BASE_URL=config["endpoint"])
    if route == "bedrock-runtime":
        os.environ.update(AWS_REGION="us-east-2", AWS_DEFAULT_REGION="us-east-2")
    return provider


def runtime(route):
    return toolkit.runtime(provider=select(route), model=routes[route]["model"],
        endpoint=routes[route]["endpoint"], api_key=keys[route],
        region="us-east-2" if route == "bedrock-runtime" else None,
        timeout_s=90, max_tokens=1024, max_turns=3, max_tool_calls=1, max_retries=0)


def checkpoint():
    (out / "results.json").write_text(json.dumps({**plan, "rows": rows, "budget": budget.summary()},
                                                ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_case(name, route, framework, execute, payload=None):
    if budget.summary()["remaining_requests"] < 1:
        raise RuntimeError("Authorized request allocation exhausted; unattempted scenarios remain pending")
    select(route)
    budget.phase = "dev5/" + name + "/" + route + "/" + framework
    before = budget.summary()
    row = {"name": name, "route": route, "framework": framework, "model": routes[route]["model"],
           "wheel_sha256": wheel_hash, "input": payload, "budget_before": before, "passed": False}
    (out / (str(len(rows) + 1).zfill(3) + "-plan.json")).write_text(json.dumps(row, indent=2), encoding="utf-8")
    started = time.monotonic()
    try:
        if route in blocked_routes:
            row["not_attempted"] = True
            raise RuntimeError(blocked_routes[route])
        if route == "bedrock-runtime" and not inspect_key(keys[route])["local_format_valid"]:
            row["not_attempted"] = True
            raise ValueError("Bedrock API key prefix is invalid locally; no transmission attempted")
        row["result"] = serialize(execute())
        if route == "ollama-gpu":
            with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=10) as response:
                inventory = json.loads(response.read())["models"]
            row["gpu"] = [{k: m.get(k) for k in ("name", "digest", "size_vram", "size")} for m in inventory]
            assert any(m["name"] == routes[route]["model"] and m.get("size_vram", 0) > 0 for m in inventory)
        row["passed"] = True
    except Exception as exc:
        message = str(exc)[-3500:]
        for secret in keys.values():
            message = message.replace(secret, "[REDACTED]")
        row["error"] = {"type": type(exc).__name__, "message": message}
        if route == "bedrock-runtime" and any(term in message for term in (
            "AccessDeniedException", "Bearer Token has expired", "Invalid API Key format", "prefix is invalid locally"
        )):
            blocked_routes[route] = "Bedrock authentication failed; remaining scenarios not attempted with this credential"
        if exc.args and isinstance(exc.args[0], dict):
            row["failed_result"] = serialize(exc.args[0])
    row.update(elapsed_s=round(time.monotonic() - started, 3), budget_after=budget.summary())
    row["requests"] = row["budget_after"]["attempts"] - before["attempts"]
    rows.append(row)
    checkpoint()
    print(json.dumps({k: row[k] for k in ("name", "route", "framework", "passed", "requests")}), flush=True)


def notebook(filename, framework):
    log = out / (filename + "-" + framework + ".log")
    with log.open("w", encoding="utf-8") as stream:
        finished = subprocess.run([sys.executable, str(ROOT / "scripts/validate_learning_notebooks_214.py"),
            "--profile", "live", "--path", filename, "--framework", framework], cwd=ROOT,
            env=os.environ.copy(), stdout=stream, stderr=subprocess.STDOUT, timeout=420)
    assert finished.returncode == 0, log.read_text(encoding="utf-8")[-3500:]
    return {"notebook": filename, "log": log.relative_to(E).as_posix()}


def refund(route, framework):
    program = build_system(framework, reasoner=runtime(route), interactive=True).compile()
    waiting = program.run(CASE, limits=toolkit.Limits(max_actions=100, timeout_s=150))
    assert waiting.status == "paused", waiting.to_dict()
    calls = budget.summary()["attempts"]
    result = program.resume(waiting, True)
    assert calls == budget.summary()["attempts"]
    assert check_result(result) and result.data["status"] == "approved", result.to_dict()
    return {"paused": waiting, "completed": result, "human_results": result.human_results(),
            "agent_lineage": result.lineage().to_prompt_context()}


def studio(route, framework):
    app = build_conversational_system(ConversationConfig(provider=select(route), framework=framework,
        model=routes[route]["model"], max_response_repairs=0, max_tokens=512, max_turns=3))
    result = app.run("Calcula 7 * 6.", history=({"role": "user", "content": "Me llamo Ana."},))
    assert result.ok and result.data["history_turns"] == 1, result.to_dict()
    assert any(e.name == "safe_calculate" and e.ok for n in result.walk() for e in n.tool_events)
    assert "42" in result.text, result.to_dict()
    return {"result": result, "scope": "Full Studio controller, history and calculator; not all browser UI controls"}


def business(module, expected, route, framework):
    operation = module.capability.tools[0]
    actor = toolkit.Agent(operation.name, runtime=runtime(route), framework=toolkit.framework(framework),
        skills=(module.capability,), instructions="Call " + operation.name + " exactly once with input unchanged; do not omit null fields. Only the Tool computes output.",
        contract={"tool_expectation": {"all_of": [operation.name]}, "completion": "when_required_tools_satisfied"}, policy={"repair": False})
    def execute(state):
        raw = actor.run(state.input)
        assert raw.ok, raw.to_dict()
        events = [e for n in raw.walk() for e in n.tool_events if e.name == operation.name and e.ok]
        assert len(events) == 1 and events[0].input == module.sample, raw.to_dict()
        value = events[0].output
        if value != expected:
            assert isinstance(value, dict) and value.get("data") == expected and value.get("ok", True) is True, value
            value = value["data"]
        assert value == expected
        return replace(raw, data=value)
    graph = toolkit.StateGraph(module.WorkState, output_schema=module.Output)
    graph.add_node("business", execute)
    graph.add_edge(toolkit.START, "business")
    graph.add_edge("business", toolkit.END)
    result = toolkit.System("observed_" + operation.name, graph=graph).run({"input": module.sample},
        limits=toolkit.Limits(max_actions=50, timeout_s=150))
    assert result.ok and result.data == expected and result.check_invariants().ok, result.to_dict()
    return {"result": result, "oracle": expected,
            "scope": "Tool-to-runtime projection; the complete original deterministic graph is validated offline"}


def interop(route):
    from examples.framework_interop.example import build
    application = build({name: runtime(route) for name in frameworks})
    result = application.run({"value": 42, "trail": []}, limits=toolkit.Limits(timeout_s=180))
    assert result.ok and result.data == {"value": 45, "trail": list(frameworks), "validated": True}, result.to_dict()
    return {"result": result, "human_results": result.human_results(),
            "scope": "native + OpenAI Agents + Strands in one System on the frozen provider"}


def pending_case(name, framework, execute, payload=None):
    # All pending Bedrock scenarios have at most three actor turns. Do not
    # start a new case with insufficient room to complete its observed protocol.
    if budget.summary()["remaining_requests"] < 3:
        rows.append({"name": name, "route": "bedrock-runtime", "framework": framework,
            "model": routes["bedrock-runtime"]["model"], "wheel_sha256": wheel_hash,
            "input": payload, "passed": False, "not_attempted": True,
            "status": "pending-budget", "requests": 0,
            "error": {"type": "PendingBudget", "message": "Fewer than three authorized requests remain; case was not started"}})
        checkpoint()
        return
    run_case(name, "bedrock-runtime", framework, execute, payload)


if args.phase == "pilot":
    run_case("provider-notebook", "bedrock-runtime", "native", lambda: notebook("03_bedrock", "native"), {"value": 37})

if args.phase == "pending":
    # The native provider notebook is the successful pilot; do not repeat it.
    previous = [read for path in sorted((E / "online").glob("*-pilot/results.json"))
                for read in json.loads(path.read_text(encoding="utf-8"))["rows"]]
    assert previous and previous[-1]["passed"] and previous[-1]["wheel_sha256"] == wheel_hash
    module = importlib.import_module("examples.applications.data_quality.example")
    expected = module.run().data
    write_case = {"input": module.sample, "expected": expected,
                  "source_sha256": hashlib.sha256((ROOT / "examples/applications/data_quality/example.py").read_bytes()).hexdigest()}
    (out / "frozen-mandatory-null.json").write_text(json.dumps(write_case, ensure_ascii=False, indent=2), encoding="utf-8")
    for framework in frameworks:
        pending_case("mandatory-null", framework,
            lambda f=framework: business(module, expected, "bedrock-runtime", f), module.sample)
    for framework in ("openai-agents", "strands"):
        pending_case("provider-notebook", framework, lambda f=framework: notebook("03_bedrock", f), {"value": 37})
    for framework in frameworks:
        pending_case("refund-pause-resume", framework, lambda f=framework: refund("bedrock-runtime", f), CASE)
    for kind in ("mcp", "a2a"):
        pending_case("strands-" + kind, "strands", lambda k=kind: probes.protocols("bedrock-runtime", k, budget))
    for framework in frameworks:
        pending_case("studio-controller", framework, lambda f=framework: studio("bedrock-runtime", f),
                     {"message": "Calcula 7 * 6.", "history_turns": 1})

if args.phase in {"notebooks", "bedrock", "all"}:
    for route, filename in (("openai-runtime", "01_openai"), ("bedrock-runtime", "03_bedrock"),
                            ("ollama-gpu", "05_ollama_gpu"), ("ollama-cloud", "02_ollama")):
        if route not in args.routes:
            continue
        for framework in frameworks:
            run_case("provider-notebook", route, framework, lambda f=filename, a=framework: notebook(f, a), {"value": 37})
    if "openai-runtime" in args.routes:
        run_case("handoff-notebook", "openai-runtime", "openai-agents", lambda: notebook("02_openai_agents", "openai-agents"))

if args.phase in {"advanced", "bedrock", "all"}:
    for route in args.routes:
        provider = select(route)
        for kind in ("mcp", "a2a"):
            run_case("strands-" + kind, route, "strands", lambda p=provider, k=kind: probes.protocols(p, k, budget))

if args.phase in {"interop", "all"}:
    for route in args.routes:
        run_case("three-framework-interop", route, "native+openai-agents+strands", lambda r=route: interop(r), {"value": 42, "trail": []})

if args.phase in {"refund", "studio", "applications", "bedrock", "all"}:
    for route in args.routes:
        for framework in frameworks:
            if args.phase in {"refund", "applications", "bedrock", "all"}:
                run_case("refund-pause-resume", route, framework, lambda r=route, f=framework: refund(r, f), CASE)
            if args.phase in {"studio", "applications", "bedrock", "all"}:
                run_case("studio-controller", route, framework, lambda r=route, f=framework: studio(r, f), {"message": "Calcula 7 * 6.", "history_turns": 1})

if args.phase in {"business", "applications", "bedrock", "all"}:
    cases = []
    for path in sorted([*(ROOT / "examples/applications").glob("*/example.py"), *(ROOT / "examples/patterns").glob("*/example.py")]):
        source = path.read_text(encoding="utf-8")
        if "class Payload(Closed)" not in source:
            continue
        module = importlib.import_module(".".join(path.relative_to(ROOT).with_suffix("").parts))
        cases.append((path, module, module.run().data))
    (out / "frozen-business-cases.json").write_text(json.dumps([
        {"path": p.relative_to(ROOT).as_posix(), "source_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
         "input": m.sample, "expected": expected} for p, m, expected in cases], ensure_ascii=False, indent=2), encoding="utf-8")
    for i, (path, module, expected) in enumerate(cases if args.phase != "bedrock" else []):
        route = args.routes[i % len(args.routes)]
        framework = frameworks[(i // len(args.routes) + i) % len(frameworks)]
        run_case("business:" + path.parent.name, route, framework,
                 lambda m=module, e=expected, r=route, f=framework: business(m, e, r, f), module.sample)
    for path, module, expected in cases:
        if path.parent.name == "data_quality" and "bedrock-runtime" in args.routes:
            for framework in frameworks:
                run_case("mandatory-null", "bedrock-runtime", framework,
                         lambda m=module, e=expected, f=framework: business(m, e, "bedrock-runtime", f), module.sample)

checkpoint()
raise SystemExit(0 if all(row["passed"] for row in rows) else 1)
