from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

import pytest

import agentic_systems
from agentic_systems.api import (
    BEDROCK_PRIMITIVE_API,
    CHAIN_API,
    CORE_API,
    ENGINE_API,
    NOTEBOOK_API,
    PUBLIC_API,
    RECOMMENDED_API,
)
from agentic_systems.engines.names import (
    BEDROCK_RUNTIME_ENGINE,
    PYTHON_RUNTIME_ENGINE,
    VLLM_RUNTIME_ENGINE,
    canonical_engine_name,
    supported_engine_names,
)
from agentic_systems.providers.base import ToolRegistryRuntime


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "tutorials"
EXPECTED_NOTEBOOKS = [
    "core/00_runtime_scheduler.ipynb",
    "core/01_tool.ipynb",
    "core/02_skills.ipynb",
    "core/03_agent.ipynb",
    "core/04_results_lineage.ipynb",
    "core/05_system.ipynb",
    "core/06_graph_native.ipynb",
    "core/07_environment_eval.ipynb",
    "core/08_single_agentic_system.ipynb",
    "core/09_multi_agentic_system.ipynb",
    "core/10_multi_agent_graph.ipynb",
    "frameworks/00_langgraph.ipynb",
    "frameworks/01_openai_agents.ipynb",
    "frameworks/02_aws_strands.ipynb",
    "providers/00_auto.ipynb",
    "providers/01_openai.ipynb",
    "providers/02_bedrock.ipynb",
    "providers/03_vllm.ipynb",
]


def _notebook(name: str) -> dict:
    return json.loads((TUTORIALS / name).read_text(encoding="utf-8"))


def _source(notebook: dict) -> str:
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
    )


