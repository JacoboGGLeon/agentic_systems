from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import agentic_systems as toolkit
from scripts.update_tutorial_contract import CURRICULUM_ORDER


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "tutorials"
SHARED_SCENARIOS = tuple(toolkit.api_contract()["scenarios"])
EXPECTED_NOTEBOOKS = {
    "api/14_api_contract_matrix.ipynb",
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
    "providers/00_auto.ipynb",
    "providers/01_openai.ipynb",
    "providers/02_bedrock.ipynb",
    "providers/03_vllm.ipynb",
    "providers/04_ollama.ipynb",
    "frameworks/00_langgraph.ipynb",
    "frameworks/01_openai_agents.ipynb",
    "frameworks/02_aws_strands.ipynb",
    "frameworks/03_provider_framework_matrix.ipynb",
}
DIRECT_SDK_ROOTS = {"boto3", "openai", "subprocess", "requests", "urllib", "httpx"}
RUN_RESULT_FIELDS = {"final", "runtime", "usage", "validation"}


def _notebooks():
    return sorted(
        path
        for path in TUTORIALS.rglob("*.ipynb")
        if path.relative_to(TUTORIALS).parts[0] != "cli"
    )


def _relative(path: Path) -> str:
    return path.relative_to(TUTORIALS).as_posix()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _source(notebook):
    return "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])


def _code(notebook):
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )


def _api_claims(tree: ast.AST):
    values = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id == "api_coverage"
            for target in targets
        ):
            continue
        value = node.value
        assert isinstance(value, (ast.List, ast.Tuple)), (
            "api_coverage must be a literal list or tuple."
        )
        assert all(
            isinstance(item, ast.Constant) and isinstance(item.value, str)
            for item in value.elts
        )
        values.append([item.value for item in value.elts])
    return values


def test_canonical_notebook_inventory_and_cell_integrity():
    paths = _notebooks()
    assert {_relative(path) for path in paths} == EXPECTED_NOTEBOOKS
    for path in paths:
        notebook = _load(path)
        ids = [cell.get("id") for cell in notebook["cells"]]
        assert all(ids), path.name
        assert len(ids) == len(set(ids)), path.name
        assert all(
            "".join(cell.get("source", [])).strip() for cell in notebook["cells"]
        ), path.name
        first_markdown = next(
            cell for cell in notebook["cells"] if cell.get("cell_type") == "markdown"
        )
        assert "Objetivo" in "".join(first_markdown.get("source", [])), path.name


def test_curriculum_order_and_reviewed_narrative_are_1_to_1():
    assert set(CURRICULUM_ORDER) == EXPECTED_NOTEBOOKS
    guide = (TUTORIALS / "README.md").read_text(encoding="utf-8")

    for index, relative in enumerate(CURRICULUM_ORDER):
        notebook = _load(TUTORIALS / relative)
        metadata = notebook["metadata"]["agentic_systems"]
        source = _source(notebook)

        assert metadata["curriculum_order"] == index, relative
        assert metadata["narrative_reviewed"] == "2.1.0", relative
        expected_scenarios = [
            scenario["id"]
            for scenario in SHARED_SCENARIOS
            if relative in scenario["notebooks"]
        ]
        assert metadata["contract_scenarios"] == expected_scenarios, relative
        assert expected_scenarios, relative
        assert "Objetivo" in source, relative
        assert "## Parametros de " in source, relative
        assert "## Resultado e interpretacion" in source, relative
        numbered_sections = [
            int(value) for value in re.findall(r"^## (\d+)\)", source, re.M)
        ]
        assert numbered_sections == list(range(1, len(numbered_sections) + 1)), relative
        assert f"| {index:02d} | {relative} |" in guide, relative

        for cell in notebook["cells"]:
            if cell.get("cell_type") != "code":
                continue
            assert cell.get("execution_count") is None, relative
            assert cell.get("outputs", []) == [], relative


