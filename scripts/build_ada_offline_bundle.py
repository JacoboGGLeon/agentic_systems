"""Build a reproducible, credential-free Agentic Systems delivery for ADA."""

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

from agentic_systems.registry import FRAMEWORK_NAMES, PROVIDER_NAMES

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 only.
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
VERSION = str(
    tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
)
DIST = ROOT / "dist"
EVIDENCE = DIST / "release-evidence"
SUMMARY = EVIDENCE / "final-certification-summary.json"
WHEEL = DIST / f"agentic_systems-{VERSION}-py3-none-any.whl"
SDIST = DIST / f"agentic_systems-{VERSION}.tar.gz"
STUDIO = ROOT / "examples" / "agentic_systems_studio"
TUTORIALS = ROOT / "tutorials"
OUTPUT_NAME = f"agentic-systems-{VERSION}-ada-offline.zip"
SECRET_PATTERNS = (
    re.compile(rb"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"(?<![A-Z0-9])AKIA[0-9A-Z]{16}"),
    re.compile(rb"(?<![A-Z0-9])ASIA[0-9A-Z]{16}"),
)
STUDIO_EXPORTS = (
    "README.md",
    "pyproject.toml",
    "app.py",
    "src",
    "notebooks",
    "docs",
)
VALIDATION_EXPORTS = (
    "run_ada_semantic_matrix.py",
    "run_semantic_matrix.py",
    "semantic_e2e_application.py",
)
FRAMEWORKS = set(FRAMEWORK_NAMES)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_semantic_evidence(
    path: Path,
    *,
    provider: str,
    certification: dict[str, object],
    row: dict[str, object],
) -> None:
    payload = _read_json(path)
    if (
        payload.get("schema_version") != "agentic_systems.semantic-attestation.v1"
        or payload.get("commit_sha") != certification["commit_sha"]
        or payload.get("wheel_sha256") != certification["wheel_sha256"]
        or not payload.get("wheel_runtime_verified")
    ):
        raise ValueError(f"Semantic evidence identity mismatch: {path.name}")

    cells = [
        cell for cell in payload.get("cells", []) if cell.get("provider") == provider
    ]
    episodes = [episode for cell in cells for episode in cell.get("episodes", [])]
    if (
        len(cells) != 4
        or {cell.get("framework") for cell in cells} != FRAMEWORKS
        or any(not cell.get("ok") for cell in cells)
        or len(episodes) != row.get("episodes_passed")
        or any(
            not episode.get("ok")
            or not episode.get("deterministic_validation", {}).get("ok")
            or not episode.get("judge", {}).get("ok")
            for episode in episodes
        )
    ):
        raise ValueError(f"Semantic evidence is incomplete: {provider}")

    runtime = (
        payload.get("environment", {})
        .get("providers", {})
        .get(provider, {})
        .get("runtime", {})
    )
    if runtime.get("selected_provider") != provider or runtime.get("fallback_provider"):
        raise ValueError(f"Semantic evidence used fallback: {provider}")


def _validate_authentication_evidence(
    path: Path,
    *,
    certification: dict[str, object],
    row: dict[str, object],
) -> None:
    payload = _read_json(path)
    cases = payload.get("cases", [])
    environment = payload.get("environment", {})
    if (
        payload.get("schema_version") != "agentic_systems.live-attestation.v1"
        or payload.get("commit_sha") != certification["commit_sha"]
        or payload.get("wheel_sha256") != certification["wheel_sha256"]
        or environment.get("bedrock_authentication_mode")
        != row.get("authentication_mode")
        or not environment.get("uses_aws_credential_chain")
        or len(cases) != 4
        or {case.get("framework") for case in cases} != FRAMEWORKS
        or any(
            case.get("provider") != "bedrock-runtime" or not case.get("ok")
            for case in cases
        )
    ):
        raise ValueError(f"Authentication evidence is incomplete: {path.name}")

    for case in cases:
        for scenario in case.get("scenarios", []):
            details = scenario.get("details", {})
            if not scenario.get("ok") or details.get("fallback_provider"):
                raise ValueError(f"Authentication evidence used fallback: {path.name}")


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _copy(source: Path, target: Path) -> None:
    ignored = shutil.ignore_patterns(
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
        ".ipynb_checkpoints",
        "*.codex-backup",
        "dist",
    )
    if source.is_dir():
        shutil.copytree(source, target, ignore=ignored)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _load_certification() -> dict[str, object]:
    if not SUMMARY.is_file():
        raise FileNotFoundError(
            "Missing final certification summary; live evidence is required for ADA"
        )
    certification = json.loads(SUMMARY.read_text(encoding="utf-8"))
    totals = certification.get("totals", {})
    if (
        certification.get("schema_version")
        != "agentic_systems.release-certification.v1"
        or certification.get("package_version") != VERSION
        or totals.get("certified_live_executions") != 24
        or totals.get("certified_live_failed") != 0
        or not certification.get("no_fallback")
        or not certification.get("secrets_redacted")
    ):
        raise ValueError("Release certification is incomplete or inconsistent")
    if not WHEEL.is_file() or sha256(WHEEL) != certification.get("wheel_sha256"):
        raise ValueError("Certified wheel is missing or its SHA256 changed")
    if not SDIST.is_file():
        raise FileNotFoundError(SDIST)

    for provider, row in certification.get("primary_matrix", {}).items():
        evidence = EVIDENCE / str(row["artifact"])
        if not evidence.is_file() or sha256(evidence) != row["sha256"]:
            raise ValueError(f"Evidence checksum mismatch: {evidence.name}")
        _validate_semantic_evidence(
            evidence,
            provider=provider,
            certification=certification,
            row=row,
        )
    for row in certification.get("additional_authentication_routes", {}).values():
        evidence = EVIDENCE / str(row["artifact"])
        if not evidence.is_file() or sha256(evidence) != row["sha256"]:
            raise ValueError(f"Evidence checksum mismatch: {evidence.name}")
        _validate_authentication_evidence(
            evidence,
            certification=certification,
            row=row,
        )
    return certification


def _provenance(
    certification: dict[str, object], *, enforce_materials_clean: bool
) -> dict[str, object]:
    certified_commit = str(certification["commit_sha"])
    materials_commit = _git("rev-parse", "HEAD")
    certified_tree = _git("rev-parse", f"{certified_commit}:src/agentic_systems")
    materials_tree = _git("rev-parse", "HEAD:src/agentic_systems")
    core_dirty = subprocess.run(
        ["git", "diff", "--quiet", "--", "src/agentic_systems"], cwd=ROOT
    ).returncode
    if certified_tree != materials_tree or core_dirty:
        raise RuntimeError(
            "The packaged core is not equivalent to the live-certified source tree"
        )
    if enforce_materials_clean:
        relevant = (
            "examples/agentic_systems_studio",
            "tutorials",
            "scripts/build_ada_offline_bundle.py",
        )
        status = _git("status", "--porcelain", "--", *relevant)
        if status:
            raise RuntimeError(
                "Commit Studio/tutorial material before building the final ADA bundle"
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
        # Resolve these packages only through the approved ADA Artifactory.
        pydantic>=2.7.0
        pandas>=2.0.0
        typing-extensions>=4.10.0
        rich>=13.0.0
        boto3>=1.39.0
        botocore>=1.39.0
        langgraph>=0.2.0
        openai>=2.45.0,<3
        openai-agents>=0.18.3,<0.19
        strands-agents[a2a]>=1.29.0,<2
        mcp>=1,<2
        streamlit>=1.37
        ipython>=8.0
        ipykernel>=6.0
        nbclient>=0.10
        nbformat>=5.10
        jupyter-server-proxy>=4.4
        """
    )


def _readme(certification: dict[str, object], provenance: dict[str, object]) -> str:
    return textwrap.dedent(
        f"""\
        # Agentic Systems {VERSION} · entrega industrial para ADA

        Este ZIP funciona sin GitHub ni PyPI. El único acceso de red esperado es
        el Artifactory aprobado y, durante una ejecución live, el endpoint del
        provider seleccionado. No contiene credenciales.

        ## Contenido

        - `artifacts/`: wheel y sdist certificados.
        - `studio/`: un solo sistema agéntico conversacional, directo y Streamlit.
        - `tutorials/`: los 21 notebooks canónicos; no hay duplicado CLI.
        - `validation/`: matriz semántica E2E ejecutable desde el wheel incluido.
        - `evidence/`: matriz primaria 20/20 y ruta Bedrock IAM 4/4.
        - `.env.example`: contrato único para provider, framework y modelo.
        - `verify_bundle.py`: verificación offline de todos los checksums.

        ## Instalación aislada

        Configura pip mediante la política de tu plataforma (`PIP_INDEX_URL`,
        certificado corporativo y autenticación de Artifactory). No copies esas
        credenciales a `.env`.

        Windows:

            py -3.10 -m venv .venv-agentic-systems
            .venv-agentic-systems\\Scripts\\python -m pip install artifacts/{WHEEL.name}
            .venv-agentic-systems\\Scripts\\python -m pip install -r requirements-ada.txt
            .venv-agentic-systems\\Scripts\\python -m pip install --no-deps -e studio

        Linux / SageMaker / ADA:

            python -m venv .venv-agentic-systems
            .venv-agentic-systems/bin/python -m pip install artifacts/{WHEEL.name}
            .venv-agentic-systems/bin/python -m pip install -r requirements-ada.txt
            .venv-agentic-systems/bin/python -m pip install --no-deps -e studio
            .venv-agentic-systems/bin/python -m ipykernel install --user --name agentic-systems-2.1

        Verifica primero:

            python verify_bundle.py

        Después copia `.env.example` a `.env`, elige provider/framework y abre:

        1. Ejecuta la matriz semántica independiente:

               python validation/run_ada_semantic_matrix.py

           El provider se toma de `.env`; el gate ejecuta sus cuatro frameworks,
           valida cada respuesta determinísticamente y mediante judge, y escribe
           `outputs/<provider>-semantic-attestation.json` y
           `outputs/<provider>-semantic-review.md`.
        2. `studio/notebooks/00_conversational_system.ipynb` para ejecutar el
           sistema sin aplicación.
        3. `studio/notebooks/01_launch_studio.ipynb` para el mismo sistema mediante
           Streamlit y el proxy de JupyterLab/ADA.

        Para Bedrock IAM deja `AWS_BEARER_TOKEN_BEDROCK` vacío: boto3 hereda el
        execution role. Para vLLM configura `VLLM_BASE_URL`; Studio consume el
        endpoint y no administra un servidor GPU dentro de ADA.

        ## Identidad certificada

        - wheel: `{WHEEL.name}`
        - wheel SHA256: `{certification["wheel_sha256"]}`
        - source commit certificado: `{provenance["certified_commit"]}`
        - materials commit: `{provenance["materials_commit"]}`
        - core source equivalente: `true`
        - live: `24/24`, sin fallback

        El commit de materiales puede ser posterior porque sólo mejora tutoriales,
        Studio y tests. El builder comprueba que el árbol `src/agentic_systems`
        sea idéntico al que produjo el wheel y las evidencias live.
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
        for row in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            expected, relative = row.split("  ", 1)
            path = root / relative
            if not path.is_file():
                raise SystemExit(f"missing: {relative}")
            observed = hashlib.sha256(path.read_bytes()).hexdigest()
            if observed != expected:
                raise SystemExit(f"checksum mismatch: {relative}")
            checked += 1
        print(json.dumps({"ok": True, "files": checked}, sort_keys=True))
        """
    )


def _checksums(root: Path) -> str:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name == "SHA256SUMS":
            continue
        rows.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    return "\n".join(rows) + "\n"


def _audit(root: Path) -> None:
    forbidden = []
    secrets = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if path.name == ".env" or "/cli/" in f"/{relative.lower()}/":
            forbidden.append(relative)
        payload = path.read_bytes()
        if any(pattern.search(payload) for pattern in SECRET_PATTERNS):
            secrets.append(relative)
    if forbidden or secrets:
        raise RuntimeError({"forbidden": forbidden, "secret_paths": secrets})


def _zip_tree(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = f"{source.name}/{path.relative_to(source).as_posix()}"
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return destination


def build_bundle(
    output_dir: str | Path | None = None, *, enforce_materials_clean: bool = True
) -> Path:
    certification = _load_certification()
    provenance = _provenance(
        certification, enforce_materials_clean=enforce_materials_clean
    )
    output = Path(output_dir) if output_dir is not None else DIST
    destination = output / OUTPUT_NAME

    with tempfile.TemporaryDirectory(prefix="agentic-systems-ada-") as temporary:
        bundle = Path(temporary) / f"agentic-systems-{VERSION}-ada-offline"
        bundle.mkdir()
        _copy(WHEEL, bundle / "artifacts" / WHEEL.name)
        _copy(SDIST, bundle / "artifacts" / SDIST.name)
        _copy(TUTORIALS, bundle / "tutorials")
        _copy(EVIDENCE, bundle / "evidence")
        for relative in STUDIO_EXPORTS:
            _copy(STUDIO / relative, bundle / "studio" / relative)
        for filename in VALIDATION_EXPORTS:
            _copy(ROOT / "scripts" / filename, bundle / "validation" / filename)
        _copy(STUDIO / ".env.example", bundle / ".env.example")

        notebooks = sorted((bundle / "tutorials").rglob("*.ipynb"))
        if len(notebooks) != 21:
            raise RuntimeError(
                f"Expected 21 canonical tutorials, found {len(notebooks)}"
            )

        manifest = {
            "schema_version": "agentic-systems.ada-offline-bundle/v1",
            "package_version": VERSION,
            "configuration_source": ".env",
            "credentials_included": False,
            "internet_required": False,
            "artifact_repository": "customer-managed-artifactory",
            "wheel": {"filename": WHEEL.name, "sha256": sha256(WHEEL)},
            "sdist": {"filename": SDIST.name, "sha256": sha256(SDIST)},
            "provenance": provenance,
            "certification": {
                "schema_version": certification["schema_version"],
                "primary": "20/20",
                "semantic_episodes": "76/76",
                "bedrock_iam": "4/4",
                "total": "24/24",
                "no_fallback": True,
            },
            "providers": list(PROVIDER_NAMES),
            "frameworks": list(FRAMEWORK_NAMES),
            "studio": "one-conversational-agentic-system",
            "semantic_gate": {
                "entrypoint": "validation/run_ada_semantic_matrix.py",
                "configuration_source": ".env",
                "frameworks": sorted(FRAMEWORKS),
                "model_provider_episodes": 16,
                "outputs": [
                    "outputs/<provider>-semantic-attestation.json",
                    "outputs/<provider>-semantic-review.md",
                ],
            },
            "tutorial_notebooks": 21,
            "cli_tutorials": 0,
        }
        (bundle / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (bundle / "requirements-ada.txt").write_text(_requirements(), encoding="utf-8")
        (bundle / "README.md").write_text(
            _readme(certification, provenance), encoding="utf-8"
        )
        (bundle / "verify_bundle.py").write_text(_verifier(), encoding="utf-8")
        _audit(bundle)
        (bundle / "SHA256SUMS").write_text(_checksums(bundle), encoding="utf-8")
        _zip_tree(bundle, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--allow-dirty-materials",
        action="store_true",
        help="Testing only: do not use for a final ADA delivery",
    )
    args = parser.parse_args()
    bundle = build_bundle(
        args.output, enforce_materials_clean=not args.allow_dirty_materials
    )
    print(json.dumps({"bundle": str(bundle.resolve()), "sha256": sha256(bundle)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
