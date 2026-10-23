"""Run the explicit 2.1.3 campaign. No model or provider substitutions."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
for key in ("OPENAI_AGENTS_DISABLE_TRACING", "OTEL_SDK_DISABLED", "AWS_EC2_METADATA_DISABLED"):
    os.environ[key] = "1" if key == "OPENAI_AGENTS_DISABLE_TRACING" else "true"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

import agentic_systems as toolkit  # noqa: E402
from agentic_systems_studio.environment import load_studio_environment  # noqa: E402
from agentic_systems_studio.routes import values, configured  # noqa: E402
from agentic_systems_studio.budget import ensure_budget  # noqa: E402

OUTPUT = ROOT / os.environ.get("AGENTIC_213_EVIDENCE_DIR", "revisions/2.1.3/framework-evidence")
PROVIDERS = ("python-runtime", "ollama-runtime", "bedrock-runtime", "openai-runtime")
FRAMEWORKS = ("native", "langgraph", "openai-agents", "strands")


def initialize():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    load_studio_environment(ROOT / ".env")
    routes = {}
    for provider in PROVIDERS[1:]:
        options = values(provider)
        assert configured(provider), provider + " is not configured"
        endpoint = options["endpoint"] or ("https://api.openai.com/v1" if provider == "openai-runtime" else
                   "https://bedrock-runtime." + options["region"] + ".amazonaws.com")
        routes[provider] = {"model": options["model"], "endpoint": endpoint,
                            "input_usd_per_million": 5, "output_usd_per_million": 20}
    path = Path(os.environ.get("AGENTIC_213_BUDGET_FILE", str(ROOT / ".tmp/campaign213/live-budget.json"))).resolve()
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        raise RuntimeError("Create the explicitly authorized allocation first; a runner never resets a budget")
    ledger = json.loads(path.read_text(encoding="utf-8"))
    assert ledger["routes"] == routes and ledger["limits"] == {"usd": 10, "requests": 300}
    os.environ["AGENTIC_213_BUDGET_FILE"] = str(path)
    (OUTPUT / "routes.json").write_text(json.dumps(routes, indent=2) + "\n", encoding="utf-8")
    return ensure_budget()


from agentic_systems_studio.lab.probes import matrix, handoffs, protocols, interop  # noqa: E402


def studio(provider, framework):
    from agentic_systems_studio import ConversationConfig, build_conversational_system
    application = build_conversational_system(ConversationConfig(provider=provider, framework=framework, max_tokens=384, max_response_repairs=0))
    history, results = [], []
    for message in ("Mi proyecto se llama LINTERNA. Confirma en una frase breve.",
                    "¿Cómo se llama mi proyecto? Responde en una frase breve.",
                    "Calcula 17 * 19 usando la calculadora y responde en una frase."):
        result = application.run(message, history=history)
        results.append(result.to_dict())
        assert result.ok and result.text.strip(), result.to_dict()
        history += [{"role": "user", "content": message}, {"role": "assistant", "content": result.text}]
    if provider != "python-runtime":
        assert "LINTERNA" in results[1]["text"].upper()
        assert "323" in results[2]["text"]
        assert any(event.name == "safe_calculate" and event.ok for node in result.walk() for event in node.tool_events)
    return {"provider": provider, "framework": framework, "turns": results,
            "semantic_scope": "deterministic mock" if provider == "python-runtime" else "memory and exact arithmetic oracle"}


def studio_ui(provider, framework):
    """Exercise the same packaged Streamlit widgets a user interacts with."""
    from streamlit.testing.v1 import AppTest
    from agentic_systems_studio.server import resolve_studio_app
    app = AppTest.from_file(str(resolve_studio_app()), default_timeout=180).run()
    assert not app.exception
    app.selectbox(key="provider").set_value(provider).run()
    app.selectbox(key="framework").set_value(framework).run()
    app.chat_input[0].set_value("Calcula 17 * 19 usando la calculadora y responde en una frase.").run()
    assert not app.exception, [str(item) for item in app.exception]
    result = app.session_state["last_result"]
    assert result.ok and "323" in result.text, result.to_dict()
    assert result.meta["framework"] == framework
    assert any(event.name == "safe_calculate" and event.ok for node in result.walk() for event in node.tool_events)
    return {"provider": provider, "framework": framework, "ui": "Streamlit AppTest; actual widgets",
            "result": result.to_dict()}


def integrated(provider, framework):
    from examples.api_walkthrough.example import build_day, check_day
    from agentic_systems_studio.routes import make_runtime
    day = build_day(runtime=make_runtime(provider, max_tokens=256), framework=toolkit.framework(framework))
    result = day.run(limits=toolkit.Limits(timeout_s=240))
    assert result.ok and check_day(result, {})['ok'], result.to_dict()
    assert result.check_invariants().ok
    # Evaluate the observed episode without buying a second execution.
    frozen = toolkit.RunResult(**result.to_dict())
    observed = toolkit.Agent('observed_episode', toolkit.Action('read', lambda data: frozen))
    evaluation = toolkit.Eval('observed_orders', observed,
        cases=({'input': {}, 'expected': {'ok': True}},), checks=(check_day,)).run()
    assert evaluation.ok, evaluation.to_dict()
    return {'provider': provider, 'framework': framework, 'result': result.to_dict(), 'eval': evaluation.to_dict(),
            'scope': 'Deterministic quote; selected runtime actor for approve/review; original Tool evidence, routing, episode memory and exact evaluation'}


def main(phase, wheel, only=None):
    assert toolkit.__version__ == "2.1.3" and "site-packages" in Path(toolkit.__file__).parts
    wheel = Path(wheel)
    with zipfile.ZipFile(wheel) as archive:
        installed = Path(toolkit.__file__).parent
        assert all((installed / name.removeprefix("agentic_systems/")).read_bytes() == archive.read(name)
                   for name in archive.namelist() if name.startswith("agentic_systems/") and not name.endswith("/"))
    budget = initialize()
    budget.phase = phase
    cases = []
    if phase == "matrix":
        cases = [(p + "--" + f, lambda p=p, f=f: matrix(p, f)) for p in PROVIDERS for f in FRAMEWORKS]
    elif phase == "features":
        cases = [(p + "--handoffs", lambda p=p: handoffs(p)) for p in PROVIDERS]
        cases += [(p + "--" + kind, lambda p=p, k=kind: protocols(p, k, budget)) for p in PROVIDERS for kind in ("mcp", "a2a")]
        cases += [("interop-python", lambda: interop(False)), ("interop-mixed", lambda: interop(True))]
        from agentic_systems_studio.lab.checkpoint import run as checkpoint
        cases += [("langgraph-checkpoint", checkpoint)]
    elif phase == "studio":
        cases = [(p + "--" + f, lambda p=p, f=f: studio(p, f)) for p in PROVIDERS for f in FRAMEWORKS]
    elif phase == "integrated":
        cases = [(p + "--" + f, lambda p=p, f=f: integrated(p, f)) for p in PROVIDERS for f in FRAMEWORKS]
    else:
        cases = [(p + "--" + f, lambda p=p, f=f: studio_ui(p, f)) for p in PROVIDERS[1:] for f in FRAMEWORKS]
    if only:
        selected_names = set(only.split(","))
        cases = [(name, execute) for name, execute in cases if name in selected_names]
        assert len(cases) == len(selected_names), "Unknown selected case"
    attempt = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    destination = OUTPUT / phase / attempt
    destination.mkdir(parents=True)
    rows = []
    for name, execute in cases:
        started = time.monotonic()
        try:
            report = execute()
            row = {"name": name, "passed": True, "report": report}
        except Exception as exc:
            row = {"name": name, "passed": False, "error": type(exc).__name__, "message": str(exc)}
        row["elapsed_s"] = round(time.monotonic() - started, 3)
        rows.append(row)
        (destination / (name + ".json")).write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"case": name, "passed": row["passed"], "budget": budget.summary()}), flush=True)
        if budget.summary().get("remaining_requests", 1) <= 0 or float(budget.summary().get("remaining_usd", 1)) < 0.04:
            break
    summary = {"phase": phase, "version": toolkit.__version__, "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
               "created_at": datetime.now(timezone.utc).isoformat(), "planned": len(cases), "executed": len(rows),
               "passed": sum(row["passed"] for row in rows), "all_passed": len(rows) == len(cases) and all(r["passed"] for r in rows),
               "budget": budget.summary(), "rows": [{k: v for k, v in row.items() if k != "report"} for row in rows]}
    summary["attempt_directory"] = destination.relative_to(ROOT).as_posix()
    (destination / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / (phase + ".json")).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("matrix", "features", "studio", "studio-ui", "integrated"))
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--only", help="Comma-separated exact case identities; previous attempts remain preserved")
    args = parser.parse_args()
    main(args.phase, args.wheel, args.only)
