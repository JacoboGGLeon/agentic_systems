import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "examples/agentic_systems_studio/src"))

from agentic_systems_studio import ConversationConfig, build_conversational_system  # noqa: E402
from agentic_systems_studio.conversation import safe_calculate, prepare_conversation_context  # noqa: E402
from agentic_systems_studio.presentation import validate_generated_agentic_systems_code  # noqa: E402


@pytest.mark.parametrize("framework", ["native", "langgraph", "openai-agents", "strands"])
def test_conversation_uses_real_python_framework_with_memory(framework):
    studio = build_conversational_system(ConversationConfig(framework=framework))
    first = studio.run("Hola")
    second = studio.run("Otra pregunta", history=[{"role": "user", "content": "Hola"}])
    assert first.ok and second.ok and first.text and second.text
    assert second.data["history_turns"] == 1
    assert second.check_invariants().ok
    assert json.loads(json.dumps(second.to_dict()))["ok"]
    assert studio.inspect()["framework"] == framework


def test_tool_math_does_not_execute_arbitrary_python():
    assert safe_calculate.run({"expression": "17*19"}).data["result"] == 323
    assert not safe_calculate.run({"expression": "__import__('os').getcwd()"}).ok
    assert not safe_calculate.run({"expression": "10**1000"}).ok


def test_bounded_context_and_generated_api_validation():
    result = prepare_conversation_context.run({"message": "new", "messages": [{"role": "user", "content": "x" * 5000}] * 20})
    assert result.ok and len(result.data["history"]) == 12 and len(result.data["history"][0]["content"]) == 2000
    validate_generated_agentic_systems_code("import agentic_systems as toolkit\na=toolkit.Agent('a',toolkit.Action('x',lambda d:d))")
    with pytest.raises(ValueError, match="not a public"):
        validate_generated_agentic_systems_code("import agentic_systems as toolkit\na=toolkit.agent()")
    validate_generated_agentic_systems_code("import agentic_systems as ag\na=ag.Agent('a',ag.Action('x',lambda d:d))")
    with pytest.raises(ValueError, match="not a public"):
        validate_generated_agentic_systems_code("import agentic_systems as ag\na=ag.agent()")


def test_no_silent_provider_selection_and_no_ungoverned_live(monkeypatch):
    with pytest.raises(ValueError):
        ConversationConfig(provider="auto")
    from agentic_systems_studio.budget import ensure_budget
    monkeypatch.delenv("AGENTIC_213_BUDGET_FILE", raising=False)
    with pytest.raises(RuntimeError, match="authorized"):
        ensure_budget()


def test_budget_stops_before_second_request(tmp_path):
    from agentic_systems_studio.budget import CampaignBudget, BudgetExceeded
    budget = CampaignBudget(tmp_path / "ledger.json", {"openai-runtime": {"endpoint": "https://api.openai.com/v1",
        "model": "fixture", "input_usd_per_million": 5, "output_usd_per_million": 20}}, "offline", usd=1, requests=1)
    request = json.dumps({"model": "fixture", "max_tokens": 128})
    budget.reserve("https://api.openai.com/v1/chat/completions", request)
    with pytest.raises(BudgetExceeded):
        budget.reserve("https://api.openai.com/v1/chat/completions", request)
    assert budget.summary()["attempts"] == 1


def test_catalog_builds_without_inference_and_launcher_is_packaged():
    from agentic_systems_studio.systems import build_all, compose_systems
    from agentic_systems_studio.server import resolve_studio_app
    systems = build_all(ConversationConfig(provider="openai-runtime", model="configured-model"))
    assert len(systems) == 10
    for item in systems:
        assert item.inspect()["system"] and "flowchart" in item.mermaid()
    assert compose_systems(systems[:2]).inspect()
    assert resolve_studio_app().name == "ui.py"
    from agentic_systems_studio.components import TOOL_ASSETS
    assert TOOL_ASSETS and all(asset.metadata["tool_name"] for asset in TOOL_ASSETS)
    json.dumps([asset.to_dict() for asset in TOOL_ASSETS])
