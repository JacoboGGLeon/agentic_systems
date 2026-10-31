"""Reconcile dev4 evidence and refresh current API/learning inventories offline."""

import ast
from decimal import Decimal
import hashlib
import inspect
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "revisions/2.1.4/pydantic-dev4"
SITE = ROOT / ".tmp/candidate214-dev4-final/site-packages"
sys.path.insert(0, str(SITE))
import agentic_systems as toolkit  # noqa: E402


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def md(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


assert toolkit.__version__ == "2.1.4.dev4"
wheel = E / "builds/03/agentic_systems-2.1.4.dev4-py3-none-any.whl"
wheel_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
latest = {}
for path in sorted((E / "notebook-runs").glob("*/results.json")):
    for row in read(path):
        latest[(row["path"], row["profile"], row["framework"])] = {**row, "results_file": path.relative_to(ROOT).as_posix()}
offline = {key[0]: row for key, row in latest.items() if key[1] == "offline"}
assert len(offline) == 26 and all(row["passed"] for row in offline.values())
examples = read(E / "examples-offline.json")
assert sum(row["passed"] is True for row in examples["rows"]) == 53
assert not examples["offline_guard_blocked_attempts"]
online = {}
attempts = []
for path in sorted((E / "online").glob("*/results.json")):
    payload = read(path)
    assert payload["wheel_sha256"] == wheel_hash
    for row in payload["rows"]:
        item = {**row, "evidence": path.relative_to(ROOT).as_posix()}
        online[row["route"]] = item
        attempts.append(item)
assert len(online) == 4 and all(row["passed"] for row in online.values())
ledger = read(ROOT / "revisions/2.1.4/learning-dev3/campaign-budget.json")
reserved = sum(Decimal(row["reserved_usd"]) for row in ledger["attempts"])
assert len(ledger["attempts"]) == 300 and reserved <= 10
core = set(toolkit.__all__) - {"__version__", "StateGraph", "START", "END", "Runtime", "Command", "Send"}
inventory = []
used = set()
lineage = ["# RunResults y linaje · 2.1.4.dev4", "", "human_results() presenta el mismo RunResult sin ejecutar inferencia. Memory conserva episodios; no constituye otro formato de resultados. Las capturas con cero resultados solo devolvieron configuración/resumen o no dejaron una variable RunResult de nivel superior. No se inventó una captura.", "", "| Archivo ejecutado | RunResults capturados | Evidencia |", "|---|---:|---|"]
for path, row in sorted(offline.items()):
    notebook = read(ROOT / path)
    code = "\n".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
    assert hashlib.sha256(code.encode()).hexdigest() == row["code_sha256_before_parameterization"], path
    tree = ast.parse(code)
    assert not any(isinstance(n, ast.FunctionDef) and n.name == "show" for n in ast.walk(tree))
    assert not any(isinstance(n, ast.Name) and n.id == "TypedDict" for n in ast.walk(tree))
    capture = E / row["capture"].replace("\\", "/")
    observed = read(capture)
    words = set(observed["grammar"]["combined"]["used"])
    used.update(words)
    declared = sorted({ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)})
    parameters = [{"call": ast.unparse(n.func), "parameters": [kw.arg or "**kwargs" for kw in n.keywords]} for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    data = {}
    for name, payload in observed.get("run_results", {}).items():
        result = toolkit.RunResult(**payload)
        data[name] = {"execution_id": result.execution_id, "ok": result.ok, "status": result.status, "human_results": result.human_results(), "human_lineage": result.lineage().render(), "agent_lineage": result.lineage().to_prompt_context()}
    target = E / "notebook-lineage" / (path.replace("/", "--") + ".json")
    target.parent.mkdir(exist_ok=True)
    write(target, {"source": path, "results": data, "capture": capture.relative_to(ROOT).as_posix()})
    lineage.append(f"| `{path}` | {len(data)} | [JSON](../{target.relative_to(ROOT).as_posix()}) |")
    inventory.append({"path": path, "offline_passed": True, "code_sha256": row["code_sha256_before_parameterization"], "core_words_observed": sorted(words & core), "upstream_words_observed": sorted(words - core), "calls_declared": declared, "calls_and_parameters": parameters, "skipped_cells": row["skipped_cells"], "evidence": row["results_file"], "capture": capture.relative_to(ROOT).as_posix()})
for row in examples["rows"]:
    target = E / "examples" / (row["path"].replace("/", "--") + ".json")
    lineage.append(f"| `{row['path']}` | {len(row.get('run_results', [])) if row['passed'] is not None else 'perfil local'} | " + (f"[JSON](../{target.relative_to(ROOT).as_posix()}) |" if target.exists() else "Ver perfil local Strands en el informe actual |"))
md(ROOT / "docs/RUNRESULTS_LINEAGE_214.md", lineage)
write(ROOT / "docs/NOTEBOOK_INVENTORY_214.json", {"version": toolkit.__version__, "wheel_sha256": wheel_hash, "core_denominator": len(core), "core_observed": sorted(used & core), "upstream_observed": sorted(used - core), "notebooks": inventory})
lines = ["# Inventario de notebooks · 2.1.4.dev4", "", "21 tutorials + 5 examples. Los 26 ejecutaron el perfil offline contra el mismo wheel final. Las celdas live/local omitidas quedan registradas; una declaración no acredita inferencia. No hay show ni TypedDict en el código de estos notebooks.", "", "[Métodos y parámetros por notebook](NOTEBOOK_INVENTORY_214.json) · [Firmas del SDK](API_214_SURFACE.md) · [Validación y límites](../revisions/2.1.4/pydantic-dev4/REPORT.md).", "", "| Notebook | Vocabulario core observado | Celdas omitidas offline |", "|---|---|---:|"]
for item in inventory:
    lines.append(f"| [{item['path']}](../{item['path']}) | {', '.join('`'+w+'`' for w in item['core_words_observed']) or 'Referencias a módulos canónicos'} | {len(item['skipped_cells'])} |")
lines += ["", f"Unión core: **{len(used & core)}/{len(core)}**. Los objetos reexportados de LangGraph se distinguen del vocabulario propio. La medición de llamadas no equivale a cubrir todos los parámetros, rutas ni proveedores."]
md(ROOT / "docs/NOTEBOOK_INVENTORY_214.md", lines)
md(ROOT / "docs/GRAMMAR_COVERAGE_214.md", ["# Cobertura de gramática · 2.1.4.dev4", "", f"Los notebooks ejercitan **{len(used & core)}/{len(core)}** constructores/funciones core: " + ", ".join(f"`{w}`" for w in sorted(used & core)) + ".", "", "Se exponen además StateGraph, START, END, Runtime, Command y Send, originales de LangGraph. Las regresiones prueban identidad, envíos dinámicos y compatibilidad de ejecución. No se cuentan como constructores propios nuevos.", "", "[Inventario por notebook y parámetros](NOTEBOOK_INVENTORY_214.md). human_results es un método de RunResult, no otra función raíz. model_server solo se declara offline: no acredita vLLM/GPU."])

# Signatures, not invented aliases. Upstream objects have their own authoritative API.
surface = ["# Firmas públicas observadas · 2.1.4.dev4", "", "Generadas con inspect sobre el wheel instalado. 17 constructores/funciones core y 6 reexportaciones de LangGraph; __version__ es un dato. Pydantic se importa directamente."]
api = {}
for name in sorted(core):
    obj = getattr(toolkit, name)
    signature = str(inspect.signature(obj))
    methods = {n: str(inspect.signature(v)) for n, v in inspect.getmembers(obj) if not n.startswith("_") and inspect.isfunction(v)} if inspect.isclass(obj) else {}
    api[name] = {"signature": signature, "methods": methods}
    surface += ["", "## " + name, "", "```python", name + signature, "```"]
    surface += [f"- `{method}{sig}`" for method, sig in methods.items()]
surface += ["", "## LangGraph desde toolkit", "", "StateGraph, START, END, Runtime, Command y Send son reexportaciones originales, sin motor ni gramática paralela. [Graph API oficial](https://docs.langchain.com/oss/python/langgraph/graph-api).", "", "Las fábricas tool/skill/runtime/framework/model_artifact/model_server devuelven objetos con métodos públicos descritos en la [API de usuario](API_214.md). La documentación histórica del inventario dev3 no sustituye el inventario de este wheel."]
if (E / "factory-surface.json").exists():
    surface += ["", "## Objetos devueltos por fábricas", "", "Se inspeccionaron sin iniciar servidores ni inferencia; no se construyen sus clases privadas directamente."]
    for name, row in read(E / "factory-surface.json").items():
        surface += ["", "### " + name, "", "Atributos: " + ", ".join("`" + field + "`" for field in row["attributes"]) + ".", ""]
        surface += [f"- `{method}{sig}`" for method, sig in row["methods"].items()]
md(ROOT / "docs/API_214_SURFACE.md", surface)
write(E / "api-signatures.json", api)

catalog = read(ROOT / "examples/catalog.json")
catalog["api_version"] = catalog["current_api_version"] = toolkit.__version__
catalog["baseline"] = {"version": toolkit.__version__, "wheel_sha256": wheel_hash}
catalog["validation_report"] = "revisions/2.1.4/pydantic-dev4/REPORT.md"
by_path = {row["path"]: row for row in examples["rows"]}
for entry in catalog["entries"]:
    old = entry.get("validation", {})
    entry.setdefault("historical_validation_dev3", old)
    path = old.get("entrypoint")
    if path not in by_path:
        path = next((s["target"] for s in entry.get("sources", []) if s["target"] in by_path), path)
    status = "offline-passed" if path in by_path and by_path[path]["passed"] is True else "see-current-report"
    if entry["id"] in {"vllm_colab", "aws_iam", "ada_iam"}:
        status = "configuration-only; target-live-pending"
    if entry["id"] == "strands_protocol_graph":
        status = "local-protocol-fixture; not-live-LM"
    entry["validation"] = {"version": toolkit.__version__, "status": status, "entrypoint": path, "wheel_sha256": wheel_hash, "report": catalog["validation_report"]}
    entry["readiness"] = status
write(ROOT / "examples/catalog.json", catalog)

suites = list(ET.parse(E / "offline-junit.xml").getroot().iter("testsuite"))
tests = {key: sum(int(s.get(key, 0)) for s in suites) for key in ("tests", "errors", "failures", "skipped")}
assert tests["errors"] == tests["failures"] == tests["skipped"] == 0
summary = {"version": toolkit.__version__, "wheel_sha256": wheel_hash, "offline_notebooks": 26, "offline_examples": 53, "offline_tests": tests, "root_core_words_observed": len(used & core), "online_latest": list(online.values()), "online_all_attempts": attempts, "budget": {"requests": len(ledger["attempts"]), "limit": 300, "reserved_usd": str(reserved), "usd_limit": 10}, "published": False, "full_online_matrix_repeated": False}
write(E / "summary.json", summary)
lines = ["# Pydantic y human_results · 2.1.4.dev4", "", "Candidata local no publicada. Dos imports básicos: import pydantic e import agentic_systems as toolkit. La evidencia dev3 permanece histórica.", "", "## Cambios", "", "Estados Pydantic para grafos de Agent, System y Environment; modelos anidados, validadores, actualizaciones parciales, entrada/salida distintas, async, reducers, Send, Context y pausa/reanudación. RunResult.human_results() es una vista acotada de la misma evidencia, sin inferencia. Los objetos LangGraph se exponen por toolkit sin cambiar identidad ni motor.", "", "Se eliminaron los tres helpers show. 26 notebooks y las declaraciones canónicas usan Pydantic; los Tools de negocio y sus muestras/aserciones se compararon por AST antes de aplicar lotes revisados. La migración masiva inicial fue rechazada por revisión automática; se usó staging, revisión y lotes pequeños. Los intentos fallidos permanecen en notebook-runs y examples.", "", "Se corrigieron contratos reales: el rechazo de un pedido admite total_cents=null; un subtotal calculado no se exige en la entrada; los jueces tienen su propio estado. Los nulos explícitos se distinguen de campos opcionales que todavía no existen.", "", "## Validación", "", "- 26/26 notebooks offline; celdas live/local omitidas explícitamente y registradas.", "- 53/53 entrypoints offline; los protocolos reales locales tienen perfil separado sin LM.", "- Regresiones completas: ver offline-junit.xml. Incluyen conservación de validadores, errores antes de efectos, paralelismo, modelos por nodo, async, outputs Pydantic, Context, Memory, Eval, pausa/reanudación y presentación humana.", "", "| Ruta | Modelo | Actor | Último resultado |", "|---|---|---|---|"]
for route, row in online.items():
    lines.append(f"| {route} | {row['model']} | {row['framework']} | {'PASS' if row['passed'] else 'FAIL'} |")
lines += ["", "Estas son cuatro pruebas de integración Pydantic → Agent LM → System → RunResult/human_results, con input value=2 y output answer=3. No son las 12 combinaciones, ni una repetición avanzada de Tools/handoff/MCP/A2A/Studio en todos los modelos. Python cubrió esas composiciones offline.", "", "El primer intento Ollama GPU fue bloqueado antes de transmitir porque el cliente nativo leyó un perfil de entorno que no coincidía con la ruta congelada. Se alineó en memoria el mismo Qwen/endpoint y se repitió solo esa celda. No se editó .env, no se sustituyó modelo y el fallo permanece en online. Los reintentos internos bloqueados no llegaron al proveedor.", "", f"Acumulado del contador: **{len(ledger['attempts'])}/300 solicitudes**, **USD {reserved}** reservados. Se agotaron las solicitudes; no se reinició ni se aplicó la ampliación a 340 que la revisión automática rechazó. Ningún trabajador sigue infiriendo y no se ejecutarán más llamadas con este contador.", "", f"Wheel SHA-256: `{wheel_hash}`. [Wheel](builds/03/agentic_systems-2.1.4.dev4-py3-none-any.whl) · [sdist](builds/03/agentic_systems-2.1.4.dev4.tar.gz) · [JUnit](offline-junit.xml) · [Resumen y todos los intentos](summary.json).", "", "## Límites y pendientes", "", "vLLM sigue pendiente por decisión del usuario. Ollama cloud no ofrece Qwen: Gemma4 fue autorizado. El fallo previo de Bedrock/Qwen al omitir un null de una Tool permanece sin resolver: el PASS de esta prueba JSON sencilla no lo corrige ni lo sustituye. No hay aceptación global de release estable, CI multiversión de esta revisión ni publicación.", "", "Context/Memory y los checkpoints siguen siendo snapshots locales; no hay persistencia durable. El estado de episodio de Environment y sus callbacks conservan el protocolo JSON documentado; el modelo Pydantic del grafo valida cada observación. Ollama nativo requiere que su perfil de entorno coincida con el runtime declarado.", "", "[API](../../../docs/API_214.md) · [Inventario completo de notebooks](../../../docs/NOTEBOOK_INVENTORY_214.md) · [RunResults y linaje](../../../docs/RUNRESULTS_LINEAGE_214.md) · [Revisión de cambios de enseñanza](staged-semantic-review.json)."]
md(E / "REPORT.md", lines)
with (E / "REPORT.md").open("a", encoding="utf-8") as stream:
    stream.write(f"\nLa suite final registró **{tests['tests']} pruebas aprobadas**, cero fallos/errores/omitidas. Los 13 avisos son una deprecación de una dependencia; no fallos de contrato.\n")
    stream.write("\n[Skill portable](deliverables/agentic-systems-skill-2.1.4.dev4.zip) · [Scaffolder y skill](skill-validation.json). La instalación personal de Codex quedó sincronizada; el ZIP no instala automáticamente en la cuenta de ChatGPT.\n")
print(json.dumps({"notebooks": 26, "examples": 53, "core_words_observed": len(used & core), "online_passed": sum(r["passed"] for r in online.values()), "wheel_sha256": wheel_hash, "budget_requests": len(ledger["attempts"])}))
