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
    PYTHON_DIRECT_ENGINE,
    VLLM_RUNTIME_ENGINE,
    canonical_engine_name,
    supported_engine_names,
)
from agentic_systems.providers.base import ToolRegistryRuntime


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


def test_maintenance_version_surface_and_packaging_are_consistent():
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = tomllib.loads(pyproject_text)

    assert project["project"]["version"] == "1.1.2"
    assert agentic_systems.__version__ == "1.1.2"
    assert len(PUBLIC_API) == 111
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
    assert "openai-agents" not in pyproject_text

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "API -> Docs -> Tutorials -> explicit automated or manual evidence" in readme
    assert "Core coverage: 100.00%" in readme
    assert "Coverage scope: Bedrock facade and internal package excluded from core; separately gated at 53.1%" in readme
    assert "build_single_agent_step_graph" not in readme
    assert "agentic-systems[tutorials" not in install
    assert "1.1.0rc1" not in install
    assert "prune tutorials" in manifest
    assert "include CHANGELOG.md" in manifest

    api_docs = (ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    assert "InspectReport" in api_docs
    assert "`PUBLIC_API` | 111" in (
        ROOT / "docs" / "GRAMMAR_TO_API.md"
    ).read_text(encoding="utf-8")


def test_public_api_groups_aliases_and_compatibility_boundary():
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
        PYTHON_DIRECT_ENGINE,
        VLLM_RUNTIME_ENGINE,
    )
    assert "bedrock" not in supported_engine_names(include_aliases=False)
    assert "bedrock" not in supported_engine_names(include_aliases=True)
    for ambiguous_name in ("local", "runtime", "python_runtime", "vllm", "vllm_runtime"):
        with pytest.raises(ValueError, match="Unknown runtime/provider"):
            canonical_engine_name(ambiguous_name)
    assert not hasattr(agentic_systems, "Toolkit")
    assert not hasattr(agentic_systems, "ToolEvent")

    from agentic_systems.skills import LoadedSkill, SkillManifest, load_skill
    from agentic_systems.tools.compat import (
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
            and "".join(cell.get("source", [])).startswith("## Parametros de ")
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


def test_tutorial_claims_match_release_1_1_contracts():
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
    assert "result = None" in agents_style
    assert "inspection.to_dict()" in system
    assert "toolkit.show(inspection" in system
    assert '"models_executed": 0' in system
    assert 'determinism="deterministic"' in evals
    assert "reproducibility_conditions" in evals


def test_release_documents_separate_automated_manual_and_external_evidence():
    release = (ROOT / "docs" / "RELEASE_1_1_2.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    notebook_matrix = (
        ROOT / "docs" / "MANUAL_NOTEBOOK_MATRIX_1_1.md"
    ).read_text(encoding="utf-8")

    assert "13 deterministic notebooks executed by pytest" in release
    assert "5 Provider notebooks checked statically" in release
    assert "Separate Bedrock coverage is 53.17%" in release
    assert "`fail_under = 53.1`" in release
    assert "external live Provider claims: 0" in notebook_matrix
    assert "Live OpenAI, Bedrock and vLLM execution remains outside" in changelog
    assert "API == Docs == Tutorials == Pytests" not in release

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
        "01_tool_api.ipynb": "toolkit.tool",
        "02_skill_api.ipynb": "toolkit.skill(",
        "03_agent_api.ipynb": "toolkit.agent(",
        "08_system_api.ipynb": "toolkit.system(",
        "09_graph_api.ipynb": "toolkit.graph(",
        "10_environment_eval_api.ipynb": "toolkit.environment(",
        "11_single_agentic_system_api.ipynb": "toolkit.eval().run(",
        "12_multi_agentic_system_api.ipynb": "toolkit.system(",
        "13_multi_agentic_graph_api.ipynb": "toolkit.graph(",
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

    standard = (ROOT / "docs" / "TUTORIAL_QUALITY_STANDARD.md").read_text(
        encoding="utf-8"
    )
    assert "API Antes Que Código Local" in standard
    assert "toolkit.environment(...)" in standard
    assert "La agnosticidad es obligatoria" in standard
    assert "rutas y registros públicos" in standard