def test_notebook_metadata_matches_layer_and_literal_api_claims():
    frameworks = {
        "00_langgraph.ipynb": "langgraph",
        "01_openai_agents.ipynb": "openai-agents",
        "02_aws_strands.ipynb": "strands",
        "03_provider_framework_matrix.ipynb": "all",
    }
    provider_names = {
        "00_auto.ipynb": "auto",
        "01_openai.ipynb": "openai-runtime",
        "02_bedrock.ipynb": "bedrock-runtime",
        "03_vllm.ipynb": "vllm-runtime",
        "04_ollama.ipynb": "ollama-runtime",
    }
    for path in _notebooks():
        notebook = _load(path)
        relative = path.relative_to(TUTORIALS)
        metadata = notebook.get("metadata", {}).get("agentic_systems", {})
        assert set(metadata) >= {
            "layer",
            "provider",
            "framework",
            "execution_mode",
            "api_coverage",
        }, _relative(path)
        assert metadata["layer"] == relative.parts[0]
        claims = _api_claims(ast.parse(_code(notebook), filename=_relative(path)))
        assert metadata["api_coverage"] == claims[0]
        if metadata["layer"] == "core":
            assert metadata["provider"] == "python-runtime"
            assert metadata["framework"] == "native"
            assert metadata["execution_mode"] == "offline"
        elif metadata["layer"] == "providers":
            assert metadata["provider"] == provider_names[path.name]
            assert metadata["framework"] == "native"
        elif metadata["layer"] == "api":
            assert metadata["provider"] == "python-runtime"
            assert metadata["framework"] == "native"
            assert metadata["execution_mode"] == "offline"
        else:
            assert metadata["provider"] == "python-runtime"
            assert metadata["framework"] == frameworks[path.name]
            assert metadata["live_provider"] == "auto"


def test_notebook_text_has_no_encoding_corruption_or_stale_constructor():
    broken = re.compile(r"\w\?\w|\ufffd")
    for path in _notebooks():
        source = _source(_load(path))
        assert not broken.search(source), path.name
        assert "toolkit.AgenticSystem(" not in source, path.name
        assert "skip" not in source.lower(), path.name
        assert "default arithmetic prompt" not in source, path.name
        assert "Empieza con 10, suma 20" not in source, path.name


def test_code_cells_parse_and_do_not_shadow_public_api():
    for path in _notebooks():
        notebook = _load(path)
        for index, cell in enumerate(notebook["cells"]):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            tree = ast.parse(source, filename=f"{path.name}:cell-{index}")
            for node in ast.walk(tree):
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    assert not hasattr(toolkit, node.name), (
                        f"{path.name}:{index} shadows toolkit.{node.name}"
                    )


def test_canonical_notebooks_do_not_bypass_provider_or_output_boundaries():
    for path in _notebooks():
        relative = _relative(path)
        allowed = (
            {"subprocess"}
            if relative
            in {
                "frameworks/02_aws_strands.ipynb",
                "providers/03_vllm.ipynb",
            }
            else set()
        )
        forbidden_roots = DIRECT_SDK_ROOTS - allowed
        tree = ast.parse(_code(_load(path)), filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
                assert not roots & forbidden_roots, (relative, roots & forbidden_roots)
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                assert root not in forbidden_roots, (relative, root)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "print", relative
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                for target in targets:
                    if isinstance(target, ast.Attribute):
                        assert target.attr not in RUN_RESULT_FIELDS, (
                            relative,
                            target.attr,
                        )


def test_notebooks_do_not_fabricate_results_or_execute_manual_graph_fallbacks():
    forbidden = (
        "toolkit.RunResult(",
        "RunResult(",
        ".apply_validation(",
        "results=[]",
        "if LANGGRAPH_AVAILABLE",
        "if langgraph_available",
        "for node in nodes",
    )
    for path in _notebooks():
        source = _code(_load(path))
        for needle in forbidden:
            assert needle not in source, f"{path.name} contains {needle}"


def test_provider_notebooks_use_the_same_public_execution_route():
    for name in (
        "providers/01_openai.ipynb",
        "providers/03_vllm.ipynb",
        "providers/02_bedrock.ipynb",
        "providers/04_ollama.ipynb",
    ):
        source = _code(_load(TUTORIALS / name))
        route = [
            "toolkit.runtime(",
            "toolkit.system(",
            "system.agent(",
            "agent.run(",
            "toolkit.human_result(",
        ]
        positions = [source.index(item) for item in route]
        assert positions == sorted(positions), name
        assert "toolkit.run_result_output(" in source, name


def test_graph_notebooks_execute_only_through_toolkit_graph():
    for name in (
        "core/06_graph_native.ipynb",
        "core/10_multi_agent_graph.ipynb",
        "frameworks/00_langgraph.ipynb",
    ):
        source = _code(_load(TUTORIALS / name))
        assert "toolkit.graph(" in source
        assert "app.run(" in source
        assert "importlib" not in source


def test_api_claims_are_literal_public_and_materialized():
    metadata = {"__all__", "__name__", "__version__"}
    for path in _notebooks():
        notebook = _load(path)
        tree = ast.parse(_code(notebook), filename=path.name)
        claim_groups = _api_claims(tree)
        assert len(claim_groups) == 1, path.name
        api_claims = claim_groups[0]
        assert api_claims, path.name

        used_toolkit = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "toolkit"
        }
        claimed_toolkit = {
            match.group(1)
            for claim in api_claims
            if (match := re.match(r"toolkit\.([A-Za-z_]\w*)", claim))
        }
        assert claimed_toolkit == used_toolkit - metadata, path.name

        used_methods = {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        for claim in api_claims:
            toolkit_match = re.match(r"toolkit\.([A-Za-z_]\w*)", claim)
            if toolkit_match:
                name = toolkit_match.group(1)
                assert hasattr(toolkit, name), (
                    f"{path.name} claims missing toolkit.{name}"
                )
                continue
            method_match = re.search(r"\.([A-Za-z_]\w*)", claim)
            assert method_match, f"{path.name} has uncheckable API claim {claim!r}"
            method = method_match.group(1)
            assert method in used_methods, f"{path.name} does not materialize {claim}"


def test_every_direct_toolkit_attribute_is_in_public_api():
    public = set(toolkit.__all__) | {"__all__", "__name__"}
    for path in _notebooks():
        tree = ast.parse(_code(_load(path)), filename=path.name)
        used = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "toolkit"
        }
        assert used <= public, (
            f"{path.name} uses non-public names: {sorted(used - public)}"
        )


