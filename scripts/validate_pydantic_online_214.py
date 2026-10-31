"""Four single-response probes on the final dev4 wheel within the existing cap."""

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / ".tmp/candidate214-dev4-final/site-packages"
sys.path[:0] = [str(SITE), str(ROOT / "examples/agentic_systems_studio/src")]
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
os.environ["OTEL_SDK_DISABLED"] = "true"
from dotenv import load_dotenv  # noqa: E402
import pydantic  # noqa: E402
import agentic_systems as toolkit  # noqa: E402
from agentic_systems_studio.budget import ensure_budget  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
E = ROOT / "revisions/2.1.4/pydantic-dev4"
os.environ["AGENTIC_BUDGET_FILE"] = str(ROOT / "revisions/2.1.4/learning-dev3/campaign-budget.json")
budget = ensure_budget()
assert toolkit.__version__ == "2.1.4.dev4" and Path(toolkit.__file__).resolve().is_relative_to(SITE)
wheel = E / "builds/03/agentic_systems-2.1.4.dev4-py3-none-any.whl"
wheel_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
routes = json.loads(budget.path.read_text())["routes"]
plan = [("openai-runtime", "openai-agents"), ("bedrock-runtime", "native"), ("ollama-gpu", "native"), ("ollama-cloud", "strands")]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--route", choices=[route for route, _ in plan])
args = parser.parse_args()
if args.route:
    plan = [item for item in plan if item[0] == args.route]
assert budget.summary()["remaining_requests"] >= len(plan)
destination = E / "online" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
destination.mkdir(parents=True)


class State(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True, extra="forbid")
    value: int
    answer: int | None = None


class Output(pydantic.BaseModel):
    answer: int


rows = []
for route, actor in plan:
    config = routes[route]
    descriptor = {"route": route, "framework": actor, "model": config["model"], "input": {"value": 2}, "expected": {"answer": 3}, "wheel_sha256": wheel_hash, "budget_before": budget.summary()}
    (destination / (route + "-plan.json")).write_text(json.dumps(descriptor, indent=2) + "\n")
    row = {**descriptor, "passed": False}
    key = os.environ["OPENAI_API_KEY"] if route == "openai-runtime" else os.environ["AWS_BEARER_TOKEN_BEDROCK"] if route == "bedrock-runtime" else os.environ["OLLAMA_API_KEY"] if route == "ollama-cloud" else "ollama-local"
    provider = "ollama-runtime" if route.startswith("ollama-") else route
    if provider == "ollama-runtime":
        # The existing native Ollama client reads its connection profile from env.
        # Match the frozen explicit route; never edit the user's dotenv file.
        os.environ.update(OLLAMA_BASE_URL=config["endpoint"], OLLAMA_MODEL=config["model"], OLLAMA_API_KEY=key)
    budget.phase = "pydantic-dev4/" + route + "/" + actor
    try:
        reasoner = toolkit.Agent("reasoner", runtime=toolkit.runtime(
            provider=provider, model=config["model"], endpoint=config["endpoint"],
            api_key=key, region="us-east-2" if route == "bedrock-runtime" else None,
            max_tokens=256, max_turns=1, max_tool_calls=1, max_retries=0, timeout_s=60,
        ), framework=toolkit.framework(actor),
            instructions='Return only JSON {"answer":3} when the supplied value is 2. No markdown or commentary.',
            contract={"output_schema": Output.model_json_schema()}, policy={"repair": False})
        graph = toolkit.StateGraph(State, output_schema=Output)
        graph.add_node("reasoner", reasoner)
        graph.add_edge(toolkit.START, "reasoner")
        graph.add_edge("reasoner", toolkit.END)
        result = toolkit.System("typed-reasoning", graph=graph).run(State(value=2), limits=toolkit.Limits(max_actions=20, timeout_s=90))
        row.update(result=result.to_dict(), human_results=result.human_results(), agent_lineage=result.lineage().to_prompt_context())
        assert result.ok and result.data == {"answer": 3} and result.check_invariants().ok
        assert row["human_results"] and "Output:" in row["human_results"]
        row["passed"] = True
    except Exception as exc:
        row["error"] = {"type": type(exc).__name__, "message": str(exc)[:1200].replace(key, "[REDACTED]")}
    row["budget_after"] = budget.summary()
    rows.append(row)
    (destination / "results.json").write_text(json.dumps({"version": toolkit.__version__, "wheel_sha256": wheel_hash, "rows": rows, "budget": budget.summary(), "scope": "Four one-response integration probes, not a complete runtime-by-framework campaign"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: row[k] for k in ("route", "framework", "passed", "budget_after")}), flush=True)
raise SystemExit(0 if all(row["passed"] for row in rows) else 1)
