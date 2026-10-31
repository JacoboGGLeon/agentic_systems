"""Reconcile saved learning evidence without inference or rewriting past attempts."""

import ast
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "revisions/2.1.4/learning-dev3"
DOCS = ROOT / "docs"
sys.path[:0] = [str(ROOT / ".tmp/candidate214-dev3/site-packages")]
import agentic_systems as toolkit  # noqa: E402

WHEEL_HASH = "83cf3dca623e57d335b02136e70e9fe13dc5dd0ffbc0cc633b8cdcbda430aab9"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def posix(value):
    return str(value).replace("\\", "/")


def link(path, origin=DOCS):
    import os

    return posix(os.path.relpath(path, origin))


def md(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


assert toolkit.__version__ == "2.1.4.dev3"
assert (
    hashlib.sha256(
        (
            ROOT
            / "revisions/2.1.4/json-markdown-fix/candidate/agentic_systems-2.1.4.dev3-py3-none-any.whl"
        ).read_bytes()
    ).hexdigest()
    == WHEEL_HASH
)
examples = read(E / "examples-offline.json")
assert examples["offline_guard_blocked_attempts"] == 0
assert all(r["passed"] is not False for r in examples["rows"])
offline = {}
profiles = {}
for result in sorted((E / "notebook-runs").glob("*/results.json")):
    for row in read(result):
        row = {**row, "results_file": posix(result.relative_to(ROOT))}
        profiles[(row["path"], row["profile"], row["framework"])] = row
        if row["profile"] == "offline":
            offline[row["path"]] = row
assert len(offline) == 26 and all(r["passed"] for r in offline.values())

# Reconcile attempts by exact case identity. Never discard original result files.
attempts = []
latest = {}
for result in sorted((E / "live-runs").glob("*/results.json")):
    for index, row in enumerate(read(result)["rows"]):
        item = {**row, "evidence": posix(result.relative_to(ROOT)), "row_index": index}
        attempts.append(item)
        latest[(row["name"], row["route"], row["framework"])] = item
ui_latest = {}
for result in sorted((E / "ui-live").glob("*/results.json")):
    for index, row in enumerate(read(result)["rows"]):
        ui_latest[(row["route"], row["framework"])] = {
            **row,
            "evidence": posix(result.relative_to(ROOT)),
            "row_index": index,
        }
budget = read(E / "campaign-budget.json")
spent = sum(Decimal(r["reserved_usd"]) for r in budget["attempts"])
usage = {
    "requests": len(budget["attempts"]),
    "usd_reserved": str(spent),
    "remaining_requests": 300 - len(budget["attempts"]),
    "remaining_usd": str(Decimal(10) - spent),
    "usd_interpretation": "Conservative transport reservation, not an invoice. Local Ollama counts requests with zero API charge.",
}
assert usage["requests"] <= 300 and spent <= 10
write(
    E / "matrix.json",
    {
        "version": toolkit.__version__,
        "wheel_sha256": WHEEL_HASH,
        "budget": usage,
        "latest_cases": list(latest.values()),
        "latest_ui": list(ui_latest.values()),
        "all_attempts": [
            {
                k: r[k]
                for k in (
                    "name",
                    "route",
                    "framework",
                    "passed",
                    "evidence",
                    "row_index",
                )
            }
            for r in attempts
        ],
        "acceptance": "incomplete: one business case failed; cloud Qwen and vLLM unavailable",
    },
)

words = set()
inventory = []
for relative, row in sorted(offline.items()):
    notebook = read(ROOT / relative)
    code = "\n".join(
        c["source"] if isinstance(c["source"], str) else "".join(c["source"])
        for c in notebook["cells"]
        if c["cell_type"] == "code"
    )
    digest = hashlib.sha256(code.encode()).hexdigest()
    assert digest == row["code_sha256_before_parameterization"], relative
    capture = E / posix(row["capture"])
    payload = read(capture)
    used = payload["grammar"]["combined"]["used"]
    words.update(used)
    calls = []
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            calls.append(
                {
                    "call": ast.unparse(node.func),
                    "keyword_parameters": [
                        kw.arg or "**kwargs" for kw in node.keywords
                    ],
                }
            )
    related = [r for key, r in profiles.items() if key[0] == relative]
    inventory.append(
        {
            "path": relative,
            "code_sha256": digest,
            "public_root_words_observed_offline": used,
            "calls_and_parameters_declared": calls,
            "offline": row,
            "profiles": related,
            "run_results_captured": len(payload.get("run_results", {})),
            "capture": posix(capture.relative_to(ROOT)),
        }
    )
write(
    DOCS / "NOTEBOOK_INVENTORY_214.json",
    {
        "version": toolkit.__version__,
        "notebooks": inventory,
        "public_root_words_observed": sorted(words),
        "root_denominator": 17,
    },
)
lines = [
    "# Inventario de notebooks · 2.1.4.dev3",
    "",
    "21 tutorials y 5 examples activos. Cada fila enlaza el archivo y la captura de su ejecución en un kernel nuevo contra el mismo wheel. Histórico, build y evidencia no cuentan como material activo.",
    "",
    "Las palabras se midieron al ejecutar el perfil offline. Celdas live/local se registran por separado; omitirlas no valida el servicio. Los métodos y parámetros escritos en cada notebook están en el [inventario JSON](NOTEBOOK_INVENTORY_214.json); las firmas completas del SDK están en [API_214_SURFACE](API_214_SURFACE.md).",
    "",
    "| Notebook | Palabras raíz observadas offline | Otros perfiles ejecutados |",
    "|---|---|---|",
]
for item in inventory:
    states = [
        f"{r['profile']}/{r['framework']}: {'pasó' if r['passed'] else 'falló'}"
        for r in item["profiles"]
        if r["profile"] != "offline"
    ]
    lines.append(
        f"| [{item['path']}]({link(ROOT / item['path'])}) | {', '.join('`' + w + '`' for w in item['public_root_words_observed_offline']) or '—'} | {'; '.join(states) or 'Offline'} |"
    )
lines += [
    "",
    f"Unión medida: **{len(words)}/17 palabras raíz**. No equivale a cubrir todos los parámetros, ramas, modelos o capacidades de los SDK.",
    "",
    "Los notebooks de Ollama Cloud y vLLM solo pasaron sus declaraciones offline: sus celdas de inferencia están pendientes. El notebook de OpenAI Agents ejecutó además su handoff con OpenAI real. Strands y Studio tienen ejecuciones locales adicionales con servicios reales y fixtures sin LM.",
]
md(DOCS / "NOTEBOOK_INVENTORY_214.md", lines)
md(
    DOCS / "GRAMMAR_COVERAGE_214.md",
    [
        "# Cobertura de gramática · 2.1.4.dev3",
        "",
        f"Los 26 notebooks activos ejercitan **{len(words)}/17** constructores y funciones raíz en el perfil offline.",
        "",
        ", ".join(f"`{w}`" for w in sorted(words)),
        "",
        "[Detalle por notebook, métodos declarados y parámetros](NOTEBOOK_INVENTORY_214.md). La medición excluye __version__ y llamadas internas del framework; no acredita todas las firmas o ramas.",
        "",
        "StateGraph, START, END, Runtime, add_node, add_edge y add_conditional_edges pertenecen a LangGraph y se cuentan aparte. model_artifact/model_server se prueban como declaraciones; el ciclo de vida simulado no acredita vLLM ni pesos en GPU.",
    ],
)

# Render compact lineage alongside raw serializable results; do not invent missing captures.
lineage_rows = []
for item in inventory:
    raw = read(ROOT / item["capture"])
    data = {}
    for name, value in raw.get("run_results", {}).items():
        result = toolkit.RunResult(**value)
        data[name] = {
            "execution_id": result.execution_id,
            "status": result.status,
            "ok": result.ok,
            "data": result.data,
            "human": result.lineage(name=name).render(),
            "agent": result.lineage().to_prompt_context(),
        }
    target = E / "notebook-lineage" / (item["path"].replace("/", "--") + ".json")
    target.parent.mkdir(exist_ok=True)
    write(
        target,
        {
            "path": item["path"],
            "run_results": data,
            "capture": item["capture"],
            "source_sha256": item["code_sha256"],
        },
    )
    lineage_rows.append((item["path"], len(data), target))
lines = [
    "# RunResults y linaje · 2.1.4.dev3",
    "",
    "El linaje explica la ejecución observada; Memory almacena episodios acotados, Context delimita el dominio y State conserva los canales de cálculo. No son almacenes intercambiables. Las capturas preservan IDs, relaciones padre/hijo, estado, datos, eventos y errores disponibles.",
    "",
    "Los ejemplos que solo devuelven un resumen o una configuración no se presentan como RunResults capturados. Los notebooks capturan variables RunResult de nivel superior, no todo resultado transitorio. Un conteo cero significa **no capturado**, no ausencia de trabajo.",
    "",
    "| Example ejecutado | RunResults capturados | Evidencia y linaje humano/agente |",
    "|---|---:|---|",
]
for row in examples["rows"]:
    target = E / "examples" / (row["path"].replace("/", "--") + ".json")
    if row["passed"] is None:
        lines.append(
            f"| `{row['path']}` | perfil local | [MCP/A2A]({link(E / 'local-protocol-results.json')}) |"
        )
    else:
        lines.append(
            f"| [{row['path']}]({link(ROOT / row['path'])}) | {len(row.get('run_results', []))} | [JSON]({link(target)}) |"
        )
lines += [
    "",
    "| Notebook | RunResults de nivel superior | Vistas de linaje |",
    "|---|---:|---|",
]
lines += [
    f"| `{name}` | {count} | [JSON]({link(path)}) |"
    for name, count, path in lineage_rows
]
lines += [
    "",
    "La [matriz online](../revisions/2.1.4/learning-dev3/matrix.json) enlaza todos los intentos originales. Los casos de negocio y reembolso incluyen además representaciones de linaje para humanos y agentes. No se recomputa inferencia para escribir este informe.",
]
md(DOCS / "RUNRESULTS_LINEAGE_214.md", lines)

matrix = [
    "| Runtime / destino | native | OpenAI Agents | AWS Strands |",
    "|---|---|---|---|",
    "| Python | Offline aprobado | Offline aprobado | Offline aprobado |",
    "| OpenAI API key · gpt-4.1-mini | Live aprobado | Live + handoff | Live + MCP/A2A |",
    "| Bedrock API key · Qwen3-32B | Live básico aprobado; 1 caso negocio falló | Live + handoff | Live + MCP/A2A |",
    "| Ollama GPU · Qwen3 4B | Live aprobado | Live + handoff | Live + MCP/A2A |",
    "| Ollama cloud/API key · Qwen | Pendiente | Pendiente | Pendiente |",
    "| vLLM GPU · Qwen | Pendiente | Pendiente | Pendiente |",
]
pending = [
    "Repetir de manera controlada calidad de datos / Bedrock / native: el modelo omitió amount:null y el esquema lo rechazó. El input exigido no se relajó ni se sustituyó el modelo.",
    "Ollama cloud autenticó, pero el catálogo no ofreció Qwen. No se usó Gemma como sustituto. vLLM no responde; requiere preparar Linux/Colab/WSL con GPU y Qwen.",
    "AWS IAM y ADA IAM, integración empresarial, extra [ada] y ADA Studio no están validados ni incluidos aquí.",
    "Las 45 proyecciones de negocio rotan los actores entre tres rutas: no son las 135 combinaciones de 15 ejemplos × 3 rutas × 3 actores, ni una ejecución LM de todos los grafos originales.",
    "Studio: controlador, envío/limpieza de historial, selección de proveedor/actor y protocolos tienen evidencia. Los 10 sistemas de catálogo se construyen/inspeccionan; faltan aceptación semántica de todos y todos los recorridos de UI.",
    "Persistencia durable de memoria/checkpoints, recuperación después de reinicio, streaming público, políticas distribuidas y API RL completa necesitan trabajo adicional del SDK.",
    "Uniformar binding de Tools con un único BaseModel y normalización de ToolEvent entre SDK; mejorar Eval para distinguir casos fallidos de no ejecutados por fail-fast. No se cambió el wheel para ocultar estas diferencias.",
    "CI multiversión de este conjunto y validación limpia Python 3.10–3.13 pendientes; las pruebas de esta campaña corrieron en Python "
    + sys.version.split()[0]
    + ".",
]
lines = [
    "# Validación de aprendizaje · 2.1.4.dev3",
    "",
    "Revisión local sin publicación. SDK instalado desde wheel sin modo editable; LangGraph es el único orquestador y native/OpenAI Agents/Strands son implementaciones de actor.",
    "",
    *matrix,
    "",
    "«Aprobado» corresponde a los escenarios identificados, no a todas las funciones del proveedor/framework.",
    "",
    "| Familia | Resultado más reciente | Alcance |",
    "|---|---:|---|",
    "| Notebooks offline | 26/26 | 21 tutorials + 5 examples; live/local omitido y registrado |",
    "| Entrypoints offline | 53/53 | 54 descubiertos; el restante usa servicios locales |",
    "| Regresiones offline | 192/192 | Contratos SDK, casos tipados y Studio |",
    "| Notebooks provider × actor | 9/9 | OpenAI, Bedrock y Ollama GPU × 3 actores |",
    "| Negocio con LM | 44/45 | 15 Tools, 3 rutas, asignación balanceada de actores |",
    "| Reembolso con pausa/reanudación | 9/9 | 3 rutas × 3 actores; reanudar no consumió otra llamada |",
    "| Studio controlador | 9/9 | 3 rutas × 3 actores |",
    "| Handoff OpenAI Agents | 3/3 | Una prueba por ruta disponible; notebook OpenAI real adicional pasó |",
    "| Strands MCP / A2A | 3/3 y 3/3 | Transporte local real + actor LM por ruta disponible |",
    "| Interoperabilidad de los tres actores | 3/3 | Repetición de las 3 rutas tras validar envoltura Bedrock |",
    "| Studio UI live | 9/9 | Envío READY, resultado y limpieza de historial |",
    "",
    "Los intentos anteriores fallidos permanecen en sus carpetas. La aceptación global está **incompleta** por un fallo de negocio y rutas no disponibles. No se publicó ni se selló una nueva versión.",
    "",
    "## Qué se corrigió",
    "",
    "Se migraron las guías y declaraciones a StateGraph. Las Tools de negocio usan argumentos tipados y esquemas cerrados compatibles con los SDK. Se corrigió la envoltura de composición secuencial de Studio, se separó el saludo visual del historial y se validó la identidad/éxito/datos antes de extraer la envoltura Bedrock en interoperabilidad. Las regresiones comprueban los límites; el SDK instalado mantiene los mismos bytes.",
    "",
    "## Presupuesto y artefacto",
    "",
    f"**{usage['requests']}/300 solicitudes**; reserva conservadora **USD {spent}/10**, saldo **{usage['remaining_requests']} solicitudes / USD {usage['remaining_usd']}**. Incluye fallos, repeticiones, handoffs, UI y Ollama. Es una reserva de transporte, no una factura del proveedor.",
    "",
    f"Wheel SHA-256: `{WHEEL_HASH}`. [Contador persistente]({link(E / 'campaign-budget.json')}) · [Matriz y todos los intentos]({link(E / 'matrix.json')}) · [JUnit offline]({link(E / 'all-offline-junit.xml')}).",
    "",
    "Ollama local usó qwen3:4b-instruct-2507-q4_K_M con digest 0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0. Las capturas comprobaron size_vram > 0 en la RTX 3070 Laptop. Bedrock usó qwen.qwen3-32b-v1:0 en us-east-2 y OpenAI gpt-4.1-mini. Claves excluidas de evidencia.",
    "",
    "## Pendientes",
    "",
    *[f"- {item}" for item in pending],
    "",
    "## Evidencia por archivo",
    "",
    "[Inventario de notebooks](NOTEBOOK_INVENTORY_214.md) · [RunResults y linaje](RUNRESULTS_LINEAGE_214.md) · [Catálogo examples](../examples/README.md) · [Plan de mejora](LEARNING_PLAN_214.md).",
]
md(DOCS / "LEARNING_VALIDATION_214.md", lines)
md(
    E / "REPORT.md",
    [
        "# Auditoría y validación · 2.1.4.dev3",
        "",
        "La documentación y las implementaciones didácticas se migraron a una sola gramática. Se restauró el logo original y se actualizó la skill mantenida. **No se publicó. La aceptación online no está completa.**",
        "",
        "[Informe de validación](../../../docs/LEARNING_VALIDATION_214.md) · [Inventario exhaustivo de notebooks](../../../docs/NOTEBOOK_INVENTORY_214.md) · [RunResults y linaje por archivo](../../../docs/RUNRESULTS_LINEAGE_214.md).",
        "",
        *matrix,
        "",
        f"Consumo: {usage['requests']} solicitudes; USD {spent} reservados. Restan {usage['remaining_requests']} solicitudes / USD {usage['remaining_usd']}.",
        "",
        "Conservación: before-learning.zip y audit-before.json documentan el punto inicial; todos los intentos live originales se mantienen. pre-format-sources.zip y format-provenance.json separan cambios de formato de correcciones semánticas; estas últimas tienen regresiones. Los cambios didácticos no modificaron el wheel del SDK.",
        "",
        "Se pueden construir referencias robustas para tareas acotadas, con contratos, límites, decisiones, controles negativos y evidencia. La documentación actual permite reproducirlas. Las limitaciones de persistencia, servicios no disponibles y aceptación semántica incompleta impiden afirmar cobertura universal o preparación de producción.",
        "",
        "[Plan congelado](live-plan.json) · [Ajuste balanceado](plan-amendments.json) · [Ajuste de contratos tipados](typed-example-amendment.json) · [Matriz reconciliada](matrix.json).",
    ],
)

# Keep stable historical catalog IDs, but make current version/status authoritative.
catalog = read(ROOT / "examples/catalog.json")
by_path = {r["path"]: r for r in examples["rows"]}
catalog["current_api_version"] = "2.1.4.dev3"
catalog["reviewed_at"] = "2026-10-26"
catalog["current_adaptations"] = {
    "historical_experiments": 34,
    "active_entrypoints": 54,
    "strict_offline_passed": 53,
    "separate_local_protocol_profile": 1,
    "target_configuration_only": 3,
}
catalog["catalog_id_policy"] = (
    "Historical IDs are stable catalog identifiers, not API aliases. Current implementation and evidence fields determine scope."
)
for entry in catalog["entries"]:
    entry["title"] = (
        entry["title"]
        .replace("cuatro frameworks", "tres actores")
        .replace("Cuatro frameworks", "Tres actores")
    )
    path = next(
        (s["target"] for s in entry.get("sources", []) if s["target"] in by_path), None
    )
    if path is None:
        mapping = {
            "order_fulfillment_213": "examples/order_fulfillment/example.py",
            "studio": "examples/agentic_systems_studio/example.py",
            "api_walkthrough": "examples/api_walkthrough/example.py",
        }
        path = mapping.get(entry["id"])
    status = (
        "offline-passed"
        if path in by_path and by_path[path]["passed"]
        else "see-file-inventory"
    )
    if entry["id"] in ("aws_iam", "ada_iam", "vllm_colab"):
        status = "configuration-offline-passed; target-live-pending"
    if entry["id"] == "strands_protocol_graph":
        status = "local-protocol-passed; zero-inference-fixture"
    if entry["id"] == "api_213_tutorials":
        status = "26-notebooks-offline-passed; live-scope-in-inventory"
    entry["readiness"] = status
    entry["validation"] = {
        "status": status,
        "version": "2.1.4.dev3",
        "wheel_sha256": WHEEL_HASH,
        "report": "docs/LEARNING_VALIDATION_214.md",
        "entrypoint": path,
    }
    projected = [r for r in latest.values() if r["name"] == "business/" + entry["id"]]
    if projected:
        entry["validation"]["live_tool_projections"] = [
            {k: r[k] for k in ("route", "framework", "passed", "evidence", "row_index")}
            for r in projected
        ]
write(ROOT / "examples/catalog.json", catalog)
lines = [
    "# Examples · 2.1.4.dev3",
    "",
    "Ejemplos de implementación con `import agentic_systems as toolkit`, ejecución directa y LangGraph. Empieza por [la guía de toda la API](api_walkthrough/01_api_user_guide.ipynb), después [seis flujos](common_graph/01_common_graph.ipynb) y [Context/Memory](context_memory_lineage/01_context_memory_lineage.ipynb).",
    "",
    "49 entradas de catálogo, incluidos los 34 experimentos históricos adaptados. Los IDs que incluyen 213 son identificadores conservados; sus fuentes actuales y validación indican dev3. Hay 54 entrypoints ejecutables: 53 pasan el perfil offline y uno el perfil de protocolos locales. Algunos son referencias explícitas al mismo ejemplo canónico; no se cuentan como experimentos independientes nuevos.",
    "",
    "Los tres ejemplos de AWS IAM, ADA IAM y vLLM/Colab solo validan configuración. El fallo live de calidad de datos queda visible. [Matriz y pendientes](../docs/LEARNING_VALIDATION_214.md) · [Resultados/linaje](../docs/RUNRESULTS_LINEAGE_214.md).",
    "",
    "| Ejemplo | Propósito | Estado actual |",
    "|---|---|---|",
]
for entry in catalog["entries"]:
    target = (
        entry.get("validation", {}).get("entrypoint") or entry["sources"][0]["target"]
    )
    lines.append(
        f"| [{entry['title']}]({link(ROOT / target, ROOT / 'examples')}) | {entry['purpose']} | {entry['readiness']} |"
    )
md(ROOT / "examples/README.md", lines)

summary = {
    "sdk_version": toolkit.__version__,
    "sdk_wheel_sha256": WHEEL_HASH,
    "budget": usage,
    "offline_notebooks": len(offline),
    "offline_examples": sum(r["passed"] is True for r in examples["rows"]),
    "latest_live_cases": len(latest),
    "latest_live_passed": sum(r["passed"] for r in latest.values()),
    "latest_ui_cases": len(ui_latest),
    "latest_ui_passed": sum(r["passed"] for r in ui_latest.values()),
    "root_words_observed": len(words),
    "published": False,
    "acceptance_complete": False,
    "pending": pending,
}
write(E / "summary.json", summary)
print(json.dumps(summary, ensure_ascii=True, indent=2))