def test_tutorial_repository_layout_and_assets_are_intentional():
    roots = sorted(
        path.name
        for path in TUTORIALS.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    )
    assert roots == ["api", "cli", "core", "frameworks", "providers", "skills"]
    assert not (TUTORIALS / "human_output.py").exists()
    assert not (TUTORIALS / "roadmap").exists()
    assert not list(TUTORIALS.glob("*.ipynb"))
    assert (TUTORIALS / "skills" / "tutorial_api_inspection").exists()
    assert (TUTORIALS / "frameworks" / "mcp_echo_server.py").exists()


def test_tutorials_use_public_output_views_without_inlining_helpers():
    forbidden = (
        "def result_output(",
        "def _tool_event_output(",
        "def _result_dict_output(",
        "def eval_report_output(",
        "def maybe_show_trace(",
        'mode="local"',
        "mode='local'",
        'engine="bedrock"',
    )
    for path in _notebooks():
        source = _source(_load(path))
        assert not any(needle in source for needle in forbidden), path.name
        assert "toolkit.human_result" in source or "toolkit.show" in source, path.name


def test_every_notebook_states_model_evidence_and_evidence_limit():
    markers = (
        "**Lugar en el modelo:**",
        "**Evidencia exigida:**",
        "**L\u00edmite de la evidencia:**",
    )
    for path in _notebooks():
        first_markdown = "".join(_load(path)["cells"][0].get("source", []))
        for marker in markers:
            assert marker in first_markdown, (_relative(path), marker)


def test_reviewed_narrative_freezes_the_2_0_conceptual_boundaries():
    requirements = {
        "providers/00_auto.ipynb": (
            "provider_priority",
            "OpenAI y Bedrock",
            "configured",
            "passed",
        ),
        "core/01_tool.ipynb": ("ToolSet", "caja completa", "colecci"),
        "core/02_skills.ipynb": (
            "Anthropic/Claude",
            "ChatGPT/OpenAI",
            "no se considera intercambiable",
        ),
        "core/03_agent.ipynb": (
            "pipeline propio",
            "System m",
            "ownership/registry",
        ),
        "core/04_results_lineage.ipynb": (
            "mismo esquema e invariantes",
            "native_result",
            "pueden variar",
        ),
        "core/05_system.ipynb": (
            "plan de ejecuci",
            "ToolSet",
            "algebra composicional",
        ),
        "core/07_environment_eval.ipynb": (
            "Environment a",
            "Agent como un System",
            "correcci",
        ),
        "frameworks/03_provider_framework_matrix.ipynb": (
            "declared",
            "not-run",
            "passed",
        ),
    }
    for relative, fragments in requirements.items():
        source = _source(_load(TUTORIALS / relative))
        normalized = (
            source.replace("\u00f1", "n")
            .replace("\u00e1", "a")
            .replace("\u00e9", "e")
            .replace("\u00ed", "i")
            .replace("\u00f3", "o")
            .replace("\u00fa", "u")
        )
        for fragment in fragments:
            assert fragment in normalized, (relative, fragment)


