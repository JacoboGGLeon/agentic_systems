"""Authorized dev3 learning campaign; persistent USD/request cap, all attempts kept."""

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

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "revisions/2.1.4/learning-dev3"
SITE = ROOT / ".tmp/candidate214-dev3/site-packages"
sys.path[:0] = [str(SITE), str(ROOT), str(ROOT / "examples/agentic_systems_studio/src")]
from dotenv import load_dotenv  # noqa: E402
import agentic_systems as toolkit  # noqa: E402
from langgraph.graph import StateGraph, START, END  # noqa: E402
from agentic_systems_studio.budget import ensure_budget  # noqa: E402
from agentic_systems_studio.lab import probes  # noqa: E402
from agentic_systems_studio import ConversationConfig, build_conversational_system  # noqa: E402
from examples.common_graph.application import CASE, build_system, check_result  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
os.environ["AGENTIC_BUDGET_FILE"] = str(E / "campaign-budget.json")
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
os.environ["OTEL_SDK_DISABLED"] = "true"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--group",
    choices=("notebooks", "examples", "advanced", "interop", "bedrock-repeat", "all"),
    default="all",
)
args = parser.parse_args()
assert toolkit.__version__ == "2.1.4.dev3" and Path(
    toolkit.__file__
).resolve().is_relative_to(SITE)
WHEEL = (
    ROOT
    / "revisions/2.1.4/json-markdown-fix/candidate/agentic_systems-2.1.4.dev3-py3-none-any.whl"
)
plan = json.loads((E / "live-plan.json").read_text(encoding="utf-8"))
assert hashlib.sha256(WHEEL.read_bytes()).hexdigest() == plan["wheel_sha256"]
budget = ensure_budget()  # Hooks remain installed through worker shutdown/process exit.
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
out = E / "live-runs" / (stamp + "-" + args.group)
out.mkdir(parents=True)
rows = []


def serialize(value):
    if isinstance(value, toolkit.RunResult):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(k): serialize(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serialize(v) for v in value]
    return value


def select(route):
    config = plan["routes"][route]
    if route == "ollama-gpu":
        os.environ.update(
            OLLAMA_BASE_URL=config["endpoint"],
            OLLAMA_MODEL=config["model"],
            OLLAMA_API_KEY="ollama-local",
        )
    return "ollama-runtime" if route == "ollama-gpu" else route


def runtime(route):
    provider = select(route)
    config = plan["routes"][route]
    key = (
        os.environ["OPENAI_API_KEY"]
        if route == "openai-runtime"
        else os.environ["AWS_BEARER_TOKEN_BEDROCK"]
        if route == "bedrock-runtime"
        else "ollama-local"
    )
    return toolkit.runtime(
        provider=provider,
        model=config["model"],
        endpoint=config["endpoint"],
        api_key=key,
        region="us-east-2" if route == "bedrock-runtime" else None,
        max_tokens=1024,
        max_turns=3,
        max_tool_calls=1,
        max_retries=0,
        timeout_s=90,
    )


