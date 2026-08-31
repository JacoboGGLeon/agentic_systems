"""Generate the concise public vLLM provider tutorial."""

from __future__ import annotations

from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tutorials" / "providers" / "03_vllm.ipynb"


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
                "toolkit.show_json",
                "toolkit.vllm_environment_snapshot",
                "toolkit.RunResult",
                "toolkit.AgentContract",
                "toolkit.RunPolicy",
            ],
            "contract_scenarios": scenarios,
            "curriculum_order": 4,
            "curriculum_origin": "v1.0.7",
            "execution_mode": "live-optional",
            "framework": "native",
            "layer": "providers",
            "narrative_reviewed": "2.1.1",
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
    notebook = nbformat.v4.new_notebook(metadata=_metadata())
    notebook.cells = [
        nbformat.v4.new_markdown_cell(
            """# Provider vLLM: Unsloth + Qwen

Objetivo: ejecutar el mismo contrato Agent/System/Tool con `vllm-runtime`. El
notebook enseña la API pública; la instalación CUDA y la certificación exhaustiva
pertenecen al kit Colab/release.

**Lugar en el modelo:** vLLM es el Provider de inferencia; `ModelServer`
administra infraestructura y Agent/System conservan la lógica agéntica.

**Evidencia exigida:** el servidor queda healthy, Qwen llama `multiply`, el
`RunResult` conserva `engine="vllm-runtime"` y pasa invariantes.

**Límite de la evidencia:** `RUN_VLLM_LIVE=0` sólo prueba construcción y `not-run`.
La matriz de cuatro frameworks se certifica en el notebook de attestation.

Prerequisito: instala el wheel y los extras `vllm-server`, `langgraph`,
`openai-agents` y `strands` en un kernel GPU aislado. `.env` es la fuente canónica."""
        ),
        nbformat.v4.new_markdown_cell(
            """## Parametros de la demostracion

El ejemplo probado usa `unsloth/Qwen3-4B-Instruct-2507`, parser Hermes y modo non-thinking.
Los perfiles `fast`, `medium`, `power` y `custom` permanecen configurables."""
        ),
        nbformat.v4.new_code_cell(
            """import json
import os
from pathlib import Path

import agentic_systems as toolkit

# Carga la .env más cercana sin sobrescribir variables del proceso.
toolkit.vllm_environment_snapshot()

RUN_VLLM_LIVE = os.getenv("RUN_VLLM_LIVE", "1").lower() in {"1", "true", "yes"}
MODEL_ID = os.getenv("VLLM_MODEL", "unsloth/Qwen3-4B-Instruct-2507")
BASE_MODEL_ID = os.getenv("VLLM_BASE_MODEL", "Qwen/Qwen3-4B-Instruct-2507")
PROFILE = os.getenv("VLLM_PROFILE", "fast")
HOST = os.getenv("VLLM_HOST", "127.0.0.1")
PORT = int(os.getenv("VLLM_PORT", "8000"))
BASE_URL = os.getenv("VLLM_BASE_URL", f"http://{HOST}:{PORT}/v1")
API_KEY = os.getenv("VLLM_API_KEY", "vllm")
TEMPERATURE = float(os.getenv("VLLM_TEMPERATURE", "0.7"))
ENABLE_THINKING = os.getenv("VLLM_ENABLE_THINKING", "0") == "1"
"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 1) Artefacto, servidor y runtime

`ModelArtifact` conserva la relación entre el modelo servido y su base. Sustituir
el artefacto por un checkpoint fine-tuned o LoRA no cambia Agent/System."""
        ),
        nbformat.v4.new_code_cell(
            """artifact = toolkit.model_artifact(
    MODEL_ID,
    base_model=BASE_MODEL_ID,
    metadata={"serving_library": "unsloth"},
)
server = toolkit.model_server(
    artifact,
    profile=PROFILE,
    host=HOST,
    port=PORT,
    gpu_memory_utilization=float(os.getenv("VLLM_GPU_MEMORY_UTILIZATION", "0.4")),
    max_model_len=int(os.getenv("VLLM_MAX_MODEL_LEN", "2048")),
    max_num_seqs=int(os.getenv("VLLM_MAX_NUM_SEQS", "4")),
    tool_call_parser=os.getenv("VLLM_TOOL_CALL_PARSER", "hermes"),
    reasoning_parser=(os.getenv("VLLM_REASONING_PARSER") or None),
    extra_args=(
        "--dtype", os.getenv("VLLM_DTYPE", "half"),
        "--default-chat-template-kwargs",
        json.dumps({"enable_thinking": ENABLE_THINKING}),
    ),
    startup_timeout_s=600,
    log_path=os.getenv("VLLM_LOG_PATH", "/content/vllm-server.log"),
)
toolkit.show_json(server.inspect(), title="vLLM ModelServer")

if RUN_VLLM_LIVE:
    endpoint = server.start()
    health = server.health()
    assert health.status == "healthy", Path(server.spec.log_path).read_text(errors="replace")
    runtime = server.runtime(metadata={"tutorial": "providers/03_vllm"})
else:
    endpoint = None
    runtime = toolkit.runtime(
        provider="vllm-runtime",
        model=MODEL_ID,
        endpoint=BASE_URL,
        metadata={"tutorial": "providers/03_vllm", "live": False},
    )
"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 2) Agent con Tool

La Tool demuestra el camino relevante: solicitud del modelo, ejecución
determinista y proyección normalizada común a todos los providers."""
        ),
        nbformat.v4.new_code_cell(
            """@toolkit.tool
def multiply(a: int, b: int) -> dict:
    return {"result": a * b}

system = toolkit.system(runtime=runtime)
agent = system.agent(
    name="qwen_calculator",
    instructions="Usa multiply para calcular y devuelve el resultado.",
    tools=[multiply],
    contract=toolkit.AgentContract(
        must_call=["multiply"],
        completion="when_required_tools_satisfied",
    ),
    policy=toolkit.RunPolicy(
        max_turns=3,
        max_tool_calls=1,
        temperature=TEMPERATURE,
        tool_choice="multiply",
    ),
)

if RUN_VLLM_LIVE:
    result = agent.run("¿Cuánto es 17 por 19?", mode="eval")
    assert isinstance(result, toolkit.RunResult)
    assert result.ok, result.errors
    assert result.engine == "vllm-runtime"
    assert [event.name for event in result.tool_events] == ["multiply"]
    result.check_invariants()
    toolkit.human_result(result, title="vLLM RunResult", show_lineage=True)
    toolkit.show_json(toolkit.run_result_output(result), title="Contrato normalizado")
else:
    result = None
    toolkit.show_json(
        {"status": "not-run", "provider": "vllm-runtime", "reason": "RUN_VLLM_LIVE=0"},
        title="vLLM live gate",
    )
"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 3) Cierre del servidor

El servidor se cierra sólo si este notebook lo inició. La attestation exhaustiva
vive separada del recorrido pedagógico."""
        ),
        nbformat.v4.new_code_cell(
            """api_coverage = [
    "toolkit.model_artifact", "toolkit.model_server", "server.inspect",
    "server.start", "server.health", "server.runtime", "server.stop",
    "toolkit.runtime", "toolkit.tool", "toolkit.system", "system.agent",
    "agent.run", "toolkit.human_result", "toolkit.run_result_output",
    "toolkit.show_json", "toolkit.vllm_environment_snapshot", "toolkit.RunResult",
    "toolkit.AgentContract", "toolkit.RunPolicy",
]
toolkit.show_json(api_coverage, title="vLLM API coverage")

if RUN_VLLM_LIVE:
    server.stop()
    toolkit.show_json({"status": "stopped", "owned_process_only": True})
"""
        ),
        nbformat.v4.new_markdown_cell(
            """## Resultado e interpretacion

La prueba termina cuando la Tool devuelve 323, `engine` conserva
`vllm-runtime` y el `RunResult` pasa invariantes."""
        ),
    ]
    for index, cell in enumerate(notebook.cells):
        cell["id"] = f"vllm-tutorial-{index:02d}"
    return notebook


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(build_notebook(), OUTPUT)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
