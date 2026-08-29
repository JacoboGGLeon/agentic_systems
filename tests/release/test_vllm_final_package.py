from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "generate_vllm_colab_e2e_package.py"
PACKAGE_STEM = "agentic-systems-2.1.0-vllm-qwen06-colab-final"
WHEEL_NAME = "agentic_systems-2.1.0-py3-none-any.whl"


def test_final_vllm_kit_derives_identity_from_real_artifacts(tmp_path: Path) -> None:
    wheel = tmp_path / WHEEL_NAME
    wheel.write_bytes(b"certified-wheel")
    commit = "a" * 40
    subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--wheel",
            str(wheel),
            "--commit",
            commit,
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
        assert names == {
            ".env",
            "03_vllm_qwen06_colab_final.ipynb",
            WHEEL_NAME,
            "README.md",
            "run_semantic_matrix.py",
            "semantic_e2e_application.py",
            "SHA256SUMS.txt",
        }
        dotenv = archive.read(".env").decode()
        assert f"AGENTIC_SYSTEMS_COMMIT_SHA={commit}" in dotenv
        assert f"AGENTIC_SYSTEMS_WHEEL_FILENAME={WHEEL_NAME}" in dotenv
        assert f"AGENTIC_SYSTEMS_WHEEL_SHA256={expected_wheel_sha}" in dotenv
        assert f"AGENTIC_SYSTEMS_WHEEL=/content/{WHEEL_NAME}" in dotenv
        assert "AGENTIC_SYSTEMS_PROVIDER_PRIORITY=vllm-runtime" in dotenv

        notebook = json.loads(archive.read("03_vllm_qwen06_colab_final.ipynb"))
        metadata = notebook["metadata"]["agentic_systems"]["portable_package"]
        assert metadata["commit_sha"] == commit
        assert metadata["wheel_sha256"] == expected_wheel_sha
        assert metadata["model"] == "unsloth/Qwen3-0.6B"

        runner = archive.read("run_semantic_matrix.py").decode()
        application = archive.read("semantic_e2e_application.py").decode()
        assert '"schema_version": "agentic_systems.semantic-attestation.v1"' in runner
        assert "human_result exposes structured technical JSON" in runner
        assert "PROVIDERS = PROVIDER_NAMES" in application
        assert "record_semantic_judgment" in application
        assert 'tool_choice="record_semantic_judgment"' in application
        assert '"poetic_calculation"' in application

        for line in archive.read("SHA256SUMS.txt").decode().splitlines():
            expected, filename = line.split("  ", 1)
            assert hashlib.sha256(archive.read(filename)).hexdigest() == expected

        combined_text = "\n".join(
            archive.read(name).decode(errors="ignore")
            for name in names
            if not name.endswith(".whl")
        )
        assert "sk-proj-" not in combined_text
        assert "AWS_SECRET_ACCESS_KEY=" not in combined_text
