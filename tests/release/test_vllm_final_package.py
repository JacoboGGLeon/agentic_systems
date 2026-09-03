from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "generate_vllm_colab_e2e_package.py"
PACKAGE_STEM = "agentic-systems-2.1.1-vllm-qwen4b-colab-final"
WHEEL_NAME = "agentic_systems-2.1.1-py3-none-any.whl"


def test_final_vllm_kit_derives_identity_from_real_artifacts(tmp_path: Path) -> None:
    wheel = tmp_path / WHEEL_NAME
    wheel.write_bytes(b"certified-wheel")
    commit = "a" * 40
    application_commit = "b" * 40
    subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--wheel",
            str(wheel),
            "--commit",
            commit,
            "--application-commit",
            application_commit,
            "--output-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    archive_path = tmp_path / f"{PACKAGE_STEM}.zip"
    assert archive_path.is_file()
    expected_wheel_sha = hashlib.sha256(wheel.read_bytes()).hexdigest()

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert {
            ".env",
            "03_vllm_qwen4b_colab_final.ipynb",
            "04_vllm_qwen4b_colab_studio.ipynb",
            WHEEL_NAME,
            "README.md",
            "run_semantic_matrix.py",
            "semantic_e2e_application.py",
            "SHA256SUMS.txt",
            "studio/app.py",
            "studio/src/agentic_systems_studio/conversation.py",
            "studio/src/agentic_systems_studio/presentation.py",
            "studio/src/agentic_systems_studio/notebook.py",
            "studio/scripts/validate_conversation_live.py",
        } <= names
        dotenv = archive.read(".env").decode()
        assert f"AGENTIC_SYSTEMS_COMMIT_SHA={commit}" in dotenv
        assert f"AGENTIC_SYSTEMS_APPLICATION_COMMIT_SHA={application_commit}" in dotenv
        assert f"AGENTIC_SYSTEMS_WHEEL_FILENAME={WHEEL_NAME}" in dotenv
        assert f"AGENTIC_SYSTEMS_WHEEL_SHA256={expected_wheel_sha}" in dotenv
        assert f"AGENTIC_SYSTEMS_WHEEL=/content/{WHEEL_NAME}" in dotenv
        assert "AGENTIC_SYSTEMS_PROVIDER_PRIORITY=vllm-runtime" in dotenv
        assert "AGENTIC_SYSTEMS_PROVIDER=vllm-runtime" in dotenv
        assert "VLLM_MODEL=unsloth/Qwen3-4B-Instruct-2507" in dotenv
        assert "VLLM_BASE_MODEL=Qwen/Qwen3-4B-Instruct-2507" in dotenv
        assert "VLLM_PROFILE=custom" in dotenv
        assert "VLLM_GPU_MEMORY_UTILIZATION=0.75" in dotenv
        assert "VLLM_MAX_NUM_SEQS=2" in dotenv
        assert "AGENTIC_SYSTEMS_STUDIO_PRESENTATION=streamlit" in dotenv
        assert "AGENTIC_SYSTEMS_STUDIO_TRANSPORT=colab-proxy" in dotenv
        assert "AGENTIC_SYSTEMS_STUDIO_PORT=8501" in dotenv

        notebook = json.loads(archive.read("03_vllm_qwen4b_colab_final.ipynb"))
        metadata = notebook["metadata"]["agentic_systems"]["portable_package"]
        assert metadata["commit_sha"] == commit
        assert metadata["application_commit_sha"] == application_commit
        assert metadata["wheel_sha256"] == expected_wheel_sha
        assert metadata["model"] == "unsloth/Qwen3-4B-Instruct-2507"
        assert metadata["base_model"] == "Qwen/Qwen3-4B-Instruct-2507"
        notebook_text = json.dumps(notebook)
        assert "unsloth/Qwen3-4B-Instruct-2507" in notebook_text
        assert "Qwen/Qwen3-4B-Instruct-2507" in notebook_text
        assert "Qwen3-0.6B" not in notebook_text
        assert "vllm-studio-live-gate" in notebook_text
        assert "vllm-studio-live.json" in notebook_text
        assert "vllm-studio-colab-launcher" in notebook_text
        assert "launch_studio" in notebook_text
        assert "AGENTIC_SYSTEMS_STUDIO_PRESENTATION" in notebook_text
        assert "AGENTIC_SYSTEMS_STUDIO_TRANSPORT" in notebook_text
        assert "display_notebook_studio" in notebook_text
        assert "notebook-native (explicit)" in notebook_text
        assert "streamlit>=1.37" in notebook_text
        studio_index = next(
            index
            for index, cell in enumerate(notebook["cells"])
            if cell.get("id") == "vllm-studio-live-gate"
        )
        launcher_index = next(
            index
            for index, cell in enumerate(notebook["cells"])
            if cell.get("id") == "vllm-studio-colab-launcher"
        )
        teardown_index = next(
            index
            for index, cell in enumerate(notebook["cells"])
            if "model-server-teardown" in cell.get("metadata", {}).get("tags", [])
        )
        assert studio_index < launcher_index < teardown_index
        launcher_source = "".join(notebook["cells"][launcher_index].get("source", ""))
        install_index = launcher_source.index('"pip", "install", "--no-deps", "-e"')
        path_index = launcher_source.index("sys.path.insert")
        import_index = launcher_source.index("from agentic_systems_studio import")
        assert install_index < path_index < import_index
        assert 'studio_root / "src"' in launcher_source
        teardown_source = "".join(notebook["cells"][teardown_index].get("source", ""))
        assert "def close_studio_and_model_server" in teardown_source
        assert "server.stop()" in teardown_source
        assert "Studio remains available until explicit closure." in teardown_source

        studio_notebook = json.loads(archive.read("04_vllm_qwen4b_colab_studio.ipynb"))
        studio_metadata = studio_notebook["metadata"]["agentic_systems"][
            "portable_package"
        ]
        assert studio_metadata["role"] == "studio-direct"
        assert studio_metadata["commit_sha"] == commit
        assert studio_metadata["application_commit_sha"] == application_commit
        studio_notebook_text = json.dumps(studio_notebook)
        assert "server.start()" in studio_notebook_text
        assert "launch_studio" in studio_notebook_text
        assert "close_studio_and_model_server" in studio_notebook_text
        assert "run_semantic_matrix.py" not in studio_notebook_text
        assert "semantic_e2e_application.py" not in studio_notebook_text
        assert "vllm-studio-live-gate" not in studio_notebook_text
        assert "record_semantic_judgment" not in studio_notebook_text
        direct_launcher_index = next(
            index
            for index, cell in enumerate(studio_notebook["cells"])
            if cell.get("id") == "vllm-studio-colab-launcher"
        )
        direct_teardown_index = next(
            index
            for index, cell in enumerate(studio_notebook["cells"])
            if "model-server-teardown" in cell.get("metadata", {}).get("tags", [])
        )
        assert direct_launcher_index < direct_teardown_index

        studio_app = archive.read("studio/app.py").decode()
        assert "processing_mark(result)" in studio_app
        assert "usage_mark(result)" in studio_app
        studio_server = archive.read(
            "studio/src/agentic_systems_studio/server.py"
        ).decode()
        assert "colab_output.eval_js" in studio_server
        assert "google.colab.kernel.proxyPort({port})" in studio_server
        assert "studio_button_html(" in studio_server
        assert "_display_html(" in studio_server
        assert 'trusted_proxy=selected_transport == "colab-proxy"' in studio_server
        assert '"--server.enableCORS"' in studio_server
        assert '"--server.enableXsrfProtection"' in studio_server
        assert '"--server.enableWebsocketCompression"' in studio_server
        assert "document.createElement" not in studio_server
        assert "accessAllowed" not in studio_server
        assert "serve_kernel_port_as_iframe" not in studio_server
        assert "def launch_studio(" in studio_server
        assert "Provider and framework selection never influence" in studio_server

        runner = archive.read("run_semantic_matrix.py").decode()
        application = archive.read("semantic_e2e_application.py").decode()
        assert '"schema_version": "agentic_systems.semantic-attestation.v1"' in runner
        assert "human_result exposes structured technical JSON" in runner
        assert "PROVIDERS = PROVIDER_NAMES" in application
        assert "record_semantic_judgment" in application
        assert 'tool_choice="record_semantic_judgment"' in application
        assert '"poetic_calculation"' in application

        checksum_lines = archive.read("SHA256SUMS.txt").decode().splitlines()
        assert not any(line.endswith("  .env") for line in checksum_lines)
        for line in checksum_lines:
            expected, filename = line.split("  ", 1)
            assert hashlib.sha256(archive.read(filename)).hexdigest() == expected

        combined_text = "\n".join(
            archive.read(name).decode(errors="ignore")
            for name in names
            if not name.endswith(".whl")
        )
        assert "sk-proj-" not in combined_text
        assert "AWS_SECRET_ACCESS_KEY=" not in combined_text
