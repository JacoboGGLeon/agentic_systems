"""Generate the Ollama provider tutorial and the parallel CLI curriculum."""

from __future__ import annotations
import argparse

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TUTORIALS = ROOT / "tutorials"
CLI_ROOT = TUTORIALS / "cli"


def _cell(kind: str, source: str, identifier: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "cell_type": kind,
        "id": identifier,
        "metadata": {},
        "source": source.splitlines(True),
    }
    if kind == "code":
        payload.update(execution_count=None, outputs=[])
    return payload


def _notebook(cells: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "cells": cells,
        "metadata": {
            "agentic_systems": metadata,
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


OLLAMA_CELLS = [
    _cell(
        "markdown",
        """# Providers 04 - Ollama Runtime

Objetivo: ejecutar un modelo local cuantizado mediante `ollama-runtime` y la
misma fachada pública que OpenAI, Bedrock y vLLM.

**Lugar en el modelo:** Ollama es el Provider local; el Agent y su Framework no
cambian. Agentic Systems no instala Ollama, no descarga modelos y no administra
el proceso del servidor.

**Evidencia exigida:** una prueba live produce `RunResult.ok=True` y
`engine="ollama-runtime"`. Un preflight o un contrato offline no demuestra que
el modelo respondió.

**Límite de la evidencia:** `not-run` sólo demuestra que el tutorial conserva
su contrato sin infraestructura; no certifica servidor, GPU, modelo ni tool
calling.
""",
        "ollama-title",
    ),
    _cell(
        "markdown",
        """## Parametros de la demostracion

| Variable | Default | Propósito |
|---|---|---|
| RUN_OLLAMA_LIVE | 1 | Usa 0 para desactivar la llamada real. |
| OLLAMA_MODEL | qwen3:4b-instruct | Modelo recomendado para agentes y tool use. |
| OLLAMA_BASE_URL | http://127.0.0.1:11434/v1 | Endpoint OpenAI-compatible. |
| OLLAMA_API_KEY | ollama | Valor local convencional; nunca se imprime. |

Para una GPU de 8 GB empieza con un modelo pequeño o cuantizado. La elección
exacta es operativa y puede cambiar sin modificar la API del Agent.
""",
        "ollama-params",
    ),
    _cell(
        "markdown",
        """## Contrato de la demostración

```text
toolkit.runtime -> toolkit.system -> system.agent -> RunResult
```

La ruta es idéntica a otros providers. Sólo cambian configuración, modelo y
evidencia operativa.
""",
        "ollama-contract",
    ),
    _cell(
        "code",
        """import os

import agentic_systems as toolkit

ollama_environment = toolkit.ollama_environment_snapshot()

RUN_OLLAMA_LIVE = os.getenv("RUN_OLLAMA_LIVE", "1").strip().lower() in {
    "1", "true", "yes"
}
MODEL = os.getenv("OLLAMA_MODEL") or "qwen3:4b-instruct"
AGENT_NAME = "ollama_public_api_probe"

toolkit.show_json(
    {
        "package": toolkit.__name__,
        "version": toolkit.__version__,
        "run_live": RUN_OLLAMA_LIVE,
        "environment": ollama_environment,
    },
    title="Preflight Ollama",
)
""",
        "ollama-preflight",
    ),
    _cell(
        "markdown",
        """## 1) Declarar runtime y límites

El endpoint por defecto apunta al servidor local oficial. Configurar una URL no
inicia el servidor ni garantiza que el modelo exista.
""",
        "ollama-runtime-md",
    ),
    _cell(
        "code",
        """scheduler = toolkit.scheduler(
    timeout_s=120,
    max_retries=0,
    max_tool_calls=1,
    max_turns=3,
    max_concurrency=1,
)

runtime = toolkit.runtime(
    provider="ollama-runtime",
    model=MODEL,
    scheduler=scheduler,
    metadata={"tutorial": "providers/ollama"},
)

toolkit.show_json(runtime.describe(), title="Ollama RuntimeConfig")
""",
        "ollama-runtime-code",
    ),
    _cell(
        "markdown",
        """## 2) Crear system, tool y agent

La Tool y el Agent no importan el SDK de Ollama. El provider conserva la
identidad `ollama-runtime` aunque use transporte OpenAI-compatible.
""",
        "ollama-agent-md",
    ),
    _cell(
        "code",
        """@toolkit.tool
def inspect_public_api(symbol: str) -> dict:
    '''Verifica un símbolo contra la superficie pública instalada.'''
    return {
        "symbol": symbol,
        "is_public": symbol in toolkit.__all__,
        "package_version": toolkit.__version__,
    }

system = toolkit.system(runtime=runtime)
agent = system.agent(
    name=AGENT_NAME,
    instructions=(
        "Usa inspect_public_api para verificar el símbolo solicitado. "
        "Responde con el nombre, si es público y la versión observada."
    ),
    tools=[inspect_public_api],
    contract=toolkit.AgentContract(
        must_call=["inspect_public_api"],
        completion="when_required_tools_satisfied",
    ),
    policy=toolkit.RunPolicy(
        max_turns=3,
        max_tool_calls=1,
        temperature=0.0,
        trace="compact",
        strict=True,
    ),
)

toolkit.show_json(agent.info(), title="Agente declarado")
""",
        "ollama-agent-code",
    ),
    _cell(
        "markdown",
        """## 3) Ejecutar o reportar not-run

La ejecución live requiere una señal explícita de Ollama. Usa
`RUN_OLLAMA_LIVE=0` para conservar un tutorial offline reproducible.
""",
        "ollama-run-md",
    ),
    _cell(
        "code",
        """can_run = RUN_OLLAMA_LIVE and bool(
    os.getenv("OLLAMA_MODEL") or os.getenv("OLLAMA_BASE_URL")
)

if can_run:
    result = agent.run(
        "Verifica si system pertenece a la API pública instalada.",
        mode="eval",
    )
    assert isinstance(result, toolkit.RunResult)
    assert result.ok, result.errors
    assert result.engine == "ollama-runtime"
    toolkit.human_result(result, title="Ollama RunResult", show_lineage=True)
    toolkit.show_json(
        toolkit.run_result_output(result),
        title="Contrato normalizado",
    )
else:
    result = None
    toolkit.show_json(
        {
            "status": "not-run",
            "provider": "ollama-runtime",
            "reason": (
                "Configura OLLAMA_MODEL u OLLAMA_BASE_URL, "
                "o usa RUN_OLLAMA_LIVE=0."
            ),
        },
        title="Ollama live gate",
    )
""",
        "ollama-run-code",
    ),
    _cell(
        "markdown",
        """## 4) API realmente ejercitada

El preflight, la declaración y la ejecución usan exclusivamente la superficie
pública.
""",
        "ollama-coverage-md",
    ),
    _cell(
        "code",
        """api_coverage = [
    "toolkit.ollama_environment_snapshot",
    "toolkit.scheduler",
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

toolkit.show_json(api_coverage, title="Ollama API coverage")
""",
        "ollama-coverage-code",
    ),
    _cell(
        "markdown",
        """## Resultado e interpretacion

`not-run` prueba que el tutorial es seguro sin infraestructura. Sólo el bloque
live exitoso demuestra servidor, modelo, tool calling y normalización
`RunResult` de Ollama.
""",
        "ollama-outcome",
    ),
]


CLI_BOOTSTRAP = """from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("No se encontró la raíz del repositorio.")


ROOT = _repo_root()
CLI = [sys.executable, "-m", "agentic_systems.cli"]


def run_cli(*args: str, expected: int = 0) -> str:
    env = os.environ.copy()
    source_path = str(ROOT / "src")
    env["PYTHONPATH"] = (
        source_path
        if not env.get("PYTHONPATH")
        else source_path + os.pathsep + env["PYTHONPATH"]
    )
    command = [*CLI, *args]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    print("$ " + " ".join(command))
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="")
    assert completed.returncode == expected, completed.stderr
    return completed.stdout


def run_cli_json(*args: str) -> dict:
    return json.loads(run_cli(*args, "--json"))


def assert_rich(output: str, title: str) -> None:
    assert title in output
    ascii_box = "+" in output and "|" in output
    unicode_box = "─" in output and "│" in output
    assert ascii_box or unicode_box
"""


CURRICULUM = (
    {
        "path": "providers/00_auto.ipynb",
        "python": "providers/00_auto.ipynb",
        "title": "Providers 00 - Auto (CLI)",
        "concept": "Resolver automáticamente el primer Provider listo.",
        "rich": ("doctor",),
        "rich_title": "Agentic Systems Doctor",
        "json": ("runtime", "--provider", "auto", "--allow-python-fallback"),
        "assertion": 'assert payload["selected_provider"] in {"python-runtime", "openai-runtime", "ollama-runtime", "vllm-runtime", "bedrock-runtime"}',
    },
    {
        "path": "providers/02_bedrock.ipynb",
        "python": "providers/02_bedrock.ipynb",
        "title": "Providers 02 - Bedrock (CLI)",
        "concept": "Inspeccionar readiness y los cuatro cruces Framework de Bedrock.",
        "rich": ("doctor",),
        "rich_title": "Agentic Systems Doctor",
        "matrix_provider": "bedrock-runtime",
    },
    {
        "path": "providers/01_openai.ipynb",
        "python": "providers/01_openai.ipynb",
        "title": "Providers 01 - OpenAI (CLI)",
        "concept": "Inspeccionar readiness y los cuatro cruces Framework de OpenAI.",
        "rich": ("doctor",),
        "rich_title": "Agentic Systems Doctor",
        "matrix_provider": "openai-runtime",
    },
    {
        "path": "core/00_runtime_scheduler.ipynb",
        "python": "core/00_runtime_scheduler.ipynb",
        "title": "Core 00 - Runtime y Scheduler (CLI)",
        "concept": "Declarar y observar la resolución del Runtime.",
        "rich": ("runtime", "--provider", "python-runtime"),
        "rich_title": "Runtime Resolution",
        "json": ("runtime", "--provider", "python-runtime"),
        "assertion": 'assert payload["selected_provider"] == "python-runtime"',
    },
    {
        "path": "providers/03_vllm.ipynb",
        "python": "providers/03_vllm.ipynb",
        "title": "Providers 03 - vLLM (CLI)",
        "concept": "Inspeccionar readiness y los cuatro cruces Framework de vLLM.",
        "rich": ("doctor",),
        "rich_title": "Agentic Systems Doctor",
        "matrix_provider": "vllm-runtime",
    },
    {
        "path": "providers/04_ollama.ipynb",
        "python": "providers/04_ollama.ipynb",
        "title": "Providers 04 - Ollama (CLI)",
        "concept": "Inspeccionar readiness y los cuatro cruces Framework de Ollama.",
        "rich": ("doctor",),
        "rich_title": "Agentic Systems Doctor",
        "matrix_provider": "ollama-runtime",
    },
    {
        "path": "core/01_tool.ipynb",
        "python": "core/01_tool.ipynb",
        "title": "Core 01 - Tool (CLI)",
        "concept": "Ejecutar una Tool determinista y observar RunResult.",
        "rich": ("tool", "run", "--value", "cli"),
        "rich_title": "Tool Workflow",
        "json": ("tool", "run", "--value", "cli"),
        "assertion": 'assert payload["result"]["ok"] is True',
    },
    {
        "path": "core/02_skills.ipynb",
        "python": "core/02_skills.ipynb",
        "title": "Core 02 - Skill (CLI)",
        "concept": "Construir e inspeccionar una Skill.",
        "rich": ("skill", "inspect"),
        "rich_title": "Skill Workflow",
        "json": ("skill", "inspect"),
        "assertion": 'assert "cli_echo_skill" in payload["skill"]',
    },
    {
        "path": "core/03_agent.ipynb",
        "python": "core/03_agent.ipynb",
        "title": "Core 03 - Agent (CLI)",
        "concept": "Ejecutar una unidad de cómputo Agent.",
        "rich": ("agent", "run", "--value", "cli"),
        "rich_title": "Agent Workflow",
        "json": ("agent", "run", "--value", "cli"),
        "assertion": 'assert payload["result"]["engine"] == "python-runtime"',
    },
    {
        "path": "core/04_results_lineage.ipynb",
        "python": "core/04_results_lineage.ipynb",
        "title": "Core 04 - Resultados y Lineage (CLI)",
        "concept": "Observar el contrato normalizado de un resultado.",
        "rich": ("agent", "run", "--value", "lineage"),
        "rich_title": "Agent Workflow",
        "json": ("agent", "run", "--value", "lineage"),
        "assertion": 'assert payload["result"]["ok"] is True and "tool_outputs" in payload["result"]',
    },
    {
        "path": "frameworks/02_aws_strands.ipynb",
        "python": "frameworks/02_aws_strands.ipynb",
        "title": "Frameworks 02 - Strands (CLI)",
        "concept": "Inspeccionar Strands sobre los cinco Providers.",
        "rich": ("matrix", "check", "--framework", "strands"),
        "rich_title": "Matrix Workflow",
        "matrix_framework": "strands",
    },
    {
        "path": "frameworks/01_openai_agents.ipynb",
        "python": "frameworks/01_openai_agents.ipynb",
        "title": "Frameworks 01 - OpenAI Agents (CLI)",
        "concept": "Inspeccionar OpenAI Agents sobre los cinco Providers.",
        "rich": ("matrix", "check", "--framework", "openai-agents"),
        "rich_title": "Matrix Workflow",
        "matrix_framework": "openai-agents",
    },
    {
        "path": "frameworks/00_langgraph.ipynb",
        "python": "frameworks/00_langgraph.ipynb",
        "title": "Frameworks 00 - LangGraph (CLI)",
        "concept": "Inspeccionar LangGraph sobre los cinco Providers.",
        "rich": ("matrix", "check", "--framework", "langgraph"),
        "rich_title": "Matrix Workflow",
        "matrix_framework": "langgraph",
    },
    {
        "path": "core/05_system.ipynb",
        "python": "core/05_system.ipynb",
        "title": "Core 05 - System (CLI)",
        "concept": "Compilar y ejecutar un System.",
        "rich": ("system", "run", "--value", "cli"),
        "rich_title": "System Workflow",
        "json": ("system", "run", "--value", "cli"),
        "assertion": 'assert payload["result"]["ok"] is True',
    },
    {
        "path": "core/06_graph_native.ipynb",
        "python": "core/06_graph_native.ipynb",
        "title": "Core 06 - Graph (CLI)",
        "concept": "Construir y ejecutar un Graph portable.",
        "rich": ("graph", "run", "--value", "cli"),
        "rich_title": "Graph Workflow",
        "json": ("graph", "run", "--value", "cli"),
        "assertion": 'assert payload["state"]["visited"] is True',
    },
    {
        "path": "core/07_environment_eval.ipynb",
        "python": "core/07_environment_eval.ipynb",
        "title": "Core 07 - Environment y Eval (CLI)",
        "concept": "Ejecutar un episodio y evaluar un Executable.",
        "rich": ("environment", "run", "--value", "cli"),
        "rich_title": "Environment Workflow",
        "json": ("eval", "run", "--value", "cli"),
        "assertion": 'assert payload["report"]["ok"] is True',
    },
    {
        "path": "core/08_single_agentic_system.ipynb",
        "python": "core/08_single_agentic_system.ipynb",
        "title": "Core 08 - Single Agentic System (CLI)",
        "concept": "Observar el caso mínimo donde Agent y System coinciden.",
        "rich": ("system", "run", "--value", "single"),
        "rich_title": "System Workflow",
        "json": ("system", "run", "--value", "single"),
        "assertion": 'assert payload["result"]["ok"] is True',
    },
    {
        "path": "core/09_multi_agentic_system.ipynb",
        "python": "core/09_multi_agentic_system.ipynb",
        "title": "Core 09 - Multi Agentic System (CLI)",
        "concept": "Relacionar composición de System con sus contratos públicos.",
        "rich": ("api", "list", "--contains", "System"),
        "rich_title": "API Inventory",
        "json": ("api", "list", "--contains", "System"),
        "assertion": 'assert payload["count"] > 0',
    },
    {
        "path": "core/10_multi_agent_graph.ipynb",
        "python": "core/10_multi_agent_graph.ipynb",
        "title": "Core 10 - Multi Agent Graph (CLI)",
        "concept": "Relacionar Graph y Agent con sus contratos públicos.",
        "rich": ("api", "list", "--contains", "Graph"),
        "rich_title": "API Inventory",
        "json": ("api", "list", "--contains", "Graph"),
        "assertion": 'assert payload["count"] > 0',
    },
    {
        "path": "frameworks/03_provider_framework_matrix.ipynb",
        "python": "frameworks/03_provider_framework_matrix.ipynb",
        "title": "Frameworks 03 - Matriz Provider × Framework (CLI)",
        "concept": "Inspeccionar las veinte combinaciones y su evidencia.",
        "rich": ("matrix", "check"),
        "rich_title": "Matrix Workflow",
        "matrix_all": True,
    },
    {
        "path": "api/14_api_contract_matrix.ipynb",
        "python": "api/14_api_contract_matrix.ipynb",
        "title": "API 14 - Contrato público (CLI)",
        "concept": "Listar y ejercitar el inventario de contratos públicos.",
        "rich": ("api", "list", "--tier", "public"),
        "rich_title": "API Inventory",
        "json": ("api", "list", "--tier", "public"),
        "assertion": 'assert payload["count"] >= 300',
    },
)


def _matrix_code(entry: dict[str, Any]) -> str:
    args = ["matrix", "check"]
    expected = 20
    if entry.get("matrix_provider"):
        args.extend(["--provider", entry["matrix_provider"]])
        expected = 4
    if entry.get("matrix_framework"):
        args.extend(["--framework", entry["matrix_framework"]])
        expected = 5
    args_literal = repr(args)
    return f"""args = {args_literal}
live_flag = os.getenv("RUN_CLI_LIVE", "0").strip().lower() in {{"1", "true", "yes"}}
if live_flag:
    args.append("--live")
    args.append("--require-pass")
payload = run_cli_json(*args)

assert payload["combination_count"] == {expected}
assert payload["failed"] == 0
assert len(payload["results"]) == {expected}
if live_flag:
    assert payload["passed"] == {expected}
payload
"""


def _json_code(entry: dict[str, Any]) -> str:
    if entry.get("matrix_provider") or entry.get("matrix_framework") or entry.get("matrix_all"):
        return _matrix_code(entry)
    args = repr(list(entry["json"]))
    assertion = entry["assertion"]
    return f"""payload = run_cli_json(*{args})
{assertion}
payload
"""


def _cli_notebook(entry: dict[str, Any], order: int) -> dict[str, Any]:
    rich_args = repr(list(entry["rich"]))
    rich_code = f"""rich_output = run_cli(*{rich_args})
assert_rich(rich_output, {entry["rich_title"]!r})
"""
    cells = [
        _cell(
            "markdown",
            f"""# {entry["title"]}

Notebook CLI paralelo a `tutorials/{entry["python"]}`.

**Objetivo:** {entry["concept"]}

Este notebook no llama factories de Agentic Systems directamente: ejecuta el
entrypoint CLI real, conserva la salida Rich y valida después el JSON del mismo
contrato.
""",
            f"cli-title-{order}",
        ),
        _cell(
            "markdown",
            """## Cómo se ejecuta

La forma portable es `python -m agentic_systems.cli ...`. Después de instalar
el wheel, el entrypoint equivalente es `agentic-systems ...`.
""",
            f"cli-command-{order}",
        ),
        _cell("code", CLI_BOOTSTRAP, f"cli-bootstrap-{order}"),
        _cell(
            "markdown",
            """## 1) Salida humana Rich

La celda conserva stdout y comprueba título y bordes. Esto detecta tablas o
paneles truncados, además del exit code.
""",
            f"cli-rich-md-{order}",
        ),
        _cell("code", rich_code, f"cli-rich-code-{order}"),
        _cell(
            "markdown",
            """## 2) Contrato de máquina

La misma ruta se ejecuta con `--json` para afirmar campos y cardinalidad sin
parsear la presentación Rich.
""",
            f"cli-json-md-{order}",
        ),
        _cell("code", _json_code(entry), f"cli-json-code-{order}"),
        _cell(
            "markdown",
            """## Resultado e interpretación

Rich responde a lectura humana; JSON responde a automatización. Ambos nacen del
mismo comando y del mismo escenario público. Un estado `not-run` conserva el
motivo, pero no cuenta como evidencia live.
""",
            f"cli-outcome-{order}",
        ),
    ]
    return _notebook(
        cells,
        {
            "cli_curriculum": True,
            "curriculum_order": order,
            "python_notebook": entry["python"],
            "rich_output_required": True,
            "outputs_preserved": True,
        },
    )


def _write(path: Path, notebook: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(notebook, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(path.relative_to(ROOT))


def _ollama_notebook() -> dict[str, Any]:
    return _notebook(
        OLLAMA_CELLS,
        {
            "curriculum_origin": "2.0",
            "curriculum_order": 5,
            "narrative_reviewed": "2.0.0",
            "contract_scenarios": ["runtime"],
            "layer": "providers",
            "provider": "ollama-runtime",
            "framework": "native",
            "execution_mode": "live-optional",
            "api_coverage": [
                "toolkit.ollama_environment_snapshot",
                "toolkit.scheduler",
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
        },
    )


def _outputs() -> list[tuple[Path, dict[str, Any], bool]]:
    outputs = [
        (
            TUTORIALS / "providers" / "04_ollama.ipynb",
            _ollama_notebook(),
            False,
        )
    ]
    outputs.extend(
        (CLI_ROOT / entry["path"], _cli_notebook(entry, order), True)
        for order, entry in enumerate(CURRICULUM)
    )
    return outputs


def _contract_view(notebook: dict[str, Any], *, cli: bool) -> dict[str, Any]:
    if not cli:
        return notebook
    return {
        "cells": [
            {
                "cell_type": cell["cell_type"],
                "id": cell["id"],
                "source": cell["source"],
            }
            for cell in notebook["cells"]
        ],
        "metadata": {
            "agentic_systems": notebook["metadata"]["agentic_systems"],
        },
        "nbformat": notebook["nbformat"],
        "nbformat_minor": notebook["nbformat_minor"],
    }

def _preserve_cli_outputs(path: Path, notebook: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return notebook

    actual = json.loads(path.read_text(encoding="utf-8"))
    actual_by_id = {
        cell.get("id"): cell
        for cell in actual.get("cells", [])
        if cell.get("cell_type") == "code" and cell.get("id")
    }
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        previous = actual_by_id.get(cell.get("id"))
        if previous is None:
            continue
        cell["execution_count"] = previous.get("execution_count")
        cell["outputs"] = previous.get("outputs", [])
    return notebook



def generate(*, check: bool = False) -> int:
    drift: list[Path] = []
    for path, expected, cli in _outputs():
        if check:
            if not path.exists():
                drift.append(path)
                continue
            actual = json.loads(path.read_text(encoding="utf-8"))
            if _contract_view(actual, cli=cli) != _contract_view(expected, cli=cli):
                drift.append(path)
            continue
        if cli:
            expected = _preserve_cli_outputs(path, expected)
        _write(path, expected)

    if drift:
        print("CLI tutorial drift:")
        for path in drift:
            print(f"- {path.relative_to(ROOT)}")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check source and metadata without changing preserved CLI outputs.",
    )
    return generate(check=parser.parse_args().check)


if __name__ == "__main__":
    raise SystemExit(main())
