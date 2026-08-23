"""Normalize tutorial metadata and editorial outcome contracts."""

from __future__ import annotations

import ast
import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
TUTORIALS = ROOT / "tutorials"
sys.path.insert(0, str(ROOT / "src"))

import agentic_systems as toolkit  # noqa: E402

SCENARIO_MANIFEST = tuple(toolkit.api_contract()["scenarios"])

CURRICULUM_ORDER = (
    "providers/00_auto.ipynb",
    "providers/02_bedrock.ipynb",
    "providers/01_openai.ipynb",
    "core/00_runtime_scheduler.ipynb",
    "providers/03_vllm.ipynb",
    "providers/04_ollama.ipynb",
    "core/01_tool.ipynb",
    "core/02_skills.ipynb",
    "core/03_agent.ipynb",
    "core/04_results_lineage.ipynb",
    "frameworks/02_aws_strands.ipynb",
    "frameworks/01_openai_agents.ipynb",
    "frameworks/00_langgraph.ipynb",
    "core/05_system.ipynb",
    "core/06_graph_native.ipynb",
    "core/07_environment_eval.ipynb",
    "core/08_single_agentic_system.ipynb",
    "core/09_multi_agentic_system.ipynb",
    "core/10_multi_agent_graph.ipynb",
    "frameworks/03_provider_framework_matrix.ipynb",
    "api/14_api_contract_matrix.ipynb",
)

V2_INSERTIONS = {
    "frameworks/00_langgraph.ipynb",
    "frameworks/03_provider_framework_matrix.ipynb",
    "providers/04_ollama.ipynb",
    "api/14_api_contract_matrix.ipynb",
}


def _source(cell: dict) -> str:
    return "".join(cell.get("source", []))


def _set_source(cell: dict, source: str) -> None:
    cell["source"] = source.splitlines(True)


def _scenario_ids(relative: str) -> list[str]:
    return [
        scenario["id"]
        for scenario in SCENARIO_MANIFEST
        if relative in scenario["notebooks"]
    ]


