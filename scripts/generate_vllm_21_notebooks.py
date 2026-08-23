"""Generate the canonical vLLM + Unsloth tutorial and release attestation."""

from __future__ import annotations

import copy
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
TUTORIAL = ROOT / "tutorials" / "providers" / "03_vllm.ipynb"
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
| COMMIT_SHA | vacío | Commit exacto que produjo el wheel candidato. |
| MODEL_ID | unsloth/Qwen3-4B-Instruct-2507 | Modelo, checkpoint o adapter servido. |
| PROFILE | custom | Perfil validado del servidor vLLM. |

En Colab: selecciona GPU, ejecuta en orden, sube el wheel y completa COMMIT_SHA."""
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

RUN_VLLM_LIVE = os.getenv("RUN_VLLM_LIVE", "1").strip().lower() in {"1", "true", "yes"}
WHEEL_PATH = None
files = None
if RUN_VLLM_LIVE:
    from google.colab import files

    uploaded = files.upload()
    wheel_names = [name for name in uploaded if name.endswith(".whl")]
    assert len(wheel_names) == 1, "Sube exactamente un wheel de agentic-systems"
    WHEEL_PATH = "/content/" + wheel_names[0]

COMMIT_SHA = ""  # obligatorio para una attestation de release
MODEL_ID = "unsloth/Qwen3-4B-Instruct-2507"
BASE_MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"
PROFILE = "custom"
PORT = 8000
MAX_MODEL_LEN = 4096
GPU_MEMORY_UTILIZATION = 0.75
MAX_NUM_SEQS = 2"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 1) Instalar el wheel y vLLM

La instalación usa el backend de Torch resuelto por vLLM para no mezclar wheels CUDA. TorchAudio y TorchVision no son necesarios para este modelo textual y se retiran si Colab dejó variantes incompatibles."""
        ),
        nbformat.v4.new_code_cell(
            """if RUN_VLLM_LIVE:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "uv"], check=True)
    subprocess.run(["uv", "pip", "install", "-U", "vllm", "--torch-backend=auto"], check=True)
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-q", WHEEL_PATH,
        "openai>=2.45,<3", "openai-agents>=0.18.3,<0.19",
        "langgraph>=0.2", "strands-agents>=1.29,<2", "mcp>=1,<2",
    ], check=True)
    subprocess.run([
        sys.executable, "-m", "pip", "uninstall", "-y", "torchaudio", "torchvision"
    ], check=False)"""
        ),
        nbformat.v4.new_code_cell(
            """import hashlib
import platform

import agentic_systems as toolkit

wheel_sha256 = hashlib.sha256(Path(WHEEL_PATH).read_bytes()).hexdigest() if WHEEL_PATH else None
environment = {
    "package": toolkit.__name__,
    "version": toolkit.__version__,
    "python": platform.python_version(),
    "run_live": RUN_VLLM_LIVE,
    "wheel_sha256": wheel_sha256,
}
if RUN_VLLM_LIVE:
    import torch

    environment.update(
        torch=torch.__version__,
        cuda_available=torch.cuda.is_available(),
        gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    )
    assert toolkit.__version__ == "2.1.0"
    assert torch.cuda.is_available(), "Selecciona Runtime > Change runtime type > GPU"
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
    host="127.0.0.1",
    port=PORT,
    max_model_len=MAX_MODEL_LEN,
    gpu_memory_utilization=GPU_MEMORY_UTILIZATION,
    max_num_seqs=MAX_NUM_SEQS,
    tool_call_parser="hermes",
    reasoning_parser=None,
    startup_timeout_s=600,
    log_path="/content/vllm-server.log",
)
toolkit.show_json(server.inspect(), title="ModelServer declarado")"""
        ),
        nbformat.v4.new_code_cell(
            """if RUN_VLLM_LIVE:
    endpoint = server.start()
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
        endpoint="http://127.0.0.1:8000/v1",
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
    policy=toolkit.RunPolicy(max_turns=3, max_tool_calls=1, temperature=0.0),
)
toolkit.show_json(agent.info(), title="Agente declarado")"""
        ),
        nbformat.v4.new_code_cell(
            """if RUN_VLLM_LIVE:
    result = agent.run("¿Cuánto es 17 por 19?", mode="eval")
    assert isinstance(result, toolkit.RunResult)
    assert result.ok, result.errors
    assert result.engine == "vllm-runtime"
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
            """## 4) Certificar los cuatro frameworks

El runner oficial consume el mismo endpoint. La attestation compara invariantes, identidad, Tools, errores y round-trip; no exige texto idéntico entre Frameworks."""
        ),
        nbformat.v4.new_code_cell(
            """if RUN_VLLM_LIVE:
    if not COMMIT_SHA:
        raise ValueError("Completa COMMIT_SHA con el commit exacto que produjo el wheel")
    repo = Path("/content/agentic-systems")
    if not repo.exists():
        subprocess.run([
            "git", "clone", "https://github.com/JacoboGGLeon/agentic_systems.git", str(repo)
        ], check=True)
    subprocess.run(["git", "-C", str(repo), "fetch", "--all", "--tags"], check=True)
    subprocess.run(["git", "-C", str(repo), "checkout", "--detach", COMMIT_SHA], check=True)
    os.environ.update(
        VLLM_BASE_URL=endpoint.base_url,
        VLLM_API_KEY="vllm",
        VLLM_MODEL=artifact.model_id,
    )
    OUTPUT = Path("/content/vllm-attestation.json")
    completed = subprocess.run([
        sys.executable, str(repo / "scripts" / "run_live_matrix.py"),
        "--wheel", WHEEL_PATH,
        "--output", str(OUTPUT),
        "--commit", COMMIT_SHA,
        "--providers", "vllm-runtime",
        "--frameworks", "native", "langgraph", "openai-agents", "strands",
    ], text=True, capture_output=True)
    toolkit.show_json({
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }, title="vLLM live matrix")
    if completed.returncode:
        toolkit.show_json({
            "vllm_log_tail": Path("/content/vllm-server.log").read_text(errors="replace")[-12000:],
        }, title="Diagnóstico vLLM")
        raise RuntimeError(f"La matriz live falló con código {completed.returncode}")
    attestation = json.loads(OUTPUT.read_text())
    toolkit.show_json(attestation.get("summary", {}), title="Attestation summary")
    assert attestation["wheel_sha256"] == wheel_sha256
    assert attestation["commit_sha"] == COMMIT_SHA
    assert attestation["summary"]["failed"] == 0
    files.download(str(OUTPUT))
else:
    toolkit.show_json({"status": "not-run", "scope": "vllm-attestation"}, title="Attestation gate")"""
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
    "system.agent",
    "agent.run",
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

Con live desactivado: contratos declarativos y estados not-run ejecutables. Con live activado: un RunResult vllm-runtime real y una attestation de native, LangGraph, OpenAI Agents y Strands. Para fine-tuning, entrena y guarda un checkpoint o adapter con Unsloth, cambia MODEL_ID y conserva el resto."""
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
    return nb


def main() -> None:
    notebook = build_notebook()
    for path in (TUTORIAL, ATTESTATION):
        path.parent.mkdir(parents=True, exist_ok=True)
        nbformat.write(copy.deepcopy(notebook), path)
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
