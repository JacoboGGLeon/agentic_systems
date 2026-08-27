"""Generate the canonical vLLM + Unsloth tutorial and release attestation."""

from __future__ import annotations

from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
ATTESTATION = ROOT / "release" / "notebooks" / "vllm_attestation.ipynb"


def _metadata() -> dict[str, object]:
    import agentic_systems as toolkit

    relative = "providers/03_vllm.ipynb"
    scenarios = [
        item["id"]
        for item in toolkit.api_contract()["scenarios"]
        if relative in item["notebooks"]
    ]
    return {
        "agentic_systems": {
            "api_coverage": [
                "toolkit.model_artifact",
                "toolkit.model_server",
                "server.inspect",
                "server.start",
                "server.health",
                "server.runtime",
                "server.stop",
                "toolkit.runtime",
                "toolkit.tool",
                "toolkit.system",
                "system.agent",
                "agent.run",
                "toolkit.human_result",
                "toolkit.run_result_output",
                "toolkit.RunResult",
                "toolkit.show_json",
                "toolkit.AgentContract",
                "toolkit.RunPolicy",
            ],
            "contract_scenarios": scenarios,
            "curriculum_order": 4,
            "curriculum_origin": "v1.0.7",
            "execution_mode": "live-optional",
            "framework": "native",
            "layer": "providers",
            "narrative_reviewed": "2.1.0",
            "provider": "vllm-runtime",
        },
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.10"},
    }


