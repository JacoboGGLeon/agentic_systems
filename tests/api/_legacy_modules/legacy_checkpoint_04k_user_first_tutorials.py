from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TUTORIALS = REPO_ROOT / "tutorials"


def test_mvp_tutorial_roots_are_user_first() -> None:
    roots = sorted(p.name for p in TUTORIALS.iterdir() if p.is_dir() and not p.name.startswith("__"))
    assert roots == ["notebooks", "skills"]
    assert not (TUTORIALS / "human_output.py").exists()


def test_user_tutorial_assets_are_centralized() -> None:
    assert not (TUTORIALS / "roadmap").exists()
    assert (TUTORIALS / "notebooks").exists()
    assert (TUTORIALS / "skills" / "accountability_otc").exists()


def test_tutorials_have_progressive_walkthrough_routes() -> None:
    fundamentals = sorted(p.name for p in (REPO_ROOT / "tutorials").glob("*.ipynb"))
    assert fundamentals == [
        "00_runtime_api.ipynb",
        "00_runtime_bedrock_provider_api.ipynb",
        "00_runtime_openai_provider_api.ipynb",
        "00_runtime_scheduler_api.ipynb",
        "01_tool_api.ipynb",
        "02_skill_api.ipynb",
        "03_agent_api.ipynb",
        "04_human_result_api.ipynb",
        "05_lineage_memory_api.ipynb",
        "06_integrations_strands_api.ipynb",
        "07_integrations_openai_runtime_api.ipynb",
        "08_system_api.ipynb",
        "09_graph_api.ipynb",
        "10_environment_eval_api.ipynb",
        "10_multi-agentic-system-api.ipynb",
        "11_multi-agentic-graph-api.ipynb",
        "12_single agentic_system.ipynb",
        "13_multi agentic_system.ipynb",
    ]