def test_reported_notebook_claims_are_enforced_by_executable_assertions():
    requirements = {
        "providers/01_openai.ipynb": (
            "assert result.ok",
            'assert result.engine == "openai-runtime"',
        ),
        "providers/02_bedrock.ipynb": (
            "assert result.ok",
            'assert result.engine == "bedrock-runtime"',
        ),
        "providers/03_vllm.ipynb": (
            "assert result.ok",
            'assert result.engine == "vllm-runtime"',
        ),
        "providers/04_ollama.ipynb": (
            "assert result.ok",
            'assert result.engine == "ollama-runtime"',
        ),
        "core/00_runtime_scheduler.ipynb": (
            'assert retry_result.usage["scheduler"]["retries"] == 1',
            'assert timeout_result.usage["scheduler"]["timed_out"] is True',
        ),
        "core/03_agent.ipynb": (
            "agent.pipeline(",
            "assert pipeline_inspection ==",
        ),
        "core/05_system.ipynb": (
            "system.compile(",
            "system.run(",
            "assert len(system_result.children) == 1",
        ),
        "core/07_environment_eval.ipynb": (
            "toolkit.eval().run(\n    agent,",
            "toolkit.eval().run(\n    system,",
            "assert agent_report.ok and system_report.ok",
        ),
        "core/09_multi_agentic_system.ipynb": (
            "toolkit.SequentialPlan(",
            "system.run(",
            "assert len(result.children) == 2",
        ),
        "frameworks/03_provider_framework_matrix.ipynb": (
            "assert len(matrix_cases) == len(matrix_results) == 20",
            "assert not failed_rows",
            'status_counts["passed"] == len(matrix_results)',
        ),
    }
    for relative, fragments in requirements.items():
        code = _code(_load(TUTORIALS / relative))
        for fragment in fragments:
            assert fragment in code, (relative, fragment)


def test_live_notebooks_are_run_all_ready_by_default():
    live_flags = {
        "providers/01_openai.ipynb": "RUN_OPENAI_LIVE",
        "providers/03_vllm.ipynb": "RUN_VLLM_LIVE",
        "providers/02_bedrock.ipynb": "RUN_BEDROCK_LIVE",
        "frameworks/00_langgraph.ipynb": "RUN_LANGGRAPH_LIVE",
        "providers/04_ollama.ipynb": "RUN_OLLAMA_LIVE",
        "frameworks/02_aws_strands.ipynb": "RUN_STRANDS_LIVE",
        "frameworks/01_openai_agents.ipynb": "RUN_OPENAI_AGENTS_LIVE",
    }
    for name, flag in live_flags.items():
        notebook = _load(TUTORIALS / name)
        source = _source(notebook)
        code = _code(notebook)
        default = "0" if name.startswith("frameworks/") else "1"
        assert f'os.getenv("{flag}", "{default}")' in code, name
        if default == "1":
            assert f"{flag}=0" in source, name

    vllm = _code(_load(TUTORIALS / "providers/03_vllm.ipynb"))
    assert "toolkit.model_artifact(" in vllm
    assert "toolkit.model_server(" in vllm
    assert "server.start()" in vllm
    assert "server.runtime(" in vllm

    bedrock = _code(_load(TUTORIALS / "providers/02_bedrock.ipynb"))
    ollama = _code(_load(TUTORIALS / "providers/04_ollama.ipynb"))
    assert "toolkit.ollama_environment_snapshot()" in ollama
    assert 'os.getenv("OLLAMA_MODEL")' in ollama

    assert 'aws_session.get("has_credentials")' in bedrock
    assert "AWS_BEARER_TOKEN_BEDROCK" in bedrock

    for name in (
        "frameworks/02_aws_strands.ipynb",
        "frameworks/01_openai_agents.ipynb",
    ):
        source = _code(_load(TUTORIALS / name))
        assert 'else toolkit.runtime(provider="python-runtime")' in source
    run_all_docs = (
        ROOT / "README.md",
        ROOT / "docs" / "API.md",
        ROOT / "docs" / "ONBOARDING_FIRST_RUN.md",
        ROOT / "tutorials" / "README.md",
    )
    for path in run_all_docs:
        text = path.read_text(encoding="utf-8")
        assert "Run All" in text, path
        assert "RUN_*_LIVE=0" in text, path

    api_docs = (ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    tutorial_docs = (ROOT / "tutorials" / "README.md").read_text(encoding="utf-8")
    assert "Converse and embeddings smoke" not in api_docs
    assert "optional LM explainer" not in api_docs
    assert "reviewer LM opcional" not in tutorial_docs


def test_framework_notebooks_bootstrap_optional_dependencies_safely():
    openai_agents = _code(_load(TUTORIALS / "frameworks/01_openai_agents.ipynb"))
    assert "OPENAI_AGENTS_DEPENDENCY" in openai_agents
    assert 'importlib.util.find_spec("agents")' in openai_agents
    assert "toolkit.dependency_target(" in openai_agents
    assert '"openai-agents>=0.18.3,<0.19"' not in openai_agents
    assert "importlib.invalidate_caches()" in openai_agents

    strands = _code(_load(TUTORIALS / "frameworks/02_aws_strands.ipynb"))
    assert "def record_after_invocation(event: AfterInvocationEvent)" in strands
