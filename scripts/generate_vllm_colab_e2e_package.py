"""Build the final portable Colab kit from one wheel and one Git commit."""

from __future__ import annotations

import argparse
import ast
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
DEFAULT_WHEEL = ROOT / "dist" / "agentic_systems-2.1.1-py3-none-any.whl"
DEFAULT_OUTPUT = ROOT / "dist"
PACKAGE_STEM = "agentic-systems-2.1.1-vllm-qwen4b-colab-final"
NOTEBOOK_FILENAME = "03_vllm_qwen4b_colab_final.ipynb"
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
    wheel: Path,
    wheel_sha256: str,
    model_id: str,
    base_model_id: str,
) -> str:
    return textwrap.dedent(
        f"""\
        RUN_VLLM_LIVE=1

        AGENTIC_SYSTEMS_COMMIT_SHA={commit}
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

        AGENTIC_SYSTEMS_PROVIDER=vllm-runtime
        AGENTIC_SYSTEMS_FRAMEWORK=native
        AGENTIC_SYSTEMS_PROVIDER_PRIORITY=vllm-runtime
        RUN_SEMANTIC_MATRIX_LIVE=1
        OPENAI_AGENTS_DISABLE_TRACING=1
        """
    )


def _readme(*, commit: str, wheel: Path, wheel_sha256: str, model_id: str) -> str:
    return textwrap.dedent(
        f"""\
        # Agentic Systems 2.1.1 · vLLM/Qwen 4B final live kit

        1. Abre un Colab nuevo y selecciona una GPU L4.
        2. Sube `{PACKAGE_STEM}.zip` cuando lo solicite la primera celda.
        3. Ejecuta **Run all** una sola vez.
        4. Descarga `vllm-semantic-attestation.json`, `vllm-semantic-review.md`
           y `vllm-studio-live.json`.
        5. El mismo notebook muestra el botón **Open Agentic Systems Studio**;
           no necesitas abrir un notebook dentro de otro. El ModelServer permanece
           activo hasta ejecutar `close_studio_and_model_server()`.

        Identidad certificable:

        - Commit: `{commit}`
        - Wheel: `{wheel.name}`
        - SHA256: `{wheel_sha256}`
        - Model: `{model_id}`

        `.env` es la fuente canónica y mutable de configuración. El notebook
        verifica los materiales inmutables antes de instalar; `.env` queda fuera
        del checksum para permitir cambiar modelo/recursos sin invalidar el ZIP. No se
        permite fallback de provider.
        El cierre exige respuesta humana, linaje jerárquico, validación
        determinista y judge; `ok=true` por sí solo no certifica una celda.
        """
    )


def _bootstrap(wheel_filename: str) -> nbformat.NotebookNode:
    source = f'''from pathlib import Path
import hashlib
import zipfile

CONTENT = Path("/content")
REQUIRED = (
    CONTENT / ".env",
    CONTENT / "{wheel_filename}",
    CONTENT / "run_semantic_matrix.py",
    CONTENT / "semantic_e2e_application.py",
    CONTENT / "studio" / "scripts" / "validate_conversation_live.py",
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
print("Agentic Systems vLLM final package ready")'''
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

from IPython.display import HTML, display

if RUN_VLLM_LIVE:
    studio_root = Path("/content/studio")
    studio_source = studio_root / "src"
    if not studio_source.is_dir():
        raise FileNotFoundError(studio_source)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "-e", str(studio_root)],
        check=True,
    )
    if find_spec("streamlit") is None:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "streamlit>=1.37"],
            check=True,
        )
    studio_source_text = str(studio_source)
    if studio_source_text not in sys.path:
        sys.path.insert(0, studio_source_text)
    from agentic_systems_studio import start_studio_server, studio_button_html

    studio_port = int(os.getenv("AGENTIC_SYSTEMS_STUDIO_PORT", "8501"))
    studio_server = start_studio_server(port=studio_port)
    try:
        from google.colab import output as colab_output
    except ImportError:
        studio_url = studio_server.local_url
    else:
        studio_url = colab_output.eval_js(
            f"google.colab.kernel.proxyPort({studio_port})"
        )
    print("Studio health: ok")
    print("Studio URL:", studio_url)
    print("When finished, run: close_studio_and_model_server()")
    display(HTML(studio_button_html(studio_url)))
else:
    toolkit.show_json(
        {"status": "not-run", "scope": "vllm-studio-ui"},
        title="vLLM Studio UI",
    )"""
    cell = nbformat.v4.new_code_cell(source)
    cell["id"] = "vllm-studio-colab-launcher"
    cell.metadata["tags"] = ["studio", "colab-launcher"]
    return cell

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
            wheel=wheel,
            wheel_sha256=wheel_sha256,
            model_id=model_id,
        ),
        encoding="utf-8",
    )

    notebook = nbformat.read(SOURCE, as_version=4)
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
        "wheel_filename": wheel.name,
        "wheel_sha256": wheel_sha256,
    }
    _assert_model_consistency(
        notebook,
        model_id=model_id,
        base_model_id=base_model_id,
    )
    nbformat.write(notebook, package_dir / NOTEBOOK_FILENAME)

    package_files = (
        ".env",
        NOTEBOOK_FILENAME,
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
        f"wheel={wheel.name}\n"
        f"wheel_sha256={wheel_sha256}\n"
        f"package_sha256={_sha256(archive_path)}"
    )
    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, default=DEFAULT_WHEEL)
    parser.add_argument("--commit", default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL_ID)
    args = parser.parse_args()
    build(
        wheel=args.wheel,
        commit=args.commit or _git_commit(),
        output_dir=args.output_dir,
        model_id=args.model,
        base_model_id=args.base_model,
    )


if __name__ == "__main__":
    main()