def checkpoint():
    (out / "results.json").write_text(
        json.dumps(
            {
                "wheel_sha256": plan["wheel_sha256"],
                "rows": rows,
                "budget": budget.summary(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def run_case(name, route, framework, function, frozen_input=None):
    if budget.summary()["remaining_requests"] < 1:
        raise RuntimeError(
            "Request allocation exhausted; unattempted cells remain pending"
        )
    budget.phase = name + "/" + route + "/" + framework
    before = budget.summary()
    descriptor = {
        "name": name,
        "route": route,
        "framework": framework,
        "model": plan["routes"][route]["model"],
        "input": frozen_input,
        "budget_before": before,
        "wheel_sha256": plan["wheel_sha256"],
    }
    number = len(rows) + 1
    (out / (str(number).zfill(3) + "-plan.json")).write_text(
        json.dumps(descriptor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    started = time.monotonic()
    row = {**descriptor, "passed": False}
    try:
        value = function()
        row.update(passed=True, result=serialize(value))
        if route == "ollama-gpu":
            with urllib.request.urlopen(
                "http://127.0.0.1:11434/api/ps", timeout=10
            ) as response:
                inventory = json.loads(response.read())["models"]
            row["gpu"] = [
                {k: m.get(k) for k in ("name", "digest", "size_vram", "size")}
                for m in inventory
            ]
            assert any(
                m["name"] == descriptor["model"] and m.get("size_vram", 0) > 0
                for m in inventory
            )
    except Exception as exc:
        message = str(exc)[-2500:]
        for key in ("OPENAI_API_KEY", "AWS_BEARER_TOKEN_BEDROCK", "OLLAMA_API_KEY"):
            secret = os.getenv(key)
            if secret:
                message = message.replace(secret, "[REDACTED]")
        row.update(passed=False, error={"type": type(exc).__name__, "message": message})
        if exc.args and isinstance(exc.args[0], dict):
            row["failed_result"] = serialize(exc.args[0])
    row.update(
        elapsed_s=round(time.monotonic() - started, 3), budget_after=budget.summary()
    )
    row["requests"] = row["budget_after"]["attempts"] - before["attempts"]
    rows.append(row)
    checkpoint()
    print(
        json.dumps(
            {k: row[k] for k in ("name", "route", "framework", "passed", "requests")}
        ),
        flush=True,
    )


def refund(route, framework):
    program = build_system(
        framework, reasoner=runtime(route), interactive=True
    ).compile()
    waiting = program.run(CASE, limits=toolkit.Limits(max_actions=100, timeout_s=150))
    assert waiting.status == "paused", waiting.to_dict()
    count = budget.summary()["attempts"]
    result = program.resume(waiting, True)
    assert count == budget.summary()["attempts"]
    assert check_result(result) and result.data["status"] == "approved", (
        result.to_dict()
    )
    return {
        "paused": waiting,
        "completed": result,
        "human_lineage": result.lineage().render(),
        "agent_lineage": result.lineage().to_prompt_context(),
    }


def business(module, expected, route, framework):
    operation = module.capability.tools[0]
    actor = toolkit.Agent(
        operation.name,
        runtime=runtime(route),
        framework=toolkit.framework(framework),
        skills=(module.capability,),
        instructions="Call "
        + operation.name
        + " exactly once with the supplied input unchanged. Only the Tool determines business output.",
        contract={
            "tool_expectation": {"all_of": [operation.name]},
            "completion": "when_required_tools_satisfied",
        },
        policy={"repair": False},
    )

    def execute(state):
        raw = actor.run(state["input"])
        assert raw.ok, raw.to_dict()
        events = [
            event
            for node in raw.walk()
            for event in node.tool_events
            if event.name == operation.name and event.ok
        ]
        assert len(events) == 1 and events[0].input == module.sample
        value = events[0].output
        if value != expected:
            assert (
                isinstance(value, dict)
                and value.get("data") == expected
                and value.get("ok", True) is True
            ), value
            value = value["data"]
        assert value == expected
        return replace(raw, data=value)

    graph = StateGraph(module.WorkState, output_schema=module.Output)
    graph.add_node("business", execute)
    graph.add_edge(START, "business")
    graph.add_edge("business", END)
    result = toolkit.System("observed_" + operation.name, graph=graph).run(
        {"input": module.sample}, limits=toolkit.Limits(max_actions=50, timeout_s=150)
    )
    assert result.ok and result.data == expected and result.check_invariants().ok, (
        result.to_dict()
    )
    return {
        "result": result,
        "oracle": expected,
        "scope": "Explicit Tool-to-runtime actor projection; original deterministic graph validated offline",
        "human_lineage": result.lineage().render(),
        "agent_lineage": result.lineage().to_prompt_context(),
    }


def studio(route, framework):
    provider = select(route)
    app = build_conversational_system(
        ConversationConfig(
            provider=provider,
            framework=framework,
            model=plan["routes"][route]["model"],
            max_response_repairs=0,
            max_tokens=512,
            max_turns=3,
        )
    )
    first = app.run("Responde en una sola frase que estas listo.")
    assert first.ok, first.to_dict()
    second = app.run(
        "Calcula 7 * 6.", history=({"role": "user", "content": "Me llamo Ana."},)
    )
    assert second.ok and second.data["history_turns"] == 1, second.to_dict()
    events = [
        e
        for n in second.walk()
        for e in n.tool_events
        if e.name == "safe_calculate" and e.ok
    ]
    assert events and "42" in second.text, second.to_dict()
    return {
        "greeting": first,
        "calculation": second,
        "scope": "Conversation/controller, history and calculator; UI tested separately",
    }


if args.group in {"notebooks", "all"}:
    for route, filename in (
        ("openai-runtime", "01_openai"),
        ("bedrock-runtime", "03_bedrock"),
        ("ollama-gpu", "05_ollama_gpu"),
    ):
        select(route)
        for framework in plan["frameworks"]:

            def notebook(filename=filename, framework=framework):
                log = out / (filename + "-" + framework + ".log")
                with log.open("w", encoding="utf-8") as stream:
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts/validate_learning_notebooks_214.py"),
                            "--profile",
                            "live",
                            "--path",
                            filename,
                            "--framework",
                            framework,
                        ],
                        cwd=ROOT,
                        env=os.environ.copy(),
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                        timeout=360,
                    )
                assert completed.returncode == 0, log.read_text(encoding="utf-8")[
                    -3500:
                ]
                return {"log": str(log.relative_to(E)), "notebook": filename}

            run_case("provider-notebook", route, framework, notebook, {"value": 37})

if args.group in {"examples", "all"}:
    # The business Tools and Python oracle are read/frozen before any call in this group.
    cases = []
    for path in sorted(
        [
            *(ROOT / "examples/applications").glob("*/example.py"),
            *(ROOT / "examples/patterns").glob("*/example.py"),
        ]
    ):
        module = importlib.import_module(
            ".".join(path.relative_to(ROOT).with_suffix("").parts)
        )
        if (
            hasattr(module, "WorkState")
            and hasattr(module, "capability")
            and hasattr(module, "sample")
        ):
            expected = module.run().data
            cases.append((path, module, expected))
    (out / "frozen-business-cases.json").write_text(
        json.dumps(
            [
                {
                    "path": p.relative_to(ROOT).as_posix(),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "input": m.sample,
                    "expected": expected,
                }
                for p, m, expected in cases
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    assert len(cases) == 15
    for case_index, (path, module, expected) in enumerate(cases):
        for route_index, route in enumerate(plan["routes"]):
            for framework in (plan["frameworks"][(case_index + route_index) % 3],):
                run_case(
                    "business/" + path.parent.name,
                    route,
                    framework,
                    lambda m=module, expected=expected, r=route, f=framework: business(
                        m, expected, r, f
                    ),
                    module.sample,
                )

if args.group in {"advanced", "all"}:
    for route in plan["routes"]:
        for framework in plan["frameworks"]:
            run_case(
                "refund-graph",
                route,
                framework,
                lambda r=route, f=framework: refund(r, f),
                CASE,
            )
            run_case(
                "studio-conversation",
                route,
                framework,
                lambda r=route, f=framework: studio(r, f),
            )
        provider = select(route)
        run_case(
            "handoff-and-guardrail",
            route,
            "openai-agents",
            lambda p=provider: probes.handoffs(p),
        )
        for kind in ("mcp", "a2a"):
            run_case(
                "strands-" + kind,
                route,
                "strands",
                lambda p=provider, k=kind: probes.protocols(p, k, budget),
            )
        from agentic_systems_studio.lab.interop import build, FRAMEWORKS

        def interop(route=route):
            app = build({name: runtime(route) for name in FRAMEWORKS})
            result = app.run(
                {"value": 42, "trail": []},
                limits=toolkit.Limits(max_actions=100, timeout_s=240),
            )
            assert result.ok and result.data == {
                "value": 45,
                "trail": list(FRAMEWORKS),
                "validated": True,
            }, result.to_dict()
            return result

        run_case(
            "three-framework-interop", route, "native+openai-agents+strands", interop
        )
checkpoint()
print(json.dumps(budget.summary()), flush=True)

if args.group == "interop":
    from agentic_systems_studio.lab.interop import build, FRAMEWORKS

    for route in plan["routes"]:

        def run_interop(route=route):
            app = build({name: runtime(route) for name in FRAMEWORKS})
            result = app.run(
                {"value": 42, "trail": []},
                limits=toolkit.Limits(max_actions=100, timeout_s=240),
            )
            assert result.ok and result.data == {
                "value": 45,
                "trail": list(FRAMEWORKS),
                "validated": True,
            }, result.to_dict()
            return result

        run_case(
            "three-framework-interop",
            route,
            "native+openai-agents+strands",
            run_interop,
        )
    checkpoint()
    print(json.dumps(budget.summary()), flush=True)

if args.group == "bedrock-repeat":
    from examples.applications.data_quality import example as data_quality

    expected = data_quality.run().data
    run_case(
        "business/data_quality",
        "bedrock-runtime",
        "native",
        lambda: business(data_quality, expected, "bedrock-runtime", "native"),
        data_quality.sample,
    )
    checkpoint()
    print(json.dumps(budget.summary()), flush=True)
