from __future__ import annotations

import ast
import json
from pathlib import Path
import tomllib

import agentic_systems
from agentic_systems.api import PUBLIC_API


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "tutorials"
EXPECTED_NOTEBOOKS = [
    "00_runtime_api.ipynb",
    "00_runtime_bedrock_provider_api.ipynb",
    "00_runtime_openai_provider_api.ipynb",
    "00_runtime_scheduler_api.ipynb",
    "00_runtime_vllm_provider_api.ipynb",
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
    "11_single_agentic_system_api.ipynb",
    "12_multi_agentic_system_api.ipynb",
    "13_multi_agentic_graph_api.ipynb",
]


def _notebook(name: str) -> dict:
    return json.loads((TUTORIALS / name).read_text(encoding="utf-8"))


def _source(notebook: dict) -> str:
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
    )


def test_release_candidate_version_and_public_inventory_are_consistent():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["version"] == "1.1.0rc1"
    assert agentic_systems.__version__ == "1.1.0rc1"
    assert len(PUBLIC_API) == 106
    assert "InspectReport" in PUBLIC_API

    api_docs = (ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    assert "InspectReport" in api_docs
    assert "`PUBLIC_API` | 106" in (
        ROOT / "docs" / "GRAMMAR_TO_API.md"
    ).read_text(encoding="utf-8")
    assert "Tests: 359 passed, 0 skipped" in (
        ROOT / "README.md"
    ).read_text(encoding="utf-8")
    assert "include CHANGELOG.md" in (
        ROOT / "MANIFEST.in"
    ).read_text(encoding="utf-8")


def test_canonical_notebooks_are_clean_public_and_statically_executable():
    paths = sorted(path.name for path in TUTORIALS.glob("*.ipynb"))
    assert paths == EXPECTED_NOTEBOOKS

    for name in paths:
        notebook = _notebook(name)
        source = _source(notebook)
        assert "import agentic_systems as toolkit" in source
        parameter_sections = [
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "markdown"
            and "".join(cell.get("source", [])).startswith("## Parámetros de ")
        ]
        assert len(parameter_sections) == 1
        assert "from agentic_systems." not in source
        assert "import agentic_systems." not in source
        assert "python-direct" not in source
        assert "PYTHON_DIRECT_ENGINE" not in source

        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] != "code":
                continue
            assert cell.get("execution_count") is None
            assert cell.get("outputs", []) == []
            code = "".join(cell.get("source", []))
            compile(
                code,
                f"{name}#cell-{index}",
                "exec",
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
            )


def test_tutorial_claims_match_checkpoint_1_1_contracts():
    runtime = _source(_notebook("00_runtime_api.ipynb"))
    strands = _source(_notebook("06_integrations_strands_api.ipynb"))
    agents_style = _source(
        _notebook("07_integrations_openai_runtime_api.ipynb")
    )
    system = _source(_notebook("08_system_api.ipynb"))
    evals = _source(_notebook("10_environment_eval_api.ipynb"))

    assert "provider_profiles()" in runtime
    assert "declarative-only" in strands
    assert 'framework_profile("strands")' in strands
    assert "style-only" in agents_style
    assert 'framework_profile("openai-agents")' in agents_style
    assert "if result is None:" in agents_style
    assert "inspection.to_dict()" in system
    assert "inspection.human_text()" in system
    assert '"models_executed": 0' in system
    assert 'determinism="deterministic"' in evals
    assert "reproducibility_conditions" in evals


def test_release_documents_state_manual_and_live_evidence_limits():
    migration = (ROOT / "docs" / "MIGRATION_1_0_TO_1_1.md").read_text(
        encoding="utf-8"
    )
    release = (ROOT / "docs" / "RELEASE_CANDIDATE_1_1.md").read_text(
        encoding="utf-8"
    )
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "1.1.0rc1" in migration
    assert "Full cell execution" in release
    assert "manual notebook matrix" in release
    assert "Live OpenAI, Bedrock, vLLM" in changelog
    assert "not part of 1.1" in changelog
