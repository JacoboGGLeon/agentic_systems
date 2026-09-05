"""Build an offline-first Bedrock IAM validation kit for ADA."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import textwrap
import zipfile
from pathlib import Path

import nbformat

from generate_bedrock_iam_package import _dotenv, _packaged_notebook


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WHEEL = ROOT / "dist" / "agentic_systems-2.1.2-py3-none-any.whl"
DEFAULT_OUTPUT = ROOT / "dist"
PACKAGE_STEM = "agentic-systems-2.1.2-bedrock-iam-ada-validation"
WHEEL_NAME = "agentic_systems-2.1.2-py3-none-any.whl"
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
VALIDATION_SCRIPTS = (
    "run_ada_semantic_matrix.py",
    "run_semantic_matrix.py",
    "semantic_e2e_application.py",
    "run_live_matrix.py",
    "validate_live_attestation.py",
)
SECRET_PATTERNS = (
    re.compile(rb"sk-proj-[A-Za-z0-9_-]+"),
    re.compile(rb"AWS_SECRET_ACCESS_KEY\s*=\s*[^\r\n]+"),
    re.compile(rb"AWS_SESSION_TOKEN\s*=\s*[^\r\n]+"),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _provenance(certified_commit: str) -> dict[str, object]:
    materials_commit = _git("rev-parse", "HEAD")
    certified_tree = _git("rev-parse", f"{certified_commit}:src/agentic_systems")
    materials_tree = _git("rev-parse", "HEAD:src/agentic_systems")
    core_dirty = subprocess.run(
        ["git", "diff", "--quiet", "--", "src/agentic_systems"], cwd=ROOT
    ).returncode
    if certified_tree != materials_tree or core_dirty:
        raise RuntimeError(
            "ADA validation materials do not match the certified core source tree"
        )
    return {
        "certified_commit": certified_commit,
        "materials_commit": materials_commit,
        "certified_core_tree": certified_tree,
        "materials_core_tree": materials_tree,
        "core_source_equivalent": True,
    }


def _requirements() -> str:
    return textwrap.dedent(
        """\
        # Resolve only through the approved ADA Artifactory.
        pydantic>=2.7.0
        typing-extensions>=4.10.0
        rich>=13.0.0
        boto3>=1.39.0
        botocore>=1.39.0
        langgraph>=0.2.0
        openai>=2.45.0,<3
        openai-agents>=0.18.3,<0.19
        strands-agents>=1.29.0,<2
        mcp>=1,<2
        ipython>=8.0
        ipykernel>=6.0
        nbformat>=5.10
        nbclient>=0.10
        nbconvert>=7.16
        jupyter-server-proxy>=4.4
        streamlit>=1.37
        """
    )


def _readme(*, commit: str, wheel_sha256: str) -> str:
    return textwrap.dedent(
        f"""\
        # Agentic Systems 2.1.2 · Bedrock IAM validation for ADA

        Este paquete no requiere GitHub ni PyPI. Usa exclusivamente el wheel
        incluido, el Artifactory aprobado para dependencias y el execution role
        de ADA para invocar Bedrock.

        1. Descomprime el ZIP y entra al directorio `{PACKAGE_STEM}`.
        2. Ejecuta `python verify_bundle.py`.
        3. Copia `.env.example` como `.env`; esa copia es configuración mutable y
           queda fuera de los checksums del artefacto:

               cp .env.example .env

           En PowerShell usa `Copy-Item .env.example .env`.
        4. Conserva `AWS_BEARER_TOKEN_BEDROCK=` vacío en `.env`; ajusta región o
           modelo únicamente si tu plataforma empresarial lo exige.
           Conserva `AWS_STS_IDENTITY_REQUIRED=1`: la certificación IAM sólo
           termina cuando `sts:GetCallerIdentity` devuelve identidad sanitizada.
        5. Instala dependencias mediante Artifactory:

               python -m pip install -r requirements-ada.txt

        6. Ejecuta la matriz E2E completa:

               python validation/run_ada_semantic_matrix.py

        7. Conserva los dos archivos creados en `outputs/`.
        8. Para probar el mismo sistema conversacional, instala el paquete local de
           Studio y ejecútalo desde la raíz del bundle:

               python -m pip install --no-deps -e "studio[ui,notebook]"
               python -m streamlit run studio/app.py

           `studio/notebooks/00_conversational_system.ipynb` ejecuta el contrato
           directamente y `01_launch_studio.ipynb` abre la UI por el proxy de
           JupyterLab. Ambos leen el único `.env` de la raíz.

        También puedes abrir `bedrock_iam_attestation.ipynb` y ejecutar Run All.
        El notebook ejecuta primero el smoke estructural y después los 16
        episodios semánticos (cuatro frameworks por cuatro episodios).

        - Commit certificado: `{commit}`
        - Wheel: `{WHEEL_NAME}`
        - Wheel SHA256: `{wheel_sha256}`
        """
    )


def _verifier() -> str:
    return textwrap.dedent(
        """\
        from __future__ import annotations

        import hashlib
        import json
        from pathlib import Path


        root = Path(__file__).resolve().parent
        checked = 0
        for row in (root / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            expected, relative = row.split("  ", 1)
            artifact = root / relative
            if not artifact.is_file():
                raise SystemExit(f"missing: {relative}")
            actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
            if actual != expected:
                raise SystemExit(f"checksum mismatch: {relative}")
            checked += 1
        print(json.dumps({"ok": True, "files": checked}, sort_keys=True))
        """
    )


def _checksums(root: Path) -> str:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name == "SHA256SUMS.txt":
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    return "\n".join(rows) + "\n"


def _audit(root: Path) -> None:
    secret_paths = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        payload = path.read_bytes()
        if any(pattern.search(payload) for pattern in SECRET_PATTERNS):
            secret_paths.append(path.relative_to(root).as_posix())
    if secret_paths:
        raise RuntimeError({"secret_paths": secret_paths})


def _zip_tree(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = f"{source.name}/{path.relative_to(source).as_posix()}"
            entry = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, path.read_bytes())


def build(*, wheel: Path, commit: str, output_dir: Path) -> Path:
    wheel = wheel.resolve()
    output_dir = output_dir.resolve()
    if not wheel.is_file():
        raise FileNotFoundError(wheel)
    if wheel.name != WHEEL_NAME:
        raise ValueError(f"Expected wheel filename {WHEEL_NAME!r}")
    if len(commit) != 40:
        raise ValueError("commit must be the full 40-character Git SHA")

    wheel_sha256 = _sha256(wheel)
    provenance = _provenance(commit)
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{PACKAGE_STEM}.zip"
    with tempfile.TemporaryDirectory(prefix="agentic-systems-ada-validation-") as tmp:
        package = Path(tmp) / PACKAGE_STEM
        package.mkdir()
        artifacts = package / "artifacts"
        artifacts.mkdir()
        shutil.copy2(wheel, artifacts / wheel.name)
        for relative in STUDIO_EXPORTS:
            source = STUDIO / relative
            target = package / "studio" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(
                    source,
                    target,
                    ignore=shutil.ignore_patterns(
                        "__pycache__", "*.pyc", "*.pyo", ".ipynb_checkpoints"
                    ),
                )
            else:
                shutil.copy2(source, target)
        dotenv = _dotenv(commit=commit, wheel=wheel, wheel_sha256=wheel_sha256).replace(
            f"AGENTIC_SYSTEMS_WHEEL={wheel.name}",
            f"AGENTIC_SYSTEMS_WHEEL=artifacts/{wheel.name}",
        )
        (package / ".env.example").write_text(dotenv, encoding="utf-8")
        (package / "requirements-ada.txt").write_text(_requirements(), encoding="utf-8")
        (package / "README.md").write_text(
            _readme(commit=commit, wheel_sha256=wheel_sha256), encoding="utf-8"
        )
        (package / "verify_bundle.py").write_text(_verifier(), encoding="utf-8")

        notebook = _packaged_notebook(
            commit=commit, wheel=wheel, wheel_sha256=wheel_sha256
        )
        nbformat.write(notebook, package / "bedrock_iam_attestation.ipynb")

        validation = package / "validation"
        validation.mkdir()
        for script in VALIDATION_SCRIPTS:
            shutil.copy2(ROOT / "scripts" / script, validation / script)
        for script in (
            "run_live_matrix.py",
            "validate_live_attestation.py",
            "run_semantic_matrix.py",
            "semantic_e2e_application.py",
        ):
            shutil.copy2(ROOT / "scripts" / script, package / script)

        manifest = {
            "schema_version": "agentic-systems.ada-iam-validation/v1",
            "package_version": "2.1.2",
            "configuration_source": ".env",
            "configuration_template": ".env.example",
            "mutable_configuration_excluded_from_checksums": True,
            "credentials_included": False,
            "wheel": {"filename": wheel.name, "sha256": wheel_sha256},
            "provenance": provenance,
            "providers": ["bedrock-runtime"],
            "frameworks": ["native", "langgraph", "openai-agents", "strands"],
            "authentication_required": "aws-credential-chain",
            "semantic_episodes": 16,
            "studio": "one-conversational-agentic-system",
        }
        (package / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        _audit(package)
        (package / "SHA256SUMS.txt").write_text(_checksums(package), encoding="utf-8")
        _zip_tree(package, destination)

    print(
        json.dumps(
            {
                "bundle": str(destination),
                "bundle_sha256": _sha256(destination),
                "wheel_sha256": wheel_sha256,
                "commit": commit,
            }
        )
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, default=DEFAULT_WHEEL)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(wheel=args.wheel, commit=args.commit, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
