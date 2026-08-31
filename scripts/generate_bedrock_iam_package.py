"""Build a portable Bedrock IAM attestation kit for SageMaker and ADA."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import textwrap
import zipfile
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "release" / "notebooks" / "bedrock_iam_attestation.ipynb"
RUNNER = ROOT / "scripts" / "run_live_matrix.py"
VALIDATOR = ROOT / "scripts" / "validate_live_attestation.py"
SEMANTIC_RUNNER = ROOT / "scripts" / "run_semantic_matrix.py"
SEMANTIC_APPLICATION = ROOT / "scripts" / "semantic_e2e_application.py"
STUDIO = ROOT / "examples" / "agentic_systems_studio"
STUDIO_EXPORTS = (
    "README.md",
    "pyproject.toml",
    "app.py",
    ".env.example",
    "src",
    "notebooks",
    "docs",
    "scripts/validate_conversation_live.py",
)
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
        RUN_SEMANTIC_MATRIX_LIVE=1
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
        4. Conserva `bedrock-attestation.json`,
           `bedrock-iam-semantic-attestation.json` y
           `bedrock-iam-semantic-review.md` cuando ambos gates pasen. La última
           celda ejecuta el mismo Studio conversacional validado localmente y
           genera `bedrock-studio-live.json` con respuestas, Tools, usage y linaje.

        El kit no clona GitHub ni contiene credenciales. Pip utiliza la
        configuración del entorno; en ADA puede resolver dependencias desde
        Artifactory.

        - Commit: `{commit}`
        - Wheel: `{wheel.name}`
        - SHA256: `{wheel_sha256}`
        """
    )


def _semantic_cell() -> nbformat.NotebookNode:
    source = '''if RUN_BEDROCK_LIVE:
    semantic_runner = Path.cwd() / "run_semantic_matrix.py"
    semantic_application = Path.cwd() / "semantic_e2e_application.py"
    missing = [
        str(path)
        for path in (semantic_runner, semantic_application)
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError({"missing_semantic_gate_files": missing})

    SEMANTIC_OUTPUT = Path.cwd() / "bedrock-iam-semantic-attestation.json"
    SEMANTIC_REVIEW = Path.cwd() / "bedrock-iam-semantic-review.md"
    semantic_run = subprocess.run([
        sys.executable,
        str(semantic_runner),
        "--wheel", str(WHEEL_PATH),
        "--output", str(SEMANTIC_OUTPUT),
        "--review", str(SEMANTIC_REVIEW),
        "--commit", COMMIT_SHA,
        "--env", str(DOTENV_PATH),
        "--providers", "bedrock-runtime",
        "--frameworks", "native", "langgraph", "openai-agents", "strands",
    ], text=True, capture_output=True)
    toolkit.show_json({
        "returncode": semantic_run.returncode,
        "stdout": semantic_run.stdout,
        "stderr": semantic_run.stderr,
    }, title="Bedrock IAM semantic matrix")
    if semantic_run.returncode:
        raise RuntimeError(
            f"La matriz semántica IAM falló con código {semantic_run.returncode}"
        )

    semantic_attestation = json.loads(
        SEMANTIC_OUTPUT.read_text(encoding="utf-8")
    )
    semantic_summary = semantic_attestation["summary"]
    authentication = semantic_attestation["environment"]["providers"][
        "bedrock-runtime"
    ]["authentication"]
    assert semantic_attestation["wheel_sha256"] == EXPECTED_WHEEL_SHA256
    assert semantic_attestation["commit_sha"] == COMMIT_SHA
    assert authentication["authentication_mode"] == "aws-credential-chain"
    assert authentication["has_credentials"] is True
    assert authentication["bedrock_api_key_configured"] is False
    assert semantic_summary == {
        "total": 4,
        "passed": 4,
        "failed": 0,
        "episodes_total": 16,
        "episodes_passed": 16,
        "episodes_failed": 0,
    }
    for matrix_cell in semantic_attestation["cells"]:
        assert matrix_cell["provider"] == "bedrock-runtime"
        assert matrix_cell["ok"]
        for episode in matrix_cell["episodes"]:
            assert episode["ok"]
            assert episode["semantic_review"]["ok"]
            assert episode["deterministic_validation"]["ok"]
            assert episode["judge"]["ok"]
            answer = episode["candidate"]["answer"]["text"].lstrip()
            assert not answer.startswith(("{", "[")), answer

    from IPython.display import FileLink, display

    toolkit.show_json(semantic_summary, title="Bedrock IAM semantic summary")
    display(FileLink(str(SEMANTIC_OUTPUT)))
    display(FileLink(str(SEMANTIC_REVIEW)))
else:
    toolkit.show_json(
        {"status": "not-run", "scope": "bedrock-iam-semantic-attestation"},
        title="Semantic attestation gate",
    )'''
    cell = nbformat.v4.new_code_cell(source)
    cell["id"] = "bedrock-iam-semantic-gate"
    cell.metadata["tags"] = ["semantic-attestation", "iam-contract"]
    return cell


