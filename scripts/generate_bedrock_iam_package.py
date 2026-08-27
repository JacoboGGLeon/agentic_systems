"""Build a portable Bedrock IAM attestation kit for SageMaker and ADA."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import textwrap
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "release" / "notebooks" / "bedrock_iam_attestation.ipynb"
RUNNER = ROOT / "scripts" / "run_live_matrix.py"
VALIDATOR = ROOT / "scripts" / "validate_live_attestation.py"
DEFAULT_WHEEL = ROOT / "dist" / "agentic_systems-2.1.0-py3-none-any.whl"
DEFAULT_OUTPUT = ROOT / "dist"
PACKAGE_STEM = "agentic-systems-2.1.0-bedrock-iam-final"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _dotenv(*, commit: str, wheel: Path, wheel_sha256: str) -> str:
    return textwrap.dedent(
        f"""\
        AGENTIC_SYSTEMS_PROVIDER=bedrock-runtime
        AGENTIC_SYSTEMS_FRAMEWORK=native
        AGENTIC_SYSTEMS_PROVIDER_PRIORITY=bedrock-runtime
        AGENTIC_SYSTEMS_COMMIT_SHA={commit}
        AGENTIC_SYSTEMS_WHEEL={wheel.name}
        AGENTIC_SYSTEMS_WHEEL_FILENAME={wheel.name}
        AGENTIC_SYSTEMS_WHEEL_SHA256={wheel_sha256}

        AWS_BEARER_TOKEN_BEDROCK=
        AWS_REGION=us-east-2
        AWS_DEFAULT_REGION=us-east-2
        BEDROCK_MODEL_ID=us.amazon.nova-pro-v1:0
        BEDROCK_STREAMING=0
        RUN_BEDROCK_LIVE=1
        OPENAI_AGENTS_DISABLE_TRACING=1
        """
    )


def _readme(*, commit: str, wheel: Path, wheel_sha256: str) -> str:
    return textwrap.dedent(
        f"""\
        # Agentic Systems 2.1.0 · Bedrock IAM final kit

        1. Descomprime este ZIP en un directorio nuevo de SageMaker/ADA.
        2. Edita `.env`: conserva `AWS_BEARER_TOKEN_BEDROCK=` vacío para IAM y
           ajusta únicamente región/modelo cuando tu cuenta lo requiera.
        3. Abre `bedrock_iam_attestation.ipynb` y ejecuta **Run All**.
        4. Conserva `bedrock-attestation.json` cuando las cuatro celdas pasen.

        El kit no clona GitHub ni contiene credenciales. Pip utiliza la
        configuración del entorno; en ADA puede resolver dependencias desde
        Artifactory.

        - Commit: `{commit}`
        - Wheel: `{wheel.name}`
        - SHA256: `{wheel_sha256}`
        """
    )


def _write_archive(package_dir: Path, names: tuple[str, ...], output: Path) -> None:
    checksum_path = package_dir / "SHA256SUMS.txt"
    checksum_path.write_text(
        "".join(f"{_sha256(package_dir / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in (*names, checksum_path.name):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, (package_dir / name).read_bytes())


def build(*, wheel: Path, commit: str, output_dir: Path) -> Path:
    wheel = wheel.resolve()
    output_dir = output_dir.resolve()
    if not wheel.is_file():
        raise FileNotFoundError(wheel)
    if len(commit) != 40:
        raise ValueError("commit must be the full 40-character Git SHA")

    wheel_sha256 = _sha256(wheel)
    package_dir = output_dir / PACKAGE_STEM
    package_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wheel, package_dir / wheel.name)
    shutil.copy2(NOTEBOOK, package_dir / "bedrock_iam_attestation.ipynb")
    shutil.copy2(RUNNER, package_dir / RUNNER.name)
    shutil.copy2(VALIDATOR, package_dir / VALIDATOR.name)
    (package_dir / ".env").write_text(
        _dotenv(commit=commit, wheel=wheel, wheel_sha256=wheel_sha256),
        encoding="utf-8",
    )
    (package_dir / "README.md").write_text(
        _readme(commit=commit, wheel=wheel, wheel_sha256=wheel_sha256),
        encoding="utf-8",
    )

    names = (
        ".env",
        "bedrock_iam_attestation.ipynb",
        wheel.name,
        "README.md",
        RUNNER.name,
        VALIDATOR.name,
    )
    output = output_dir / f"{PACKAGE_STEM}.zip"
    _write_archive(package_dir, names, output)
    print(
        f"{output}\ncommit={commit}\nwheel={wheel.name}\n"
        f"wheel_sha256={wheel_sha256}\npackage_sha256={_sha256(output)}"
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, default=DEFAULT_WHEEL)
    parser.add_argument("--commit", default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(
        wheel=args.wheel,
        commit=args.commit or _git_commit(),
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
