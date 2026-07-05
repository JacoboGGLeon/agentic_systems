import ast
import json
from pathlib import Path


def _tutorials():
    repo_root = Path(__file__).resolve().parents[1]
    notebook_dirs = [repo_root / "tutorials"]
    paths = []
    for tutorial_dir in notebook_dirs:
        assert tutorial_dir.exists()
        paths.extend(tutorial_dir.glob("**/*.ipynb"))
    return sorted(paths)


def test_tutorial_code_cells_parse():
    for tutorial_path in _tutorials():
        nb = json.loads(tutorial_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(nb.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            try:
                ast.parse(source)
            except SyntaxError as exc:  # pragma: no cover - failure path is the assertion payload
                raise AssertionError(
                    f"{tutorial_path.name} cell {index} has invalid Python syntax: {exc}"
                ) from exc


def test_mvp_tutorial_set_is_progressive_fundamentals_tools_skills():
    repo_root = Path(__file__).resolve().parents[1]
    tutorials = repo_root

    expected = {
        "tutorials/00_runtime_api.ipynb",
        "tutorials/00_runtime_bedrock_provider_api.ipynb",
        "tutorials/00_runtime_openai_provider_api.ipynb",
        "tutorials/00_runtime_scheduler_api.ipynb",
        "tutorials/01_tool_api.ipynb",
        "tutorials/02_skill_api.ipynb",
        "tutorials/03_agent_api.ipynb",
        "tutorials/04_human_result_api.ipynb",
        "tutorials/05_lineage_memory_api.ipynb",
        "tutorials/06_integrations_strands_api.ipynb",
        "tutorials/07_integrations_openai_runtime_api.ipynb",
        "tutorials/08_system_api.ipynb",
        "tutorials/09_graph_api.ipynb",
        "tutorials/10_environment_eval_api.ipynb",
        "tutorials/11_multi_agentic_system_api.ipynb",
        "tutorials/12_multi_agentic_graph_api.ipynb",
        "tutorials/13_single_agentic_system_api.ipynb",
        "tutorials/14_multi_agentic_system_api.ipynb",
    }
    actual = {path.relative_to(tutorials).as_posix() for path in _tutorials()}
    assert actual == expected
    assert not (tutorials / "roadmap").exists()
    
    for tutorial_path in _tutorials():
        text = tutorial_path.read_text(encoding="utf-8")
        assert "agentic_systems" in text
        assert "toolkit.human_" in text or "toolkit.show" in text or "lab.human_" in text or "print_human_" in text or "lab.show" in text
        assert "system." + "_adapter" not in text
        assert "ada_" + "bedrock_" + "adapter" not in text
        assert "Controlled" + "BedrockRuntime" not in text
        assert "attach_" + "controlled_runtime" not in text
