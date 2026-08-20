from __future__ import annotations

from agentic_systems.utils import configure_notebook_environment


def test_notebook_helpers_are_public_and_honor_explicit_root(tmp_path):
    import agentic_systems as toolkit

    assert callable(configure_notebook_environment)
    assert callable(toolkit.show_json)
    assert configure_notebook_environment(tmp_path, add_src=False) == tmp_path.resolve()


def test_notebook_environment_and_markdown_prompt_contract(monkeypatch):
    import inspect
    import sys
    from pathlib import Path

    from agentic_systems.bedrock_runtime_client import BedrockRuntimeClient

    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setattr(
        sys,
        "path",
        [item for item in sys.path if item not in {str(repo_root), str(repo_root / "src")}],
    )
    configured = configure_notebook_environment(repo_root)
    assert configured == repo_root
    assert str(repo_root) in sys.path
    assert str(repo_root / "src") in sys.path

    source = inspect.getsource(BedrockRuntimeClient.answer_from_markdown)
    assert "No copies ni reimprimas el Markdown completo" in source
    assert "Devuelve sólo la respuesta final" in source
    assert "no reproduzcas el documento fuente" in source
