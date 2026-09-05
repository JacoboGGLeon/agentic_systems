"""Build the final portable Colab kit from one wheel and one Git commit."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import re
import shutil
import subprocess
import textwrap
import zipfile
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "release" / "notebooks" / "vllm_attestation.ipynb"
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
DEFAULT_WHEEL = ROOT / "dist" / "agentic_systems-2.1.2-py3-none-any.whl"
DEFAULT_OUTPUT = ROOT / "dist"
PACKAGE_STEM = "agentic-systems-2.1.2-vllm-qwen4b-colab-final"
NOTEBOOK_FILENAME = "03_vllm_qwen4b_colab_final.ipynb"
STUDIO_NOTEBOOK_FILENAME = "04_vllm_qwen4b_colab_studio.ipynb"
DEFAULT_MODEL_ID = "unsloth/Qwen3-4B-Instruct-2507"
DEFAULT_BASE_MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"

MODEL_REFERENCE = re.compile(r"(?:unsloth|Qwen)/Qwen3-[A-Za-z0-9_.:-]+")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _dotenv(
    *,
    commit: str,
    application_commit: str,
    wheel: Path,
    wheel_sha256: str,
    model_id: str,
    base_model_id: str,
) -> str:
    return textwrap.dedent(
        f"""\
        RUN_VLLM_LIVE=1

        AGENTIC_SYSTEMS_COMMIT_SHA={commit}
        AGENTIC_SYSTEMS_APPLICATION_COMMIT_SHA={application_commit}
        AGENTIC_SYSTEMS_WHEEL=/content/{wheel.name}
        AGENTIC_SYSTEMS_WHEEL_FILENAME={wheel.name}
        AGENTIC_SYSTEMS_WHEEL_SHA256={wheel_sha256}

        VLLM_MODEL={model_id}
        VLLM_BASE_MODEL={base_model_id}
        VLLM_PROFILE=custom
        VLLM_HOST=127.0.0.1
        VLLM_PORT=8000
        VLLM_BASE_URL=http://127.0.0.1:8000/v1
        VLLM_API_KEY=vllm
        VLLM_TOOL_CALL_PARSER=hermes
        VLLM_REASONING_PARSER=
        VLLM_ENABLE_THINKING=0
        VLLM_TEMPERATURE=0.7
        AGENTIC_SYSTEMS_LIVE_TEMPERATURE=0.0
        VLLM_GPU_MEMORY_UTILIZATION=0.75
        VLLM_MAX_MODEL_LEN=8192
        VLLM_MAX_NUM_SEQS=2

        AGENTIC_SYSTEMS_STUDIO_PRESENTATION=streamlit
        AGENTIC_SYSTEMS_STUDIO_TRANSPORT=colab-proxy
        AGENTIC_SYSTEMS_STUDIO_HOST=127.0.0.1
        AGENTIC_SYSTEMS_STUDIO_PORT=8501

        AGENTIC_SYSTEMS_PROVIDER=vllm-runtime
        AGENTIC_SYSTEMS_FRAMEWORK=native
        AGENTIC_SYSTEMS_PROVIDER_PRIORITY=vllm-runtime
        RUN_SEMANTIC_MATRIX_LIVE=1
        OPENAI_AGENTS_DISABLE_TRACING=1
        """
    )


def _readme(
    *,
    commit: str,
    application_commit: str,
    wheel: Path,
    wheel_sha256: str,
    model_id: str,
) -> str:
    return textwrap.dedent(
        f"""\
        # Agentic Systems 2.1.2 · vLLM/Qwen 4B final live kit

        El bundle contiene dos recorridos sobre el mismo wheel, modelo y Studio:

        1. Abre un Colab nuevo y selecciona una GPU L4.
        2. Para conversar de inmediato, abre `{STUDIO_NOTEBOOK_FILENAME}`, sube
           `{PACKAGE_STEM}.zip` y ejecuta **Run all**. Este notebook sólo instala,
           levanta vLLM/Qwen y presenta Studio; no ejecuta la attestation.
        3. Para certificar el release, abre `{NOTEBOOK_FILENAME}`. Ese recorrido sí
           produce `vllm-semantic-attestation.json`, `vllm-semantic-review.md` y
           `vllm-studio-live.json`.
        4. En ambos casos, el ModelServer permanece activo hasta ejecutar
           `close_studio_and_model_server()`.

        Colab presenta **Agentic Systems Studio** mediante un botón HTML que abre
        una pestaña nueva sobre su proxy autenticado. El perfil `colab-proxy`
        mantiene Streamlit en loopback y adapta CORS/XSRF y WebSocket sólo para esa
        frontera confiable; no cambia provider, framework ni lógica de aplicación.
        La UI notebook-native sigue disponible como alternativa explícita con
        `AGENTIC_SYSTEMS_STUDIO_PRESENTATION=notebook`.

        Identidad certificable:

        - Wheel commit: `{commit}`
        - Studio application commit: `{application_commit}`
        - Wheel: `{wheel.name}`
        - SHA256: `{wheel_sha256}`
        - Model: `{model_id}`

        `.env` es la fuente canónica y mutable de configuración. El notebook de
        certificación verifica los materiales inmutables antes de instalar; `.env`
        queda fuera del checksum para permitir cambiar recursos sin invalidar el
        ZIP. No se permite fallback de provider. La certificación exige respuesta
        humana, linaje, validación determinista y judge; `ok=true` por sí solo no
        certifica una celda.
        """
    )


def _bootstrap(
    wheel_filename: str,
    *,
    include_attestation: bool = True,
) -> nbformat.NotebookNode:
    required = [
        ".env",
        wheel_filename,
        "studio/app.py",
        "studio/src/agentic_systems_studio/__init__.py",
    ]
    if include_attestation:
        required.extend(
            [
                "run_semantic_matrix.py",
                "semantic_e2e_application.py",
                "studio/scripts/validate_conversation_live.py",
            ]
        )
    required_source = "\n".join(f"    CONTENT / {name!r}," for name in required)
    source = f"""from pathlib import Path