def _studio_cell() -> nbformat.NotebookNode:
    source = '''if RUN_BEDROCK_LIVE:
    studio_root = Path.cwd() / "studio"
    studio_gate = studio_root / "scripts" / "validate_conversation_live.py"
    if not studio_gate.is_file():
        raise FileNotFoundError(studio_gate)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "-e", str(studio_root)],
        check=True,
    )
    STUDIO_OUTPUT = Path.cwd() / "bedrock-studio-live.json"
    studio_run = subprocess.run(
        [
            sys.executable,
            str(studio_gate),
            "--providers",
            "bedrock-runtime",
            "--output",
            str(STUDIO_OUTPUT),
            "--quiet",
        ],
        text=True,
        capture_output=True,
    )
    toolkit.show_json(
        {
            "returncode": studio_run.returncode,
            "stdout": studio_run.stdout,
            "stderr": studio_run.stderr,
        },
        title="Bedrock Studio live gate",
    )
    if studio_run.returncode:
        raise RuntimeError("Bedrock Studio live gate failed")
    studio_report = json.loads(STUDIO_OUTPUT.read_text(encoding="utf-8"))
    assert studio_report["ok"] is True
    from IPython.display import FileLink, display

    display(FileLink(str(STUDIO_OUTPUT)))
else:
    toolkit.show_json(
        {"status": "not-run", "scope": "bedrock-studio-live"},
        title="Bedrock Studio live gate",
    )'''
    cell = nbformat.v4.new_code_cell(source)
    cell["id"] = "bedrock-studio-live-gate"
    cell.metadata["tags"] = ["studio", "live-semantic-gate", "iam-contract"]
    return cell


def _packaged_notebook(
    *, commit: str, wheel: Path, wheel_sha256: str
) -> nbformat.NotebookNode:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    notebook.cells.append(_semantic_cell())
    notebook.cells.append(_studio_cell())
    notebook.metadata.setdefault("agentic_systems", {})["portable_package"] = {
        "commit_sha": commit,
        "wheel_filename": wheel.name,
        "wheel_sha256": wheel_sha256,
        "authentication": "aws-credential-chain",
        "semantic_episodes": 16,
    }
    return notebook


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
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wheel, package_dir / wheel.name)
    nbformat.write(
        _packaged_notebook(
            commit=commit, wheel=wheel, wheel_sha256=wheel_sha256
        ),
        package_dir / "bedrock_iam_attestation.ipynb",
    )
    shutil.copy2(RUNNER, package_dir / RUNNER.name)
    shutil.copy2(VALIDATOR, package_dir / VALIDATOR.name)
    shutil.copy2(SEMANTIC_RUNNER, package_dir / SEMANTIC_RUNNER.name)
    shutil.copy2(SEMANTIC_APPLICATION, package_dir / SEMANTIC_APPLICATION.name)
    for relative in STUDIO_EXPORTS:
        source = STUDIO / relative
        target = package_dir / "studio" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
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
        SEMANTIC_RUNNER.name,
        SEMANTIC_APPLICATION.name,
        *(
            path.relative_to(package_dir).as_posix()
            for path in sorted(
                item for item in (package_dir / "studio").rglob("*") if item.is_file()
            )
        ),
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
