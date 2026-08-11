from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import agentic_systems as toolkit


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "tutorials"
EXPECTED_NOTEBOOKS = {
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
}
DIRECT_SDK_ROOTS = {"boto3", "openai", "subprocess", "requests", "urllib", "httpx"}
RUN_RESULT_FIELDS = {"final", "runtime", "usage", "validation"}


def _notebooks():
    return sorted(TUTORIALS.glob("*.ipynb"))


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
        if not any(isinstance(target, ast.Name) and target.id == "api_coverage" for target in targets):
            continue
        value = node.value
        assert isinstance(value, (ast.List, ast.Tuple)), "api_coverage must be a literal list or tuple."
        assert all(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in value.elts)
        values.append([item.value for item in value.elts])
    return values


def test_canonical_notebook_inventory_and_cell_integrity():
    paths = _notebooks()
    assert {path.name for path in paths} == EXPECTED_NOTEBOOKS
    for path in paths:
        notebook = _load(path)
        ids = [cell.get("id") for cell in notebook["cells"]]
        assert all(ids), path.name
        assert len(ids) == len(set(ids)), path.name
        assert all("".join(cell.get("source", [])).strip() for cell in notebook["cells"]), path.name
        first_markdown = next(cell for cell in notebook["cells"] if cell.get("cell_type") == "markdown")
        assert "Objetivo" in "".join(first_markdown.get("source", [])), path.name


def test_notebook_text_has_no_encoding_corruption_or_stale_constructor():
    broken = re.compile(r"\w\?\w|\ufffd")
    for path in _notebooks():
        source = _source(_load(path))
        assert not broken.search(source), path.name
        assert "toolkit.AgenticSystem(" not in source, path.name
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
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    assert not hasattr(toolkit, node.name), f"{path.name}:{index} shadows toolkit.{node.name}"


def test_canonical_notebooks_do_not_bypass_provider_or_output_boundaries():
    for path in _notebooks():
        tree = ast.parse(_code(_load(path)), filename=path.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
                assert not roots & DIRECT_SDK_ROOTS, (path.name, roots & DIRECT_SDK_ROOTS)
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                assert root not in DIRECT_SDK_ROOTS, (path.name, root)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "print", path.name
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Attribute):
                        assert target.attr not in RUN_RESULT_FIELDS, (path.name, target.attr)


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
        "00_runtime_openai_provider_api.ipynb",
        "00_runtime_vllm_provider_api.ipynb",
        "00_runtime_bedrock_provider_api.ipynb",
    ):
        source = _code(_load(TUTORIALS / name))
        route = ["toolkit.runtime(", "toolkit.system(", "system.agent(", "agent.run(", "toolkit.human_result("]
        positions = [source.index(item) for item in route]
        assert positions == sorted(positions), name
        assert "toolkit.run_result_output(" in source, name


def test_graph_notebooks_execute_only_through_toolkit_graph():
    for name in ("09_graph_api.ipynb", "13_multi_agentic_graph_api.ipynb"):
        source = _code(_load(TUTORIALS / name))
        assert "toolkit.graph(" in source
        assert "app.run(" in source
        assert "importlib" not in source


def test_api_claims_are_literal_public_and_materialized():
    for path in _notebooks():
        notebook = _load(path)
        source = _code(notebook)
        claim_groups = _api_claims(ast.parse(source, filename=path.name))
        assert len(claim_groups) == 1, path.name
        api_claims = claim_groups[0]
        assert api_claims, path.name
        for claim in api_claims:
            toolkit_match = re.match(r"toolkit\.([A-Za-z_]\w*)", claim)
            if toolkit_match:
                name = toolkit_match.group(1)
                assert hasattr(toolkit, name), f"{path.name} claims missing toolkit.{name}"
                assert f"toolkit.{name}" in source, f"{path.name} does not materialize {claim}"
                continue
            method_match = re.search(r"\.([A-Za-z_]\w*)", claim)
            assert method_match, f"{path.name} has uncheckable API claim {claim!r}"
            method = method_match.group(1)
            assert f".{method}" in source, f"{path.name} does not materialize {claim}"



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
        assert used <= public, f"{path.name} uses non-public names: {sorted(used - public)}"



def test_tutorial_repository_layout_and_assets_are_intentional():
    roots = sorted(
        path.name
        for path in TUTORIALS.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    )
    assert roots == ["notebooks", "skills"]
    assert not (TUTORIALS / "human_output.py").exists()
    assert not (TUTORIALS / "roadmap").exists()
    assert (TUTORIALS / "skills" / "accountability_otc").exists()


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


def test_live_notebooks_are_run_all_ready_by_default():
    live_flags = {
        "00_runtime_openai_provider_api.ipynb": "RUN_OPENAI_LIVE",
        "00_runtime_vllm_provider_api.ipynb": "RUN_VLLM_LIVE",
        "00_runtime_bedrock_provider_api.ipynb": "RUN_BEDROCK_LIVE",
        "06_integrations_strands_api.ipynb": "RUN_STRANDS_IDENTITY_LIVE",
        "07_integrations_openai_runtime_api.ipynb": "RUN_OPENAI_STYLE_LIVE",
    }
    for name, flag in live_flags.items():
        notebook = _load(TUTORIALS / name)
        source = _source(notebook)
        code = _code(notebook)
        assert f'os.getenv("{flag}", "1")' in code, name
        assert f"{flag}=0" in source, name

    vllm = _code(_load(TUTORIALS / "00_runtime_vllm_provider_api.ipynb"))
    assert 'vllm_environment.get("base_url_configured")' in vllm
    assert 'vllm_environment.get("model_configured")' in vllm

    bedrock = _code(_load(TUTORIALS / "00_runtime_bedrock_provider_api.ipynb"))
    assert 'aws_session.get("has_credentials")' in bedrock

    for name in (
        "06_integrations_strands_api.ipynb",
        "07_integrations_openai_runtime_api.ipynb",
    ):
        source = _code(_load(TUTORIALS / name))
        assert "resolved_provider" in source
        assert "resolved_provider != \"auto\"" in source
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