from __future__ import annotations

import json
import re
from pathlib import Path

import agentic_systems as toolkit
from agentic_systems.registry import FRAMEWORKS, PROVIDERS


ROOT = Path(__file__).resolve().parents[2]
CORE_NARRATIVES = (
    ROOT / "README.md",
    ROOT / "INSTALL.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "NARRATIVE_CONTRACT.md",
    ROOT / "docs" / "ONBOARDING_FIRST_RUN.md",
    ROOT / "docs" / "RUNTIME_AND_FRAMEWORK_CONTRACTS.md",
)
UNICODE_ARROWS = ("→", "←", "↔", "⇒")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_core_narrative_mirrors_the_runtime_registry() -> None:
    readme = _text(ROOT / "README.md")
    runtime_contract = _text(ROOT / "docs" / "RUNTIME_AND_FRAMEWORK_CONTRACTS.md")
    narrative_contract = _text(ROOT / "docs" / "NARRATIVE_CONTRACT.md")

    for definition in PROVIDERS:
        assert definition.name in readme
        assert definition.name in runtime_contract
        assert definition.name in narrative_contract

    for definition in FRAMEWORKS:
        assert definition.name in readme
        assert definition.name in runtime_contract
        assert definition.name in narrative_contract

    assert not re.search(r"^\|\s*`?auto`?\s*\|", readme, flags=re.MULTILINE)
    assert re.search(
        r"`auto` is a selection\s+mode, not a sixth Provider",
        narrative_contract,
    )


def test_core_narrative_preserves_the_computational_grammar() -> None:
    narrative = "\n".join(_text(path) for path in CORE_NARRATIVES)
    readme = _text(ROOT / "README.md")

    assert "Tool -> Skill -> Agent -> System" in narrative
    assert "Tool -> Skill -> Agent -> System -> Graph" not in narrative
    assert "Environment -> Episode -> Step" in narrative
    assert "Tool -> Agent -> Skill" not in narrative
    assert "System -> Graph -> Environment -> Eval" not in narrative
    assert not any(arrow in narrative for arrow in UNICODE_ARROWS)
    assert "### 5. System" in readme
    assert "Native AgenticSystem" not in readme
    assert "AgenticSystem" not in readme
    assert "Agent pipeline" in readme
    assert "System owns:" in readme
    assert "Graph owns:" in readme
    assert "## A Grammar You Can Execute" in readme
    assert "This is not a lowest-common-denominator wrapper" in readme
    assert "Provider  -> who generates or executes" in readme
    assert "Framework -> who controls the Agent loop" in readme
    assert "Graph     -> what application topology runs" in readme
    assert '`provider="langgraph"` is invalid' in readme
    assert '`framework="langgraph"`' in readme
    assert "minimal one-node `StateGraph`" in readme
    assert "It does **not** invent business routing" in readme


def test_normative_docs_preserve_orthogonal_boundaries_and_example_identity() -> None:
    api = _text(ROOT / "docs" / "API.md")
    model = _text(ROOT / "docs" / "COMPUTATIONAL_MODEL.md")
    run_result = _text(ROOT / "docs" / "RUNRESULT_CONTRACT.md")

    assert "Computation: function -> Tool -> Skill -> Agent -> System" in model
    assert "Composition: Agent pipeline | System execution plan | Graph topology" in model
    assert "Time:        Environment -> Episode -> Step" in model
    assert "Evidence:    Eval observes Agent, System or Episode behavior" in model
    assert "System -> Graph -> Environment -> Eval" not in model
    assert "function -> Tool -> Skill -> Agent -> AgenticSystem" not in model
    assert "## Environment" in api
    assert "## Evals" in api
    assert "## Environment And Evals" not in api
    assert '{"procedure": ["20 + 22"], "final_result": 42}' in api
    assert 'question="What is 20 + 22?"' in api
    assert '{"procedure": ["20 + 22 = 42"], "final_result": 42}' in run_result
    assert '"2 + 3' not in api
    assert '"2 + 3' not in run_result


def test_current_onboarding_does_not_claim_an_unpublished_pypi_release() -> None:
    narrative = "\n".join(_text(path) for path in CORE_NARRATIVES)
    onboarding = _text(ROOT / "docs" / "ONBOARDING_FIRST_RUN.md")

    assert not re.search(r"pip install .*agentic-systems(?:\[[^]]+\])?==2\.1\.0", narrative)
    assert f'assert toolkit.__version__ == "{toolkit.__version__}"' in onboarding
    assert "OLLAMA_BASE_URL" in onboarding
    assert "OLLAMA_MODEL" in onboarding
    assert "RUN_OLLAMA_LIVE" in onboarding