import hashlib
import zipfile

CONTENT = Path("/content")
REQUIRED = (
{required_source}
)

from google.colab import files

uploaded = files.upload()
package_names = [name for name in uploaded if name.lower().endswith(".zip")]
assert len(package_names) == 1, "Sube exactamente un ZIP del paquete E2E"
with zipfile.ZipFile(CONTENT / package_names[0]) as package:
    package.extractall(CONTENT)

missing = [str(path) for path in REQUIRED if not path.is_file()]
assert not missing, {{"missing_package_files": missing}}
manifest_path = CONTENT / "SHA256SUMS.txt"
assert manifest_path.is_file(), {{"missing_package_files": [str(manifest_path)]}}
for line in manifest_path.read_text(encoding="utf-8").splitlines():
    expected, filename = line.split("  ", 1)
    artifact = CONTENT / filename
    actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert actual == expected, {{
        "checksum_mismatch": filename,
        "actual": actual,
        "expected": expected,
    }}
print("Agentic Systems vLLM final package ready")"""
    cell = nbformat.v4.new_code_cell(source)
    cell["id"] = "vllm-final-bootstrap"
    cell.metadata["tags"] = ["colab-bootstrap", "package-contract"]
    return cell


def _configure_notebook_models(
    notebook: nbformat.NotebookNode,
    *,
    model_id: str,
    base_model_id: str,
) -> None:
    """Project the package model contract into every notebook cell."""
    replacements = {"unsloth": model_id, "Qwen": base_model_id}
    for cell in notebook.cells:
        source = str(cell.get("source", ""))
        cell["source"] = MODEL_REFERENCE.sub(
            lambda match: replacements[match.group(0).split("/", 1)[0]],
            source,
        )


def _studio_cell() -> nbformat.NotebookNode:
    source = """from pathlib import Path
import json
import subprocess
import sys

