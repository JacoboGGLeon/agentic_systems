"""Bounded pending-route checks against the unchanged dev3 wheel; never publishes."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / ".tmp/candidate214-dev3/site-packages"
sys.path[:0] = [str(SITE), str(ROOT), str(ROOT / "examples/agentic_systems_studio/src")]
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
os.environ["OTEL_SDK_DISABLED"] = "true"
from dotenv import load_dotenv  # noqa: E402
import agentic_systems as toolkit  # noqa: E402
from agentic_systems_studio.budget import ensure_budget  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--group", choices=("cloud", "bedrock-diagnostic"), required=True)
parser.add_argument("--framework", choices=("native", "openai-agents", "strands"))
args = parser.parse_args()
E = ROOT / "revisions/2.1.4/release-followup"
E.mkdir(exist_ok=True)
ledger_path = ROOT / "revisions/2.1.4/learning-dev3/campaign-budget.json"
os.environ["AGENTIC_BUDGET_FILE"] = str(ledger_path)
assert toolkit.__version__ == "2.1.4.dev3" and Path(toolkit.__file__).is_relative_to(
    SITE
)
wheel = (
    ROOT
    / "revisions/2.1.4/json-markdown-fix/candidate/agentic_systems-2.1.4.dev3-py3-none-any.whl"
)
wheel_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
assert wheel_hash == "83cf3dca623e57d335b02136e70e9fe13dc5dd0ffbc0cc633b8cdcbda430aab9"
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
destination = E / (stamp + "-" + args.group)
destination.mkdir()
ledger = json.loads(ledger_path.read_text())
assert ledger["limits"] == {"usd": 10, "requests": 300}, (
    "The rejected cap extension is not applied"
)
if args.group == "cloud":
    route = {
        "model": "gemma4:31b",
        "endpoint": "https://ollama.com/v1",
        "input_usd_per_million": 1,
        "output_usd_per_million": 4,
    }
    (destination / "route-amendment.json").write_text(
        json.dumps(
            {
                "authorization": "User requested another available cloud model before release",
                "selected_route": route,
                "reservation_rates": "Conservative ceilings, not supplier prices",
                "prior_limits": ledger["limits"],
                "prior_requests": len(ledger["attempts"]),
                "prior_ledger_sha256": hashlib.sha256(
                    ledger_path.read_bytes()
                ).hexdigest(),
                "original_qwen_scope": "Unavailable in authenticated current cloud catalog; historical evidence retained",
            },
            indent=2,
        )
        + "\n"
    )
    if "ollama-cloud" in ledger["routes"]:
        assert ledger["routes"]["ollama-cloud"] == route
    else:
        ledger["routes"]["ollama-cloud"] = route
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
budget = ensure_budget()
rows = []


def persist():
    (destination / "results.json").write_text(
        json.dumps(
            {
                "version": toolkit.__version__,
                "wheel_sha256": wheel_hash,
                "rows": rows,
                "budget": budget.summary(),
                "published": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if args.group == "cloud":

    @toolkit.tool
    def echo(value: int) -> dict:
        """Return the supplied value unchanged."""
        return {"value": value}

    from agentic_systems_studio.lab.interop import observed_output

    for actor in (
        (args.framework,) if args.framework else ("native", "openai-agents", "strands")
    ):
        budget.phase = "release-followup/ollama-cloud/" + actor
        before = budget.summary()
        row = {
            "framework": actor,
            "model": "gemma4:31b",
            "route": "ollama-cloud",
            "input": {"value": 7},
            "passed": False,
            "budget_before": before,
        }
        (destination / (actor + "-plan.json")).write_text(
            json.dumps(row, indent=2) + "\n"
        )
        try:
            agent = toolkit.Agent(
                "cloud-echo",
                runtime=toolkit.runtime(
                    provider="ollama-runtime",
                    model="gemma4:31b",
                    endpoint="https://ollama.com/v1",
                    api_key=os.environ["OLLAMA_API_KEY"],
                    max_tokens=512,
                    max_retries=0,
                    max_turns=3,
                    max_tool_calls=1,
                    timeout_s=90,
                ),
                framework=toolkit.framework(actor),
                skills=(toolkit.skill(name="echo", tools=(echo,)),),
                instructions="Call echo exactly once with value=7. Preserve the input. Do not invent a result.",
                contract={
                    "tool_expectation": {"all_of": ["echo"]},
                    "completion": "when_required_tools_satisfied",
                },
                policy={"repair": False},
            )
            result = agent.run(
                row["input"], limits=toolkit.Limits(max_actions=30, timeout_s=120)
            )
            row["result"] = result.to_dict()
            events = [
                e
                for node in result.walk()
                for e in node.tool_events
                if e.name == "echo"
            ]
            assert result.ok and result.check_invariants().ok and len(events) == 1
            assert events[0].ok and events[0].input == {"value": 7}
            assert observed_output(events[0].output, "echo", {"value": 7}) == {
                "value": 7
            }
            row.update(
                passed=True,
                human_lineage=result.lineage().render(),
                agent_lineage=result.lineage().to_prompt_context(),
            )
        except Exception as exc:
            row["error"] = {
                "type": type(exc).__name__,
                "message": str(exc)[:1000].replace(
                    os.environ["OLLAMA_API_KEY"], "[REDACTED]"
                ),
            }
        row["budget_after"] = budget.summary()
        rows.append(row)
        persist()
        print(
            json.dumps({k: row[k] for k in ("framework", "passed", "budget_after")}),
            flush=True,
        )
else:
    from agentic_systems._engine.providers.bedrock.converse import _ConverseMixin
    from examples.applications.data_quality.example import capability, sample

    original = _ConverseMixin.converse
    wire = []

    def observe(self, **kwargs):
        record = {
            "messages": kwargs.get("messages"),
            "tools": kwargs.get("tools"),
            "system": kwargs.get("system"),
        }
        response = original(self, **kwargs)
        record["response"] = response
        wire.append(json.loads(json.dumps(record)))
        return response

    _ConverseMixin.converse = (
        observe  # Observe only; delegate arguments/response unchanged.
    )
    budget.phase = "release-followup/bedrock-null-diagnostic"
    agent = toolkit.Agent(
        "profile_rows",
        runtime=toolkit.runtime(
            provider="bedrock-runtime",
            model="qwen.qwen3-32b-v1:0",
            region="us-east-2",
            api_key=os.environ["AWS_BEARER_TOKEN_BEDROCK"],
            max_tokens=1024,
            max_retries=0,
            max_turns=3,
            max_tool_calls=1,
            timeout_s=90,
        ),
        skills=(capability,),
        instructions="Call profile_rows exactly once with the supplied input unchanged. Only the Tool determines business output.",
        contract={
            "tool_expectation": {"all_of": ["profile_rows"]},
            "completion": "when_required_tools_satisfied",
        },
        policy={"repair": False},
    )
    result = agent.run(sample, limits=toolkit.Limits(max_actions=30, timeout_s=120))
    rows.append(
        {
            "route": "bedrock-runtime",
            "framework": "native",
            "passed": result.ok,
            "result": result.to_dict(),
            "input": sample,
            "wire": wire,
        }
    )
    persist()
    print(
        json.dumps(
            {
                "passed": result.ok,
                "observed_converse_calls": len(wire),
                "budget": budget.summary(),
            }
        )
    )