def _api_coverage(notebook: dict) -> list[str]:
    """Read the one literal api_coverage assignment from notebook code."""

    code = "\n\n".join(
        _source(cell) for cell in notebook["cells"] if cell.get("cell_type") == "code"
    )
    tree = ast.parse(code)
    claims: list[list[str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        is_api_coverage = any(
            isinstance(target, ast.Name) and target.id == "api_coverage"
            for target in targets
        )
        if not is_api_coverage:
            continue
        claims.append(list(ast.literal_eval(node.value)))
    if len(claims) != 1:
        raise ValueError(
            f"Expected exactly one literal api_coverage assignment, found {len(claims)}."
        )
    return claims[0]


def _normalize(relative: str, notebook: dict) -> dict:
    metadata = notebook.setdefault("metadata", {}).setdefault("agentic_systems", {})
    metadata["curriculum_order"] = CURRICULUM_ORDER.index(relative)
    metadata["curriculum_origin"] = (
        "v1.0.7"
        if relative == "providers/03_vllm.ipynb"
        else "2.0"
        if relative in V2_INSERTIONS
        else "v1.1.3"
    )
    metadata["narrative_reviewed"] = "2.1.0"
    metadata["contract_scenarios"] = _scenario_ids(relative)
    metadata["api_coverage"] = _api_coverage(notebook)

    for cell in notebook["cells"]:
        if cell.get("cell_type") != "markdown":
            continue
        source = _source(cell)
        source = source.replace("4 x 4", "5 x 4")
        source = source.replace("4 × 4", "5 × 4")
        source = source.replace("4×4", "5×4")
        _set_source(cell, source)
        if source.startswith("## Resultado esperado"):
            _set_source(
                cell,
                source.replace(
                    "## Resultado esperado",
                    "## Resultado e interpretacion",
                    1,
                ),
            )
        elif source.startswith("## Lo importante"):
            _set_source(
                cell,
                source.replace(
                    "## Lo importante",
                    "## Resultado e interpretacion",
                    1,
                ),
            )

    if relative.startswith("providers/") and relative != "providers/00_auto.ipynb":
        for cell in notebook["cells"]:
            source = _source(cell)
            source = source.replace(
                "muestra un skip estructurado",
                "muestra un estado not-run estructurado",
            )
            source = source.replace(
                "forzar un skip seguro",
                "forzar un estado not-run seguro",
            )
            source = source.replace(
                "skip estructurado",
                "estado not-run estructurado",
            )
            source = source.replace(
                "skip explicito",
                "estado not-run explicito",
            )
            source = source.replace(
                '"status": "skipped"',
                '"status": "not-run"',
            )
            source = source.replace(
                "con engine `vllm-runtime`",
                "cuyo runtime reporta `vllm-runtime`",
            )
            _set_source(cell, source)
        if not any(_source(cell).startswith("## 3)") for cell in notebook["cells"]):
            raise ValueError(
                f"Provider tutorial {relative} has no section 3 execution gate."
            )

    if relative == "providers/02_bedrock.ipynb":
        _set_source(
            notebook["cells"][0],
            """# Providers 02 - Bedrock Runtime

Objetivo: comprobar `bedrock-runtime` mediante la misma fachada publica usada
por otros providers y distinguir sus dos rutas de autenticacion.

**Lugar en el modelo:** Bedrock es el Provider (donde corre la inferencia);
credenciales, region y modelo son configuracion, no logica del Agent.

**Evidencia exigida:** con configuracion valida, la ejecucion debe producir un
`RunResult` exitoso con `engine="bedrock-runtime"`; sin ella debe reportar
`not-run` con motivo.

**Límite de la evidencia:** el snapshot prueba deteccion local, no permisos ni
inferencia. Solo una fila `passed` contiene evidencia live.
""",
        )
        _set_source(
            notebook["cells"][1],
            """## Parametros de la demostracion

| Variable | Default | Proposito |
|---|---|---|
| RUN_BEDROCK_LIVE | 1 | Usa 0 para desactivar la llamada real. |
| BEDROCK_MODEL_ID | provider default | Modelo habilitado en la cuenta y region. |
| AWS_REGION o AWS_DEFAULT_REGION | us-east-1 | Region de Bedrock. |
| cadena AWS estandar | auto | ADA, perfil, rol/ARN, web identity o credenciales temporales SigV4. |
| AWS_BEARER_TOKEN_BEDROCK | sin valor | API key temporal nativa de Bedrock fuera o dentro de AWS. |

### Dos rutas, un solo Provider

- **ADA/IAM/ARN:** boto3 resuelve la cadena AWS normal, firma con SigV4 y puede
  consultar identidad STS cuando la politica lo permite.
- **API key temporal:** boto3 lee `AWS_BEARER_TOKEN_BEDROCK` y autentica la
  llamada Bedrock como Bearer. Esa credencial es regional, dura como maximo la
  sesion temporal (hasta 12 horas) y no autentica STS.
- Si ambas señales estan presentes, Agentic Systems reporta
  `authentication_mode="bedrock-api-key"` y no intenta `GetCallerIdentity`.
- Las dos rutas convergen en `bedrock-runtime` y deben producir el mismo
  contrato `RunResult`.
""",
        )
        preflight = notebook["cells"][3]
        preflight_code = _source(preflight)
        if "AUTH_MODE =" not in preflight_code:
            preflight_code = preflight_code.replace(
                'HAS_BEARER = bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK"))\n',
                'HAS_BEARER = bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK"))\n'
                'AUTH_MODE = aws_session.get("authentication_mode")\n'
                'assert AUTH_MODE in {None, "aws-credential-chain", "bedrock-api-key"}\n',
            )
        _set_source(preflight, preflight_code)
        _set_source(
            notebook["cells"][8],
            """## 3) Ejecutar o reportar not-run

La llamada live esta habilitada por defecto cuando existe region y una de las
dos rutas de autenticacion. En ADA se espera la cadena AWS/rol; fuera de AWS se
puede usar la API key temporal. Usa `RUN_BEDROCK_LIVE=0` para forzar
`not-run`. Errores de permisos, region, expiracion o modelo permanecen
visibles.
""",
        )
        _set_source(
            notebook["cells"][-1],
            """## Resultado e interpretacion

Con live desactivado: snapshot seguro, modo de autenticacion y configuracion
observable. Con live activado: un `RunResult` real cuyo runtime reporta
`bedrock-runtime`. El modo API key no promete identidad STS; el modo
IAM/ARN si puede reportarla, pero ambos conservan el mismo contrato de
ejecucion y nunca exponen secretos.
""",
        )

    if relative == "frameworks/03_provider_framework_matrix.ipynb":
        for cell in notebook["cells"]:
            source = _source(cell)
            source = source.replace("16", "20")
            source = source.replace("doce externas", "dieciseis externas")
            source = source.replace("4 x 4", "5 x 4")
            source = source.replace("4 × 4", "5 × 4")
            source = source.replace("4×4", "5×4")
            _set_source(cell, source)

        execution = notebook["cells"][5]
        code = _source(execution)
        code = code.replace(
            'matrix_results.append({**case.to_dict(), "execution": "skipped"})',
            "matrix_results.append({\n"
            "            **case.to_dict(),\n"
            '            "execution": "not-run",\n'
            '            "execution_reason": (\n'
            '                case.reason if not case.ready else "RUN_MATRIX_LIVE=0"\n'
            "            ),\n"
            "        })",
        )
        _set_source(execution, code)
        if not any(
            _source(cell).startswith("## Resultado e interpretacion")
            for cell in notebook["cells"]
        ):
            notebook["cells"].append(
                {
                    "cell_type": "markdown",
                    "id": "matrix-outcome",
                    "metadata": {},
                    "source": [
                        "## Resultado e interpretacion\n",
                        "\n",
                        "Cada fila conserva provider, framework, readiness y ejecucion. ",
                        "passed exige un RunResult real y ok; not-run conserva el motivo ",
                        "y nunca demuestra compatibilidad live. failed mantiene visible ",
                        "el error del cruce ejecutado.\n",
                    ],
                }
            )

    return notebook


def update(*, check: bool) -> int:
    drift: list[str] = []
    for relative in CURRICULUM_ORDER:
        if relative.startswith("api/"):
            continue
        path = TUTORIALS / relative
        notebook = json.loads(path.read_text(encoding="utf-8"))
        normalized = _normalize(relative, notebook)
        content = json.dumps(normalized, indent=1, ensure_ascii=False) + "\n"
        current = path.read_text(encoding="utf-8")
        if current == content:
            continue
        if check:
            drift.append(relative)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"updated {relative}")
    if drift:
        print("Tutorial contract drift:")
        for relative in drift:
            print(f"- {relative}")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    return update(check=parser.parse_args().check)


if __name__ == "__main__":
    raise SystemExit(main())