if RUN_VLLM_LIVE:
    studio_root = Path("/content/studio")
    studio_gate = studio_root / "scripts" / "validate_conversation_live.py"
    if not studio_gate.is_file():
        raise FileNotFoundError(studio_gate)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "-e", str(studio_root)],
        check=True,
    )
    studio_output = Path("/content/vllm-studio-live.json")
    studio_run = subprocess.run(
        [
            sys.executable,
            str(studio_gate),
            "--providers",
            "vllm-runtime",
            "--output",
            str(studio_output),
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
        title="vLLM Studio live gate",
    )
    if studio_run.returncode:
        raise RuntimeError("vLLM Studio live gate failed")
    studio_report = json.loads(studio_output.read_text(encoding="utf-8"))
    assert studio_report["ok"] is True
    from IPython.display import FileLink, display

    display(FileLink(str(studio_output)))
else:
    toolkit.show_json(
        {"status": "not-run", "scope": "vllm-studio-live"},
        title="vLLM Studio live gate",
    )"""
    cell = nbformat.v4.new_code_cell(source)
    cell["id"] = "vllm-studio-live-gate"
    cell.metadata["tags"] = ["studio", "live-semantic-gate"]
    return cell


def _studio_launcher_cell() -> nbformat.NotebookNode:
    source = """import os
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

if RUN_VLLM_LIVE:
    studio_root = Path("/content/studio")
    studio_source = studio_root / "src"
    if not studio_source.is_dir():
        raise FileNotFoundError(studio_source)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "-e", str(studio_root)],
        check=True,
    )
    studio_source_text = str(studio_source)
    if studio_source_text not in sys.path:
        sys.path.insert(0, studio_source_text)

    studio_mode = os.getenv(
        "AGENTIC_SYSTEMS_STUDIO_PRESENTATION", "streamlit"
    ).strip().lower()
    if studio_mode == "streamlit":
        if find_spec("streamlit") is None:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "streamlit>=1.37"],
                check=True,
            )
        from agentic_systems_studio import launch_studio

        studio_port = int(os.getenv("AGENTIC_SYSTEMS_STUDIO_PORT", "8501"))
        studio_host = os.getenv("AGENTIC_SYSTEMS_STUDIO_HOST", "127.0.0.1")
        studio_transport = os.getenv(
            "AGENTIC_SYSTEMS_STUDIO_TRANSPORT", "auto"
        )
        studio_presentation = launch_studio(
            host=studio_host,
            port=studio_port,
            transport=studio_transport,
        )
        studio_server = studio_presentation.server
        print(
            "Studio presentation: Streamlit via "
            + studio_presentation.transport
            + " (HTML button opens a new tab)"
        )
        print("Studio health: ok")
    elif studio_mode == "notebook":
        try:
            from google.colab import output as colab_output
        except ImportError:
            colab_output = None
        if colab_output is not None:
            colab_output.enable_custom_widget_manager()
        if find_spec("ipywidgets") is None:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "ipywidgets>=8.1"],
                check=True,
            )
        from agentic_systems_studio import display_notebook_studio

        studio_view = display_notebook_studio()
        print("Studio presentation: notebook-native (explicit)")
    else:
        raise ValueError(
            "AGENTIC_SYSTEMS_STUDIO_PRESENTATION must be streamlit or notebook; "
            f"observed {studio_mode!r}."
        )
    print("When finished, run: close_studio_and_model_server()")
else:
    toolkit.show_json(
        {"status": "not-run", "scope": "vllm-studio-ui"},
        title="vLLM Studio UI",
    )"""
    cell = nbformat.v4.new_code_cell(source)
    cell["id"] = "vllm-studio-colab-launcher"
    cell.metadata["tags"] = ["studio", "colab-launcher"]
    return cell


def _studio_only_notebook(
    source: nbformat.NotebookNode,
    *,
    wheel_filename: str,
    model_id: str,
    base_model_id: str,
    commit: str,
    application_commit: str,
    wheel_sha256: str,
) -> nbformat.NotebookNode:
    """Build the direct Colab path: install → ModelServer → Studio."""

    selected_ids = [f"vllm-21-{index:02d}" for index in range(10)] + ["vllm-21-18"]
    cells_by_id = {cell.get("id"): cell for cell in source.cells}
    missing = [cell_id for cell_id in selected_ids if cell_id not in cells_by_id]
    if missing:
        raise ValueError(f"missing Studio notebook source cells: {missing}")
    notebook = nbformat.v4.new_notebook(
        metadata=copy.deepcopy(source.metadata),
        cells=[copy.deepcopy(cells_by_id[cell_id]) for cell_id in selected_ids],
    )
    notebook.cells[0]["source"] = """# Agentic Systems Studio · vLLM + Qwen 4B

Este recorrido operativo hace una sola cosa de principio a fin:

`instalar → levantar Qwen con vLLM → abrir Agentic Systems Studio`

No ejecuta smokes, matrices, judges ni attestations antes de presentar Studio.
El servidor permanece activo hasta llamar `close_studio_and_model_server()`."""
    notebook.cells[1]["source"] = """## Parámetros de ejecución

