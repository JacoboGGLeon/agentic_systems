from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "generate_ada_iam_validation_package.py"
PACKAGE_STEM = "agentic-systems-2.1.2-bedrock-iam-ada-validation"
WHEEL_NAME = "agentic_systems-2.1.2-py3-none-any.whl"


def test_ada_iam_validation_kit_is_offline_first_and_semantic(tmp_path: Path) -> None:
    wheel = tmp_path / WHEEL_NAME
    wheel.write_bytes(b"certified-wheel")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
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

    expected_wheel_sha = hashlib.sha256(wheel.read_bytes()).hexdigest()
    archive_path = tmp_path / f"{PACKAGE_STEM}.zip"
    with zipfile.ZipFile(archive_path) as archive:
        prefix = f"{PACKAGE_STEM}/"
        names = set(archive.namelist())
        assert not any(
            "__pycache__" in name or name.endswith((".pyc", ".pyo")) for name in names
        )
        required = {
            ".env.example",
            "README.md",
            "manifest.json",
            "requirements-ada.txt",
            "verify_bundle.py",
            "SHA256SUMS.txt",
            "bedrock_iam_attestation.ipynb",
            f"artifacts/{WHEEL_NAME}",
            "validation/run_ada_semantic_matrix.py",
            "validation/run_semantic_matrix.py",
            "validation/semantic_e2e_application.py",
            "studio/app.py",
            "studio/pyproject.toml",
            "studio/notebooks/00_conversational_system.ipynb",
            "studio/notebooks/01_launch_studio.ipynb",
            "studio/src/agentic_systems_studio/conversation.py",
            "studio/scripts/validate_conversation_live.py",
        }
        assert {prefix + name for name in required} <= names

        assert prefix + ".env" not in names
        dotenv = archive.read(prefix + ".env.example").decode()
        assert f"AGENTIC_SYSTEMS_COMMIT_SHA={commit}" in dotenv
        assert f"AGENTIC_SYSTEMS_WHEEL_SHA256={expected_wheel_sha}" in dotenv
        assert f"AGENTIC_SYSTEMS_WHEEL=artifacts/{WHEEL_NAME}" in dotenv
        assert "AGENTIC_SYSTEMS_PROVIDER=bedrock-runtime" in dotenv
        assert "AWS_BEARER_TOKEN_BEDROCK=" in dotenv.splitlines()
        assert "AWS_STS_IDENTITY_REQUIRED=1" in dotenv
        assert "RUN_SEMANTIC_MATRIX_LIVE=1" in dotenv

        manifest = json.loads(archive.read(prefix + "manifest.json"))
        assert manifest["credentials_included"] is False
        assert manifest["configuration_source"] == ".env"
        assert manifest["configuration_template"] == ".env.example"
        assert manifest["mutable_configuration_excluded_from_checksums"] is True
        assert manifest["authentication_required"] == "aws-credential-chain"
        assert manifest["semantic_episodes"] == 16
        assert manifest["studio"] == "one-conversational-agentic-system"
        assert manifest["wheel"]["sha256"] == expected_wheel_sha
        assert manifest["provenance"]["core_source_equivalent"] is True

        notebook = json.loads(archive.read(prefix + "bedrock_iam_attestation.ipynb"))
        code = "\n".join(
            "".join(cell.get("source", ""))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        )
        assert 'Path.cwd() / "run_semantic_matrix.py"' in code
        assert 'authentication["authentication_mode"] == "aws-credential-chain"' in code
        assert "from agentic_systems.utils import mask_sensitive" in code
        assert "toolkit.mask_sensitive" not in code
        assert 'f"{studio_root}[ui,notebook]"' in code
        assert "bedrock-studio-live-gate" in json.dumps(notebook)

        requirements = archive.read(prefix + "requirements-ada.txt").decode()
        assert "streamlit>=1.37" in requirements
        assert "jupyter-server-proxy>=4.4" in requirements

        checksum_lines = archive.read(prefix + "SHA256SUMS.txt").decode().splitlines()
        assert not any(line.endswith("  .env") for line in checksum_lines)
        for line in checksum_lines:
            expected, filename = line.split("  ", 1)
            assert (
                hashlib.sha256(archive.read(prefix + filename)).hexdigest() == expected
            )

        combined = "\n".join(
            archive.read(name).decode(errors="ignore")
            for name in names
            if not name.endswith(".whl")
        )
        assert "sk-proj-" not in combined
        assert "AWS_SECRET_ACCESS_KEY=" not in combined
