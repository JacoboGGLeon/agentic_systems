from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

from agentic_systems.registry import FRAMEWORK_NAMES, PROVIDERS, provider_capability


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_bundle_builder():
    path = PROJECT_ROOT / "scripts" / "build_bundle.py"
    spec = importlib.util.spec_from_file_location("studio_bundle_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_notebooks_are_the_same_conversational_system_with_and_without_ui():
    notebooks = sorted((PROJECT_ROOT / "notebooks").glob("*.ipynb"))
    assert [path.name for path in notebooks] == [
        "00_conversational_system.ipynb",
        "01_launch_studio.ipynb",
    ]
    direct = json.loads(notebooks[0].read_text(encoding="utf-8"))
    launch = json.loads(notebooks[1].read_text(encoding="utf-8"))
    direct_code = "\n".join(
        "".join(cell["source"])
        for cell in direct["cells"]
        if cell["cell_type"] == "code"
    )
    launch_code = "\n".join(
        "".join(cell["source"])
        for cell in launch["cells"]
        if cell["cell_type"] == "code"
    )
    assert "build_conversational_system(" in direct_code
    assert "safe_calculate.run(" in direct_code
    assert "environment_path = load_studio_environment()" in direct_code
    assert direct_code.index("load_studio_environment()") < direct_code.index(
        "RUN_STUDIO_LIVE ="
    )
    assert "start_studio_server(" in launch_code
    assert "environment_path = load_studio_environment()" in launch_code
    assert launch_code.index("load_studio_environment()") < launch_code.index("PORT =")
    assert "studio_proxy_url(" in launch_code
    assert direct["metadata"]["agentic_systems"]["configuration"] == ".env"
    assert launch["metadata"]["agentic_systems"]["configuration"] == ".env"
    assert "cli_equivalent" not in direct["metadata"]["agentic_systems"]
    assert "cli_equivalent" not in launch["metadata"]["agentic_systems"]


def test_streamlit_is_conversational_and_env_configured():
    source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    assert "st.chat_input(" in source
    assert "st.chat_message(" in source
    assert "ConversationConfig.from_environment()" in source
    assert "build_conversational_system(" in source
    assert "configured_provider_names()" in source
    assert source.count("st.selectbox(") == 2
    assert "create_application(" not in source
    assert "SYSTEM_SPECS" not in source


def test_studio_metadata_and_grounding_match_release_2_1():
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    conversation = (
        PROJECT_ROOT / "src/agentic_systems_studio/conversation.py"
    ).read_text(encoding="utf-8")

    assert 'version = "2.1.0"' in pyproject
    assert "inspect_agentic_systems_grammar" in conversation
    assert 'name="agentic-systems-grammar"' in conversation
    assert "skills=[] if mock else [grammar_skill]" in conversation


def test_bundle_is_reproducible_conversational_delivery(tmp_path: Path):
    module = _load_bundle_builder()
    first = module.build_bundle(tmp_path / "first")
    second = module.build_bundle(tmp_path / "second")
    assert first.read_bytes() == second.read_bytes()
    assert first.name == "agentic-systems-studio-2.1.0.zip"

    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["schema_version"] == "agentic-systems.studio-bundle/v2"
        assert manifest["application"] == "conversational-studio"
        assert manifest["configuration_source"] == ".env"
        assert manifest["credentials_included"] is False
        assert manifest["normalized_result"] == "RunResult"
        assert manifest["providers"] == [
            "auto",
            *(
                item.name
                for item in PROVIDERS
                if provider_capability(item.name, "model_generation").status
                != "unsupported"
            ),
        ]
        assert manifest["frameworks"] == list(FRAMEWORK_NAMES)
        assert "notebooks/00_conversational_system.ipynb" in names
        assert "notebooks/01_launch_studio.ipynb" in names
        assert "src/agentic_systems_studio/conversation.py" in names
        assert "SHA256SUMS" in names
        assert not any(name.startswith("system-bundles/") for name in names)
        assert not any(".codex-backup" in name for name in names)