`.env` conserva la identidad del wheel y permite ajustar recursos de vLLM. El
modelo predeterminado es `unsloth/Qwen3-4B-Instruct-2507` sobre una GPU L4."""
    notebook.cells[2]["source"] = """## Frontera operativa

ModelArtifact identifica el modelo; ModelServer posee el proceso vLLM; Runtime
conecta Agentic Systems con su endpoint OpenAI-compatible; Studio utiliza esa
misma API pública sin redefinir el sistema."""
    _configure_notebook_models(
        notebook,
        model_id=model_id,
        base_model_id=base_model_id,
    )
    notebook.cells.insert(0, _bootstrap(wheel_filename, include_attestation=False))
    _insert_before_model_server_teardown(notebook, _studio_launcher_cell())
    _defer_model_server_teardown(notebook)
    notebook.metadata.setdefault("agentic_systems", {})["portable_package"] = {
        "filename": f"{PACKAGE_STEM}.zip",
        "role": "studio-direct",
        "model": model_id,
        "base_model": base_model_id,
        "commit_sha": commit,
        "application_commit_sha": application_commit,
        "wheel_filename": wheel_filename,
        "wheel_sha256": wheel_sha256,
    }
    _assert_model_consistency(
        notebook,
        model_id=model_id,
        base_model_id=base_model_id,
    )
    return notebook


def _defer_model_server_teardown(notebook: nbformat.NotebookNode) -> None:
    teardown_cells = [
        cell
        for cell in notebook.cells
        if "model-server-teardown" in cell.metadata.get("tags", ())
    ]
    if len(teardown_cells) != 1:
        raise ValueError(
            "expected exactly one tagged ModelServer teardown cell; "
            f"observed={len(teardown_cells)}"
        )
    teardown_cells[0]["source"] = """def close_studio_and_model_server():
    if not RUN_VLLM_LIVE:
        return
    try:
        if "studio_server" in globals():
            studio_server.stop()
    finally:
        server.stop()
    toolkit.show_json(
        {"status": "stopped", "owned_process_only": True},
        title="Studio and ModelServer closure",
    )


