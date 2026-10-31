"""Nine real UI send/clear probes within the existing authorized campaign."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "revisions/2.1.4/learning-dev3"
sys.path[:0] = [
    str(ROOT / ".tmp/candidate214-dev3/site-packages"),
    str(ROOT),
    str(ROOT / "examples/agentic_systems_studio/src"),
]
from dotenv import load_dotenv  # noqa: E402
from agentic_systems_studio.budget import ensure_budget  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402
import agentic_systems as toolkit  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["AGENTIC_BUDGET_FILE"] = str(E / "campaign-budget.json")
assert toolkit.__version__ == "2.1.4.dev3"
budget = ensure_budget()
assert budget.summary()["remaining_requests"] >= 9
plan = json.loads((E / "live-plan.json").read_text(encoding="utf-8"))
directory = E / "ui-live" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
directory.mkdir(parents=True)
ui = ROOT / "examples/agentic_systems_studio/src/agentic_systems_studio/ui.py"
rows = []
for route, config in plan["routes"].items():
    provider = "ollama-runtime" if route == "ollama-gpu" else route
    prefix = {
        "openai-runtime": "OPENAI",
        "bedrock-runtime": "BEDROCK",
        "ollama-gpu": "OLLAMA",
    }[route]
    profile = directory / (route + ".env")
    # Credential-free connection contract; real keys stay in the process environment.
    content = (
        prefix
        + "_MODEL="
        + config["model"]
        + "\n"
        + prefix
        + "_MODEL_ID="
        + config["model"]
        + "\n"
    )
    if route == "bedrock-runtime":
        content += "AWS_REGION=us-east-2\nAWS_DEFAULT_REGION=us-east-2\n"
    else:
        content += prefix + "_BASE_URL=" + config["endpoint"] + "\n"
    profile.write_text(content, encoding="utf-8")
    os.environ["AGENTIC_SYSTEMS_ENV_FILE"] = str(profile)
    if route == "ollama-gpu":
        os.environ["OLLAMA_API_KEY"] = "ollama-local"
    for framework in plan["frameworks"]:
        budget.phase = "studio-ui/" + route + "/" + framework
        count = budget.summary()["attempts"]
        row = {
            "route": route,
            "framework": framework,
            "model": config["model"],
            "passed": False,
            "ui_sha256": hashlib.sha256(ui.read_bytes()).hexdigest(),
            "prompt": "Responde únicamente READY.",
        }
        try:
            app = AppTest.from_file(str(ui), default_timeout=120).run()
            app.selectbox(key="provider").set_value(provider).run()
            app.selectbox(key="framework").set_value(framework).run()
            app.chat_input[0].set_value(row["prompt"]).run()
            assert not app.exception, [str(e) for e in app.exception]
            result = app.session_state["last_result"]
            row["result"] = result.to_dict()
            assert result.ok and "READY" in result.text, result.to_dict()
            assert (
                result.meta["provider"] == provider
                and result.meta["framework"] == framework
            )
            assert any(n.model == config["model"] for n in result.walk())
            before_clear = budget.summary()["attempts"]
            app.button(key="clear_conversation").click().run()
            assert "last_result" not in app.session_state and not app.exception
            assert budget.summary()["attempts"] == before_clear
            row.update(
                passed=True,
                clear_history=True,
                requests_during_clear=0,
                human_lineage=result.lineage().render(),
                agent_lineage=result.lineage().to_prompt_context(),
            )
        except Exception as exc:
            row["error"] = {"type": type(exc).__name__, "message": str(exc)[-2500:]}
        row["requests"] = budget.summary()["attempts"] - count
        rows.append(row)
        (directory / "results.json").write_text(
            json.dumps(
                {
                    "rows": rows,
                    "budget": budget.summary(),
                    "scope": "Provider/framework selection, message send, normalized result rendering and history clear; not all possible UI paths",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {k: row[k] for k in ("route", "framework", "passed", "requests")}
            ),
            flush=True,
        )
print(json.dumps(budget.summary()), flush=True)
