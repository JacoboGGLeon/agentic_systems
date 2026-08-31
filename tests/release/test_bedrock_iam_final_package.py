from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "generate_bedrock_iam_package.py"
PACKAGE_STEM = "agentic-systems-2.1.1-bedrock-iam-final"
WHEEL_NAME = "agentic_systems-2.1.1-py3-none-any.whl"


def test_final_bedrock_iam_kit_is_portable_and_env_driven(tmp_path: Path) -> None:
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
    expected_wheel_sha = hashlib.sha256(wheel.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert {
            ".env",
            "bedrock_iam_attestation.ipynb",
            WHEEL_NAME,
            "README.md",
            "run_live_matrix.py",
            "validate_live_attestation.py",
            "run_semantic_matrix.py",
            "semantic_e2e_application.py",
            "SHA256SUMS.txt",
            "studio/app.py",
            "studio/src/agentic_systems_studio/conversation.py",
            "studio/src/agentic_systems_studio/presentation.py",
            "studio/scripts/validate_conversation_live.py",
        } <= names
        dotenv = archive.read(".env").decode()
        assert f"AGENTIC_SYSTEMS_COMMIT_SHA={commit}" in dotenv
        assert f"AGENTIC_SYSTEMS_WHEEL_FILENAME={WHEEL_NAME}" in dotenv
        assert f"AGENTIC_SYSTEMS_WHEEL_SHA256={expected_wheel_sha}" in dotenv
        assert f"AGENTIC_SYSTEMS_WHEEL={WHEEL_NAME}" in dotenv
        assert "AGENTIC_SYSTEMS_PROVIDER=bedrock-runtime" in dotenv
        assert "AGENTIC_SYSTEMS_PROVIDER_PRIORITY=bedrock-runtime" in dotenv
        assert "AWS_BEARER_TOKEN_BEDROCK=" in dotenv.splitlines()
        assert "RUN_SEMANTIC_MATRIX_LIVE=1" in dotenv

        notebook = json.loads(archive.read("bedrock_iam_attestation.ipynb"))
        notebook_text = json.dumps(notebook)
        assert "bedrock-studio-live-gate" in notebook_text
        assert "bedrock-studio-live.json" in notebook_text

        studio_app = archive.read("studio/app.py").decode()
        assert "processing_mark(result)" in studio_app
        assert "usage_mark(result)" in studio_app
        code = "\n".join(
            "".join(cell.get("source", ""))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        )
        assert commit not in code
        assert expected_wheel_sha not in code
        assert "https://github.com" not in code
        assert 'Path.cwd() / "run_live_matrix.py"' in code
        assert 'Path.cwd() / "run_semantic_matrix.py"' in code
        assert 'Path.cwd() / "semantic_e2e_application.py"' in code
        assert '"episodes_total": 16' in code
        assert 'authentication["authentication_mode"] == "aws-credential-chain"' in code
        metadata = notebook["metadata"]["agentic_systems"]["portable_package"]
        assert metadata["commit_sha"] == commit
        assert metadata["wheel_sha256"] == expected_wheel_sha
        assert metadata["semantic_episodes"] == 16

        checksum_lines = archive.read("SHA256SUMS.txt").decode().splitlines()
        assert not any(line.endswith("  .env") for line in checksum_lines)
        for line in checksum_lines:
            expected, filename = line.split("  ", 1)
            assert hashlib.sha256(archive.read(filename)).hexdigest() == expected

        combined = "\n".join(
            archive.read(name).decode(errors="ignore")
            for name in names
            if not name.endswith(".whl")
        )
        assert "sk-proj-" not in combined
        assert "AWS_SECRET_ACCESS_KEY=" not in combined