def test_auto_tutorial_derives_provider_inventory_from_the_public_registry() -> None:
    path = ROOT / "tutorials" / "providers" / "00_auto.ipynb"
    notebook = json.loads(_text(path))
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )

    assert "toolkit.providers.provider_profiles()" in source
    assert "profile.capability(\"model_generation\")" in source
    assert "model_provider_names" in source


def test_zero_to_hero_is_a_progressive_grammar_not_a_snippet_catalog() -> None:
    readme = _text(ROOT / "README.md")
    markers = (
        "Start with the smallest executable unit",
        "A Skill is the modularity boundary",
        "An Agent turns context into actions",
        "Moving from OpenAI to Ollama, Bedrock or vLLM",
        "A **System** turns those parts into one",
        "Use a Graph when the route is part of the application contract",
        "Environment is not an Eval harness disguised as an abstraction",
        "Environment is useful without Eval, and Eval is useful without",
        "`RunResult` is the portability boundary",
    )

    for marker in markers:
        assert marker in readme

    headings = (
        "### 1. Deterministic Tool",
        "### 2. Runtime Skill",
        "### 3. Deterministic Agent",
        "### 4. Provider-Backed Agent",
        "### 5. System",
        "### 6. Graph",
        "### 7. Environment",
        "### 8. Evals",
        "### 9. Results, Lineage And Human Output",
    )
    positions = [readme.index(heading) for heading in headings]
    assert positions == sorted(positions)
    zero_to_hero = readme[
        readme.index("## From Zero-to-Hero") : readme.index("## Integrations")
    ]
    assert zero_to_hero.count("skills=[calculator_skill]") == 2
    assert zero_to_hero.count("structured_request") >= 5
    assert "system.skill(calculator_skill)" in zero_to_hero
    assert "calculator_agent = calculator_agent.bind(system)" in zero_to_hero
    assert "calculator_agent.pipeline(name=\"calculator_pipeline\")" in zero_to_hero
    assert "result = agent_pipeline.run(structured_request)" in zero_to_hero
    assert "system.compile(" in zero_to_hero
    assert "name=\"calculator_system_pipeline\"" in zero_to_hero
    assert "toolkit.show(system_pipeline.inspect(), title=\"System execution plan\")" in zero_to_hero
    assert "result = system_pipeline.run(structured_request)" in zero_to_hero
    assert "toolkit.show(graph.inspect(), title=\"Native Graph inspection\")" in zero_to_hero
    for reference in (
        "[API: Agent and `Agent.pipeline`](docs/API.md#agents)",
        "[Notebook: Core 03 - Agent](tutorials/core/03_agent.ipynb)",
        "[API: Tools](docs/API.md#tools)",
        "[Notebook: Core 01 - Tool](tutorials/core/01_tool.ipynb)",
        "[API: Skills](docs/API.md#skills)",
        "[Notebook: Core 02 - Skills](tutorials/core/02_skills.ipynb)",
        "[OpenAI notebook](tutorials/providers/01_openai.ipynb)",
        "[Ollama notebook](tutorials/providers/04_ollama.ipynb)",
        "[Bedrock notebook](tutorials/providers/02_bedrock.ipynb)",
        "[vLLM notebook](tutorials/providers/03_vllm.ipynb)",
        "[API: System and static inspection](docs/API.md#system)",
        "[Notebook: Core 05 - System](tutorials/core/05_system.ipynb)",
        "[API: native Graph and `GraphApp.inspect`](docs/API.md#graph-integrations)",
        "[Notebook: Core 06 - Native Graph](tutorials/core/06_graph_native.ipynb)",
        "[API: Environment](docs/API.md#environment)",
        "[API: Evals](docs/API.md#evals)",
        "[API: Results and Lineage Memory](docs/API.md#results-and-human-output)",
        "[Notebook: Core 04 - Results and Lineage](tutorials/core/04_results_lineage.ipynb)",
    ):
        assert reference in zero_to_hero

    assert 'question="What is 20 + 22?"' in zero_to_hero
    assert '"final_result": 42' in zero_to_hero
    assert 'question="What is 2 + 3?"' not in zero_to_hero
    assert '"final_result": 5' not in zero_to_hero
    assert "system_agent" not in zero_to_hero
    assert "deterministic_agent" not in zero_to_hero
    assert "portable_calculator" not in zero_to_hero
    assert "from collections.abc import Mapping" not in zero_to_hero
    assert 'return float(state["result"].ok)' in zero_to_hero
    assert "SDK response classes or Provider-specific payloads" in zero_to_hero