def test_alpha_version_surface_and_packaging_are_consistent():
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = tomllib.loads(pyproject_text)

    assert project["project"]["version"] == "2.0.0a1"
    assert agentic_systems.__version__ == "2.0.0a1"
    assert len(PUBLIC_API) == 112
    assert "InspectReport" in PUBLIC_API
    assert not hasattr(agentic_systems, "build_single_agent_step_graph")
    assert not hasattr(agentic_systems, "PUBLIC_API")

    extras = project["project"]["optional-dependencies"]
    assert "tutorials" not in extras
    assert "vll" not in extras
    assert "vllm" in extras
    assert set(extras["dev"]) <= set(extras["all"])
    base_dependencies = project["project"]["dependencies"]
    assert not any(name in requirement for name in ("langgraph", "awswrangler", "boto3", "vllm") for requirement in base_dependencies)
    assert extras["openai-agents"] == ["openai-agents>=0.18.3,<0.19"]
    assert extras["strands"] == ["strands-agents>=1.29.0,<2", "mcp>=1,<2"]

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "API -> Docs -> Tutorials -> explicit automated or manual evidence" in readme
    assert "Core coverage: 100.00%" in readme
    assert "Coverage scope: Bedrock facade and internal package excluded from core; separately gated at 100%" in readme
    assert "build_single_agent_step_graph" not in readme
    assert "agentic-systems[tutorials" not in install
    assert "1.1.0rc1" not in install
    assert "prune tutorials" in manifest
    assert "include CHANGELOG.md" in manifest

    api_docs = (ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    assert "InspectReport" in api_docs
    model = (ROOT / "docs" / "COMPUTATIONAL_MODEL.md").read_text(encoding="utf-8")
    assert "baseline contains 112 top-level symbols" in model


def test_public_api_groups_and_canonical_namespace_boundary():
    assert tuple(agentic_systems.__all__) == PUBLIC_API
    assert agentic_systems.core.RunResult is agentic_systems.RunResult
    assert agentic_systems.providers.ToolRegistryRuntime is ToolRegistryRuntime
    assert hasattr(agentic_systems.integrations, "__all__")
    assert "AgenticSystem" in CORE_API
    assert "Skill" in CORE_API
    assert "Toolkit" not in PUBLIC_API
    assert "BedrockRuntimeClient" in BEDROCK_PRIMITIVE_API
    assert "Chain" in CHAIN_API
    assert "run_result_view" in NOTEBOOK_API
    assert "BEDROCK_RUNTIME_ENGINE" in ENGINE_API
    assert "VLLM_RUNTIME_ENGINE" in ENGINE_API
    assert supported_engine_names() == (
        BEDROCK_RUNTIME_ENGINE,
        "openai-runtime",
        PYTHON_RUNTIME_ENGINE,
        VLLM_RUNTIME_ENGINE,
    )
    assert "bedrock" not in supported_engine_names()
    assert "bedrock" not in supported_engine_names()
    for ambiguous_name in ("local", "runtime", "python_runtime", "vllm", "vllm_runtime"):
        with pytest.raises(ValueError, match="Unknown runtime/provider"):
            canonical_engine_name(ambiguous_name)
    assert not hasattr(agentic_systems, "Toolkit")
    assert not hasattr(agentic_systems, "ToolEvent")

    from agentic_systems.skills import LoadedSkill, SkillManifest, load_skill
    from agentic_systems.tools import (
        Toolkit,
        ToolEvent,
        assert_dict_tool_output,
        expand_tool_inputs,
        now_ms,
    )

    assert Toolkit.__name__ == "Toolkit"
    assert ToolEvent.__name__ == "ToolEvent"
    assert assert_dict_tool_output("demo", {"ok": True}) == {"ok": True}
    assert expand_tool_inputs(None) == ()
    assert isinstance(now_ms(), float)
    assert LoadedSkill.__name__ == "LoadedSkill"
    assert SkillManifest.__name__ == "SkillManifest"
    assert callable(load_skill)


def test_canonical_notebooks_are_clean_public_and_statically_executable():
    paths = sorted(path.relative_to(TUTORIALS).as_posix() for path in TUTORIALS.rglob("*.ipynb"))
    assert paths == EXPECTED_NOTEBOOKS

    for name in paths:
        notebook = _notebook(name)
        source = _source(notebook)
        assert "import agentic_systems as toolkit" in source
        parameter_sections = [
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "markdown"
            and "".join(cell.get("source", [])).startswith("## Parametros de ")
        ]
        assert len(parameter_sections) == 1
        assert "from agentic_systems." not in source
        assert "import agentic_systems." not in source
        assert "python-direct" not in source
        assert "PYTHON_RUNTIME_ENGINE" not in source

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


def test_tutorial_claims_match_current_product_contracts():
    runtime = _source(_notebook("providers/00_auto.ipynb"))
    skills = _source(_notebook("core/02_skills.ipynb"))
    native_graph = _source(_notebook("core/06_graph_native.ipynb"))
    langgraph = _source(_notebook("frameworks/00_langgraph.ipynb"))
    strands = _source(_notebook("frameworks/02_aws_strands.ipynb"))
    openai_agents = _source(_notebook("frameworks/01_openai_agents.ipynb"))
    system = _source(_notebook("core/05_system.ipynb"))
    evals = _source(_notebook("core/07_environment_eval.ipynb"))

    assert "provider_profiles()" in runtime
    assert 'toolkit.load_skill("tutorials/skills/accountability_otc")' in skills
    assert 'GRAPH_ENGINE = "portable"' in native_graph
    assert 'engine="langgraph"' in langgraph
    assert "conditional_edges=" in langgraph
    assert "await app.arun" in langgraph
    assert 'framework_profile("strands")' in strands
    assert "streamable_http_client" in strands
    assert "stdio_client" in strands
    assert "structured_output_model" in strands
    assert 'framework_profile("openai-agents")' in openai_agents
    assert "SQLiteSession" in openai_agents
    assert "input_guardrail" in openai_agents
    assert "native_handoff" in openai_agents
    assert "await agent.arun" in openai_agents
    assert "inspection.to_dict()" in system
    assert "toolkit.show(inspection" in system
    assert '"models_executed": 0' in system
    assert 'determinism="deterministic"' in evals
    assert "reproducibility_conditions" in evals


def test_changelog_separates_automated_and_external_evidence():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "15 deterministic notebooks" in changelog
    assert "3 external Provider notebooks" in changelog
    assert "53.17%" in changelog
    assert "`fail_under = 53.1`" in changelog
    assert "Live OpenAI, Bedrock and vLLM execution remains outside" in changelog

def test_canonical_grammar_factories_delegate_to_existing_types():
    assert RECOMMENDED_API[:7] == (
        "tool",
        "skill",
        "agent",
        "system",
        "graph",
        "environment",
        "eval",
    )

    capability = agentic_systems.skill(name="demo")
    composition = agentic_systems.system(
        runtime=agentic_systems.runtime(provider="python-runtime")
    )
    episode = agentic_systems.environment(
        [{"value": 1}],
        transition_fn=lambda row, action, info: {"value": row["value"]},
    )
    evaluation = agentic_systems.eval()

    assert isinstance(capability, agentic_systems.Skill)
    system_module = importlib.import_module("agentic_systems.system")
    assert callable(agentic_systems.system)
    assert system_module.AgenticSystem is agentic_systems.AgenticSystem
    assert composition.__class__ is agentic_systems.AgenticSystem

    assert isinstance(composition, agentic_systems.AgenticSystem)
    assert isinstance(episode, agentic_systems.AgenticEnvironment)
    assert isinstance(evaluation, agentic_systems.Evaluator)

def test_notebooks_follow_the_user_centered_api_first_standard():
    canonical_usage = {
        "core/01_tool.ipynb": "toolkit.tool",
        "core/02_skills.ipynb": "toolkit.skill(",
        "core/03_agent.ipynb": "toolkit.agent(",
        "core/05_system.ipynb": "toolkit.system(",
        "core/06_graph_native.ipynb": "toolkit.graph(",
        "core/07_environment_eval.ipynb": "toolkit.environment(",
        "core/08_single_agentic_system.ipynb": "toolkit.eval().run(",
        "core/09_multi_agentic_system.ipynb": "toolkit.system(",
        "core/10_multi_agent_graph.ipynb": "toolkit.graph(",
    }
    narrative_markers = (
        "Objetivo",
        "Historia",
        "Este notebook",
        "Contrato 1.1",
        "Checkpoint",
        "Fundamentals explora",
    )

    for name in EXPECTED_NOTEBOOKS:
        notebook = _notebook(name)
        source = _source(notebook)
        first_markdown = "".join(notebook["cells"][0].get("source", []))
        assert any(marker in first_markdown for marker in narrative_markers), name
        assert "api_coverage" in source, name
        assert "from tutorials" not in source, name
        assert "import tutorials" not in source, name
        assert "class Fake" not in source, name
        assert "unittest.mock" not in source, name
        assert "toolkit.Skill(" not in source, name
        assert "toolkit.AgenticSystem(" not in source, name
        if "toolkit.system(" in source:
            assert "toolkit.runtime(" in source, name
            assert source.index("toolkit.runtime(") < source.index("toolkit.system("), name
        if name in canonical_usage:
            assert canonical_usage[name] in source, name

    standard = (ROOT / "tutorials" / "README.md").read_text(encoding="utf-8")
    assert "## Contribution Standard" in standard
    assert "toolkit.environment(...)" in standard
    assert "package internals" in standard
    assert "Run All" in standard


def test_documentation_has_no_retired_parallel_sources():
    retired = {
        "BOUNDARIES.md",
        "COMPUTATIONAL_GRAMMAR.md",
        "EXECUTION_CONTEXT_DECISION.md",
        "FRAMEWORK_GRAPH_BOUNDARY.md",
        "GRAMMAR_TO_API.md",
        "PYTEST_COVERAGE_REPORT.md",
        "RUNRESULT_FINAL_ANSWER.md",
        "SEMANTICS.md",
        "SMOKE_CHECKLIST_2_4_9.md",
        "TEST_MIGRATION_1_1_2.md",
        "TUTORIAL_QUALITY_STANDARD.md",
        "MIGRATION_1_0_TO_1_1.md",
        "RELEASE_1_1_2.md",
        "CHECKPOINT_1_1_3.md",
        "STATIC_SYSTEM_INSPECTION.md",
        "SYSTEM_ENVIRONMENT_EVAL_SEMANTICS.md",
    }
    assert not any((ROOT / "docs" / name).exists() for name in retired)
    assert not (ROOT / "docs" / "adr").exists()
    assert not (ROOT / "docs" / "rfcs").exists()
    assert not (ROOT / "docs" / "history").exists()