if RUN_VLLM_LIVE:
    toolkit.show_json(
        {
            "status": "running",
            "reason": "Studio remains available until explicit closure.",
            "close_with": "close_studio_and_model_server()",
        },
        title="Studio lifecycle",
    )"""


def _insert_before_model_server_teardown(
    notebook: nbformat.NotebookNode,
    cell: nbformat.NotebookNode,
) -> None:
    """Keep live consumers inside the explicit ModelServer lifecycle."""

    teardown_indexes: list[int] = []
    for index, candidate in enumerate(notebook.cells):
        if candidate.get("cell_type") != "code":
            continue
        try:
            tree = ast.parse(str(candidate.get("source", "")))
        except SyntaxError:
            continue
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "stop"
            for node in ast.walk(tree)
        ):
            teardown_indexes.append(index)

    if len(teardown_indexes) != 1:
        raise ValueError(
            "expected exactly one ModelServer teardown cell; "
            f"observed={len(teardown_indexes)}"
        )
    teardown_index = teardown_indexes[0]
    teardown = notebook.cells[teardown_index]
    tags = list(teardown.metadata.get("tags", ()))
    if "model-server-teardown" not in tags:
        tags.append("model-server-teardown")
    teardown.metadata["tags"] = tags
    notebook.cells.insert(teardown_index, cell)


def _assert_model_consistency(
    notebook: nbformat.NotebookNode,
    *,
    model_id: str,
    base_model_id: str,
) -> None:
    """Reject a bundle whose notebook references a different Qwen model."""
    observed = set(MODEL_REFERENCE.findall(nbformat.writes(notebook)))
    expected = {model_id, base_model_id}
    unexpected = observed - expected
    missing = expected - observed
    if unexpected or missing:
        raise ValueError(
            "inconsistent vLLM model references: "
            f"unexpected={sorted(unexpected)}, missing={sorted(missing)}"
        )


def _write_archive(
    package_dir: Path, files: tuple[str, ...], archive_path: Path
) -> None:
    checksum_path = package_dir / "SHA256SUMS.txt"
    immutable_files = tuple(name for name in files if name != ".env")
    checksum_path.write_text(
        "".join(f"{_sha256(package_dir / name)}  {name}\n" for name in immutable_files),
        encoding="utf-8",
    )
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for name in (*files, checksum_path.name):
            data = (package_dir / name).read_bytes()
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)


def build(
    *,
    wheel: Path,
    commit: str,
    application_commit: str,
    output_dir: Path,
    model_id: str = DEFAULT_MODEL_ID,
    base_model_id: str = DEFAULT_BASE_MODEL_ID,
) -> Path:
    wheel = wheel.resolve()
    output_dir = output_dir.resolve()
    if not wheel.is_file():
        raise FileNotFoundError(wheel)
    if len(commit) != 40:
        raise ValueError("commit must be the full 40-character Git SHA")
    if len(application_commit) != 40:
        raise ValueError("application_commit must be the full 40-character Git SHA")

    wheel_sha256 = _sha256(wheel)
    package_dir = output_dir / PACKAGE_STEM
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    packaged_wheel = package_dir / wheel.name
    shutil.copy2(wheel, packaged_wheel)
    shutil.copy2(SEMANTIC_RUNNER, package_dir / "run_semantic_matrix.py")
    shutil.copy2(SEMANTIC_APPLICATION, package_dir / "semantic_e2e_application.py")
    for relative in STUDIO_EXPORTS:
        source = STUDIO / relative
        target = package_dir / "studio" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    (package_dir / ".env").write_text(
        _dotenv(
            commit=commit,
            application_commit=application_commit,
            wheel=wheel,
            wheel_sha256=wheel_sha256,
            model_id=model_id,
            base_model_id=base_model_id,
        ),
        encoding="utf-8",
    )
    (package_dir / "README.md").write_text(
        _readme(
            commit=commit,
            application_commit=application_commit,
            wheel=wheel,
            wheel_sha256=wheel_sha256,
            model_id=model_id,
        ),
        encoding="utf-8",
    )

    source_notebook = nbformat.read(SOURCE, as_version=4)
    notebook = copy.deepcopy(source_notebook)
    _configure_notebook_models(
        notebook,
        model_id=model_id,
        base_model_id=base_model_id,
    )
    notebook.cells.insert(0, _bootstrap(wheel.name))
    _insert_before_model_server_teardown(notebook, _studio_cell())
    _insert_before_model_server_teardown(notebook, _studio_launcher_cell())
    _defer_model_server_teardown(notebook)
    notebook.metadata.setdefault("agentic_systems", {})["portable_package"] = {
        "filename": f"{PACKAGE_STEM}.zip",
        "model": model_id,
        "base_model": base_model_id,
        "commit_sha": commit,
        "application_commit_sha": application_commit,
        "wheel_filename": wheel.name,
        "wheel_sha256": wheel_sha256,
    }
    _assert_model_consistency(
        notebook,
        model_id=model_id,
        base_model_id=base_model_id,
    )
    nbformat.write(notebook, package_dir / NOTEBOOK_FILENAME)
    studio_notebook = _studio_only_notebook(
        source_notebook,
        wheel_filename=wheel.name,
        model_id=model_id,
        base_model_id=base_model_id,
        commit=commit,
        application_commit=application_commit,
        wheel_sha256=wheel_sha256,
    )
    nbformat.write(studio_notebook, package_dir / STUDIO_NOTEBOOK_FILENAME)
    package_files = (
        ".env",
        NOTEBOOK_FILENAME,
        STUDIO_NOTEBOOK_FILENAME,
        wheel.name,
        "README.md",
        "run_semantic_matrix.py",
        "semantic_e2e_application.py",
        *(
            path.relative_to(package_dir).as_posix()
            for path in sorted(
                item for item in (package_dir / "studio").rglob("*") if item.is_file()
            )
        ),
    )
    archive_path = output_dir / f"{PACKAGE_STEM}.zip"
    _write_archive(package_dir, package_files, archive_path)
    print(
        f"{archive_path}\n"
        f"commit={commit}\n"
        f"application_commit={application_commit}\n"
        f"wheel={wheel.name}\n"
        f"wheel_sha256={wheel_sha256}\n"
        f"package_sha256={_sha256(archive_path)}"
    )
    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, default=DEFAULT_WHEEL)
    parser.add_argument("--commit", default=None)
    parser.add_argument("--application-commit", default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL_ID)
    args = parser.parse_args()
    build(
        wheel=args.wheel,
        commit=args.commit or _git_commit(),
        application_commit=args.application_commit or _git_commit(),
        output_dir=args.output_dir,
        model_id=args.model,
        base_model_id=args.base_model,
    )


if __name__ == "__main__":
    main()