def build_notebook() -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook(metadata=_metadata())
    nb.cells = [
        nbformat.v4.new_markdown_cell(
            """# Providers 03 - vLLM + Unsloth + Qwen

Objetivo: usar este notebook como punto de entrada único de Colab para vllm-runtime. Recupera la receta de Agentic Systems 1.0, pero usa la API pública 2.1: ModelArtifact, ModelServer, RuntimeConfig, Agent, RunResult y la certificación de los cuatro Frameworks.

**Lugar en el modelo:** vLLM es el Provider de inferencia y ModelServer es la frontera de infraestructura; Unsloth/Qwen identifica el artefacto, mientras Agent y System conservan su lógica.

**Evidencia exigida:** live debe producir un RunResult con engine vllm-runtime, ejecutar multiply y emitir una attestation aprobada para native, LangGraph, OpenAI Agents y Strands.

**Límite de la evidencia:** la ruta offline sólo demuestra construcción, schemas y not-run. La compatibilidad GPU exige ejecutar la ruta live sobre el wheel y commit exactos.

El servidor tiene ciclo de vida explícito. Construirlo no inicia procesos; start registra endpoint y PID, y stop termina únicamente el proceso propio.

Requisito live: Runtime de Colab con GPU. Para certificar un release, sube el wheel candidato exacto y completa COMMIT_SHA con el commit que produjo ese wheel. RUN_VLLM_LIVE=0 conserva una ruta offline not-run para los gates."""
        ),
        nbformat.v4.new_markdown_cell(
            """## Parametros de la demostracion

| Variable | Default | Proposito |
|---|---|---|
| RUN_VLLM_LIVE | 1 | Usa 0 para ejecutar sólo el contrato offline. |
| COMMIT_SHA | candidato 2.1.0 | Commit exacto que produjo el wheel candidato. |
| EXPECTED_WHEEL_SHA256 | candidato 2.1.0 | Hash que debe tener el wheel subido. |
| MODEL_ID | unsloth/Qwen3-0.6B | Modelo ligero con tool calling para Colab. |
| PROFILE | auto | Resuelve fast, medium o power desde VRAM; admite override. |
| VLLM_DTYPE | automático | half en T4; bfloat16 desde compute capability 8.0. |
| VLLM_ENABLE_THINKING | 0 | Desactiva reasoning en tool calling multi-turn. |
| VLLM_TEMPERATURE | 0.7 | Sampling recomendado por Qwen3 en modo non-thinking. |

En Colab: selecciona GPU, ejecuta en orden y sube el wheel indicado. Los valores
pueden sustituirse mediante variables de entorno para certificar otro candidato."""
        ),
        nbformat.v4.new_markdown_cell(
            """## Contrato de la demostracion

La misma fachada pública cubre el ciclo completo: model_artifact, model_server, runtime, system, agent y RunResult. El runner final sustituye sólo el Framework y conserva Provider, endpoint y modelo."""
        ),
        nbformat.v4.new_code_cell(
            """import json
import os
import subprocess
import sys
from pathlib import Path


def load_canonical_dotenv(start: Path) -> Path | None:
    # The explicit path exists for isolated CI; otherwise the nearest .env is king.
    explicit = os.getenv("AGENTIC_SYSTEMS_DOTENV")
    candidates = (
        (Path(explicit).expanduser().resolve(),)
        if explicit
        else tuple(directory / ".env" for directory in (start.resolve(), *start.resolve().parents))
    )
    for candidate in candidates:
        if not candidate.is_file():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key:
                os.environ[key] = value.strip().strip('"').strip("'")
        return candidate
    return None


DOTENV_PATH = load_canonical_dotenv(Path.cwd())
RUN_VLLM_LIVE = os.getenv("RUN_VLLM_LIVE", "1").strip().lower() in {"1", "true", "yes"}
COMMIT_SHA = os.getenv("AGENTIC_SYSTEMS_COMMIT_SHA", "").strip()
EXPECTED_WHEEL_FILENAME = os.getenv("AGENTIC_SYSTEMS_WHEEL_FILENAME", "").strip()
EXPECTED_WHEEL_SHA256 = os.getenv("AGENTIC_SYSTEMS_WHEEL_SHA256", "").strip().lower()
MODEL_ID = os.getenv("VLLM_MODEL", "unsloth/Qwen3-0.6B")
BASE_MODEL_ID = os.getenv("VLLM_BASE_MODEL", "Qwen/Qwen3-0.6B")
REQUESTED_PROFILE = os.getenv("VLLM_PROFILE", "fast").strip().lower()
VLLM_HOST = os.getenv("VLLM_HOST", "127.0.0.1")
VLLM_PORT = int(os.getenv("VLLM_PORT", "8000"))
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", f"http://{VLLM_HOST}:{VLLM_PORT}/v1")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "vllm")
VLLM_TOOL_CALL_PARSER = os.getenv("VLLM_TOOL_CALL_PARSER", "hermes")
VLLM_ENABLE_THINKING = os.getenv("VLLM_ENABLE_THINKING", "0").strip().lower() in {
    "1", "true", "yes"
}
VLLM_REASONING_PARSER = os.getenv(
    "VLLM_REASONING_PARSER", "qwen3" if VLLM_ENABLE_THINKING else ""
).strip() or None
VLLM_TEMPERATURE = float(os.getenv("VLLM_TEMPERATURE", "0.7"))
VLLM_GPU_MEMORY_UTILIZATION = float(os.getenv("VLLM_GPU_MEMORY_UTILIZATION", "0.4"))
VLLM_MAX_MODEL_LEN = int(os.getenv("VLLM_MAX_MODEL_LEN", "8192"))
VLLM_MAX_NUM_SEQS = int(os.getenv("VLLM_MAX_NUM_SEQS", "4"))
assert REQUESTED_PROFILE in {"auto", "fast", "medium", "power", "custom"}

WHEEL_PATH = None
if RUN_VLLM_LIVE:
    assert len(COMMIT_SHA) == 40, "Define AGENTIC_SYSTEMS_COMMIT_SHA en .env"
    assert EXPECTED_WHEEL_FILENAME.endswith(".whl"), (
        "Define AGENTIC_SYSTEMS_WHEEL_FILENAME en .env"
    )
    assert len(EXPECTED_WHEEL_SHA256) == 64, (
        "Define AGENTIC_SYSTEMS_WHEEL_SHA256 en .env"
    )
    configured_wheel = os.getenv("AGENTIC_SYSTEMS_WHEEL")
    search_roots = [Path.cwd(), Path("/content")]
    wheel_candidates = (
        [Path(configured_wheel).expanduser()]
        if configured_wheel
        else [
            root / EXPECTED_WHEEL_FILENAME
            for root in search_roots
            if (root / EXPECTED_WHEEL_FILENAME).is_file()
        ]
    )
    wheel_candidates = list(dict.fromkeys(path.resolve() for path in wheel_candidates))
    if len(wheel_candidates) > 1:
        raise RuntimeError(
            "Existe más de un wheel candidato; define AGENTIC_SYSTEMS_WHEEL en .env"
        )
    if wheel_candidates:
        WHEEL_PATH = str(wheel_candidates[0])
    else:
        try:
            from google.colab import files
        except ImportError as exc:
            raise FileNotFoundError(
                f"Coloca {EXPECTED_WHEEL_FILENAME} junto al notebook"
            ) from exc
        uploaded = files.upload()
        wheel_names = [name for name in uploaded if name.endswith(".whl")]
        assert len(wheel_names) == 1, "Sube exactamente un wheel de agentic-systems"
        WHEEL_PATH = "/content/" + wheel_names[0]"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 1) Instalar el wheel y vLLM

La instalación usa el backend de Torch resuelto por vLLM para no mezclar wheels CUDA. TorchVision se instala en la misma transacción porque vLLM 0.27 lo importa durante el warm-up incluso para modelos de texto; sólo TorchAudio se retira si Colab dejó una variante CUDA incompatible."""
        ),
        nbformat.v4.new_code_cell(
            """if RUN_VLLM_LIVE:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "uv"], check=True)
    subprocess.run([
        "uv", "pip", "install", "-U", "vllm", "torchvision",
        "--torch-backend=auto",
    ], check=True)
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-q",
        "--force-reinstall", "--no-deps", WHEEL_PATH,
    ], check=True)
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-q",
        "openai>=2.45,<3", "openai-agents>=0.18.3,<0.19",
        "langgraph>=0.2", "strands-agents>=1.29,<2", "mcp>=1,<2",
    ], check=True)
    subprocess.run([
        sys.executable, "-m", "pip", "uninstall", "-y", "torchaudio"
    ], check=False)"""
        ),
        nbformat.v4.new_code_cell(
            """import hashlib
import platform
from importlib.metadata import version as package_version

import agentic_systems as toolkit

wheel_sha256 = hashlib.sha256(Path(WHEEL_PATH).read_bytes()).hexdigest() if WHEEL_PATH else None
environment = {
    "package": toolkit.__name__,
    "version": toolkit.__version__,
    "python": platform.python_version(),
    "run_live": RUN_VLLM_LIVE,
    "wheel_sha256": wheel_sha256,
    "dotenv": str(DOTENV_PATH) if DOTENV_PATH else None,
    "model": MODEL_ID,
    "requested_profile": REQUESTED_PROFILE,
    "host": VLLM_HOST,
    "port": VLLM_PORT,
    "api_key_configured": bool(VLLM_API_KEY),
}
if RUN_VLLM_LIVE:
    import torch

    assert Path(WHEEL_PATH).name == EXPECTED_WHEEL_FILENAME, (
        Path(WHEEL_PATH).name,
        EXPECTED_WHEEL_FILENAME,
    )
    assert wheel_sha256 == EXPECTED_WHEEL_SHA256, (
        wheel_sha256,
        EXPECTED_WHEEL_SHA256,
    )
    environment.update(
        torch=torch.__version__,
        torchvision=package_version("torchvision"),
        vllm=package_version("vllm"),
        cuda_available=torch.cuda.is_available(),
        gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        cuda_capability=(
            list(torch.cuda.get_device_capability(0))
            if torch.cuda.is_available()
            else None
        ),
    )
    assert toolkit.__version__ == "2.1.0"
    assert torch.cuda.is_available(), "Selecciona Runtime > Change runtime type > GPU"

    cuda_major, cuda_minor = torch.cuda.get_device_capability(0)
    gpu_properties = torch.cuda.get_device_properties(0)
    gpu_memory_gib = round(gpu_properties.total_memory / (1024 ** 3), 2)
    VLLM_DTYPE = os.getenv("VLLM_DTYPE") or (
        "half" if cuda_major < 8 else "bfloat16"
    )
    if REQUESTED_PROFILE == "auto":
        PROFILE = (
            "fast"
            if gpu_memory_gib < 20
            else "medium"
            if gpu_memory_gib < 60
            else "power"
        )
    else:
        PROFILE = REQUESTED_PROFILE
    SERVER_EXTRA_ARGS = (
        "--dtype", VLLM_DTYPE,
        "--default-chat-template-kwargs",
        json.dumps({"enable_thinking": VLLM_ENABLE_THINKING}),
    )
    environment.update(
        requested_vllm_profile=REQUESTED_PROFILE,
        selected_vllm_profile=PROFILE,
        vllm_dtype=VLLM_DTYPE,
        cuda_capability=[cuda_major, cuda_minor],
        gpu_memory_gib=gpu_memory_gib,
    )
else:
    PROFILE = REQUESTED_PROFILE if REQUESTED_PROFILE != "auto" else "fast"
    VLLM_DTYPE = None
    SERVER_EXTRA_ARGS = ()
toolkit.show_json(environment, title="Preflight vLLM")"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 2) Declarar artefacto, servidor y runtime

ModelArtifact separa la identidad servida de su modelo base. Esa frontera permite sustituir MODEL_ID por un checkpoint fine-tuned o un adapter LoRA sin rediseñar el sistema agéntico."""
        ),
        nbformat.v4.new_code_cell(
            """artifact = toolkit.model_artifact(
    MODEL_ID,
    base_model=BASE_MODEL_ID,
    metadata={"serving_library": "unsloth"},
)
server = toolkit.model_server(
    artifact,
    backend="vllm",
    profile=PROFILE,
    gpu_memory_utilization=VLLM_GPU_MEMORY_UTILIZATION,
    max_model_len=VLLM_MAX_MODEL_LEN,
    max_num_seqs=VLLM_MAX_NUM_SEQS,
    host=VLLM_HOST,
    port=VLLM_PORT,
    tool_call_parser=VLLM_TOOL_CALL_PARSER,
    reasoning_parser=VLLM_REASONING_PARSER,
    extra_args=SERVER_EXTRA_ARGS,
    startup_timeout_s=600,
    log_path="/content/vllm-server.log",
)
toolkit.show_json(server.inspect(), title="ModelServer declarado")"""
        ),
        nbformat.v4.new_code_cell(
            """if RUN_VLLM_LIVE:
    try:
        endpoint = server.start()
    except Exception as exc:
        log_path = Path("/content/vllm-server.log")
        log_text = (
            log_path.read_text(encoding="utf-8", errors="replace")
            if log_path.exists()
            else ""
        )
        diagnostic_lines = [
            line
            for line in log_text.splitlines()
            if any(
                token in line.lower()
                for token in (
                    "error",
                    "exception",
                    "runtimeerror",
                    "valueerror",
                    "traceback",
                    "cuda",
                    "bfloat16",
                    "dtype",
                )
            )
        ]
        toolkit.show_json(
            {
                "error_type": type(exc).__name__,
                "message": str(exc),
                "profile": PROFILE,
                "dtype": VLLM_DTYPE,
                "log_head": log_text[:24000],
                "log_tail": log_text[-24000:],
                "diagnostic_lines": diagnostic_lines[-200:],
            },
            title="vLLM startup failure",
        )
        raise
    health = server.health()
    toolkit.show_json(health.model_dump(mode="json"), title="vLLM health")
    assert health.status == "healthy", "Revisa /content/vllm-server.log"
    runtime = server.runtime(metadata={"tutorial": "providers/vllm-unsloth-qwen"})
else:
    endpoint = None
    health = None
    runtime = toolkit.runtime(
        provider="vllm-runtime",
        model=MODEL_ID,
        endpoint=VLLM_BASE_URL,
        metadata={"tutorial": "providers/vllm-unsloth-qwen", "live": False},
    )
toolkit.show_json(runtime.describe(), title="vLLM RuntimeConfig")"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 3) Crear system, tool y agent

Esta prueba valida el camino relevante: el modelo solicita una Tool, Agentic Systems la ejecuta y RunResult conserva la misma proyección pública que los demás Providers."""
        ),
        nbformat.v4.new_code_cell(
            """@toolkit.tool
def multiply(a: int, b: int) -> dict:
    return {"result": a * b}

system = toolkit.system(runtime=runtime)
agent = system.agent(
    name="qwen_calculator",
    instructions="Usa multiply para calcular. Devuelve sólo el resultado.",
    tools=[multiply],
    contract=toolkit.AgentContract(
        must_call=["multiply"],
        completion="when_required_tools_satisfied",
    ),
    policy=toolkit.RunPolicy(
        max_turns=3,
        max_tool_calls=1,
        temperature=VLLM_TEMPERATURE,
        tool_choice="multiply",
    ),
)
toolkit.show_json(agent.info(), title="Agente declarado")"""
        ),
        nbformat.v4.new_code_cell(
            """if RUN_VLLM_LIVE:
    result = agent.run("¿Cuánto es 17 por 19?", mode="eval")
    assert isinstance(result, toolkit.RunResult)
    assert result.ok, result.errors
    assert result.engine == "vllm-runtime"
    assert [event.name for event in result.tool_events] == ["multiply"]
    assert "323" in result.text
    assert not result.text.lstrip().startswith(("{", "[")), result.text
    assert "ToolEnvelope" not in result.text
    result.check_invariants()
    toolkit.human_result(result, title="vLLM RunResult", show_lineage=True)
    toolkit.show_json(toolkit.run_result_output(result), title="Contrato normalizado")
else:
    result = None
    toolkit.show_json({
        "status": "not-run",
        "provider": "vllm-runtime",
        "reason": "RUN_VLLM_LIVE=0; no se inició infraestructura GPU.",
    }, title="vLLM live gate")"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 4) Certificar semánticamente los cuatro frameworks

El runner oficial ejecuta cuatro episodios E2E por Framework: cálculo, poema
basado en cálculo verificado, análisis de texto y petición fuera de alcance. Una
celda sólo pasa cuando coinciden respuesta humana, ruta Agent/Tool, linaje,
identidad real, validación determinista y judge.
Un `ok=true` estructural no es suficiente."""
        ),
        nbformat.v4.new_code_cell(
            """if RUN_VLLM_LIVE:
    if not COMMIT_SHA:
        raise ValueError("Completa COMMIT_SHA con el commit exacto que produjo el wheel")
    semantic_runner = Path.cwd() / "run_semantic_matrix.py"
    semantic_application = Path.cwd() / "semantic_e2e_application.py"
    missing = [
        str(path)
        for path in (semantic_runner, semantic_application)
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError({"missing_semantic_gate_files": missing})
    os.environ.update(
        VLLM_BASE_URL=endpoint.base_url,
        VLLM_API_KEY=VLLM_API_KEY,
        VLLM_MODEL=artifact.model_id,
    )
    OUTPUT = Path("/content/vllm-semantic-attestation.json")
    REVIEW = Path("/content/vllm-semantic-review.md")
    completed = subprocess.run([
        sys.executable, str(semantic_runner),
        "--wheel", WHEEL_PATH,
        "--output", str(OUTPUT),
        "--review", str(REVIEW),
        "--commit", COMMIT_SHA,
        "--env", str(DOTENV_PATH),
        "--providers", "vllm-runtime",
        "--frameworks", "native", "langgraph", "openai-agents", "strands",
    ], text=True, capture_output=True)
    toolkit.show_json({
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }, title="vLLM live matrix")
    if completed.returncode:
        if OUTPUT.is_file():
            failed_attestation = json.loads(OUTPUT.read_text(encoding="utf-8"))
            toolkit.show_json({
                "summary": failed_attestation.get("summary"),
                "failures": [
                    {
                        "framework": cell.get("framework"),
                        "episode": episode.get("name"),
                        "review": episode.get("semantic_review", {}).get("failures", []),
                        "judge": episode.get("judge"),
                    }
                    for cell in failed_attestation.get("cells", [])
                    for episode in cell.get("episodes", [])
                    if not episode.get("ok")
                ],
            }, title="Fallas semánticas por episodio")
            files.download(str(OUTPUT))
        if REVIEW.is_file():
            files.download(str(REVIEW))
        toolkit.show_json({
            "vllm_log_tail": Path("/content/vllm-server.log").read_text(errors="replace")[-12000:],
        }, title="Diagnóstico vLLM")
        raise RuntimeError(f"La matriz live falló con código {completed.returncode}")
    attestation = json.loads(OUTPUT.read_text(encoding="utf-8"))
    summary = attestation["summary"]
    toolkit.show_json(summary, title="Semantic attestation summary")
    assert attestation["wheel_sha256"] == wheel_sha256
    assert attestation["commit_sha"] == COMMIT_SHA
    assert len(attestation["gate_assets"]["runner"]["sha256"]) == 64
    assert len(attestation["gate_assets"]["application"]["sha256"]) == 64
    assert summary["total"] == 4
    assert summary["failed"] == 0
    assert summary["episodes_total"] == 16
    assert summary["episodes_failed"] == 0
    for cell in attestation["cells"]:
        assert cell["provider"] == "vllm-runtime"
        assert cell["ok"]
        for episode in cell["episodes"]:
            assert episode["ok"]
            assert episode["semantic_review"]["ok"]
            assert episode["deterministic_validation"]["ok"]
            assert episode["judge"]["ok"]
            answer = episode["candidate"]["answer"]["text"].lstrip()
            assert not answer.startswith(("{", "[")), answer
    files.download(str(OUTPUT))
    files.download(str(REVIEW))
else:
    toolkit.show_json({"status": "not-run", "scope": "vllm-semantic-attestation"}, title="Attestation gate")"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 5) API realmente ejercitada

La cobertura enumera sólo llamadas presentes en las celdas anteriores. Servir el modelo y consumirlo son contratos separados, conectados por RuntimeConfig."""
        ),
        nbformat.v4.new_code_cell(
            """api_coverage = [
    "toolkit.model_artifact",
    "toolkit.model_server",
    "server.inspect",
    "server.start",
    "server.health",
    "server.runtime",
    "server.stop",
    "toolkit.runtime",
    "toolkit.tool",
    "toolkit.system",
    "toolkit.Skill",
    "system.agent",
    "system.compile",
    "agent.run",
    "toolkit.Evaluator.evaluate",
    "toolkit.JudgeRubric",
    "toolkit.human_result",
    "toolkit.run_result_output",
    "toolkit.RunResult",
    "toolkit.show_json",
    "toolkit.AgentContract",
    "toolkit.RunPolicy",
]
toolkit.show_json(api_coverage, title="vLLM API coverage")"""
        ),
        nbformat.v4.new_markdown_cell(
            """## Resultado e interpretacion

Con live desactivado: contratos declarativos y estados not-run ejecutables. Con
live activado: un RunResult vllm-runtime con respuesta humana y una certificación
semántica de 16 episodios sobre native, LangGraph, OpenAI Agents y Strands. Para
fine-tuning, entrena y guarda un checkpoint o adapter con Unsloth, cambia MODEL_ID
y conserva el resto."""
        ),
        nbformat.v4.new_code_cell(
            """if RUN_VLLM_LIVE:
    server.stop()
    toolkit.show_json(
        {"status": "stopped", "owned_process_only": True},
        title="ModelServer closure",
    )"""
        ),
    ]
    for index, cell in enumerate(nb.cells):
        cell["id"] = f"vllm-21-{index:02d}"
    return nb


def main() -> None:
    notebook = build_notebook()
    for path in (ATTESTATION,):
        path.parent.mkdir(parents=True, exist_ok=True)
        nbformat.write(notebook, path)
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
