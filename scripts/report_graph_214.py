"""Report the dev7 grammar from its installed wheel and offline evidence."""
import ast
import dataclasses
import hashlib
import inspect
import json
from pathlib import Path
import platform
import re
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "revisions/2.1.4/grammar-dev7"
def read(path):
    return json.loads(path.read_text(encoding="utf-8"))
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def md(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
installation = read(E / "installation.json")
SITE = Path(installation["site"])
sys.path[:0] = [str(SITE), str(ROOT / "tutorials")]
from _offline import enforce_offline  # noqa: E402
enforce_offline()
import agentic_systems as toolkit  # noqa: E402
assert toolkit.__version__ == "2.1.4.dev7" and Path(toolkit.__file__).resolve().is_relative_to(SITE)
wheel = ROOT / installation["wheel"]
wheel_hash = digest(wheel)
assert wheel_hash == installation["wheel_sha256"]
with zipfile.ZipFile(wheel) as archive:
    for name in archive.namelist():
        if name.startswith("agentic_systems/") and not name.endswith("/"):
            assert archive.read(name) == (SITE / name).read_bytes() == (ROOT / "src" / name).read_bytes(), name
sdist = wheel.with_name("agentic_systems-2.1.4.dev7.tar.gz")
with tarfile.open(sdist) as archive:
    for member in archive.getmembers():
        if not member.isfile():
            continue
        relative = Path(*Path(member.name).parts[1:])
        if str(relative).replace("\\", "/").startswith("src/agentic_systems/") or relative.name in {"README.md", "CHANGELOG.md", "pyproject.toml"}:
            assert archive.extractfile(member).read() == (ROOT / relative).read_bytes(), member.name
upstream = {"Graph", "START", "END", "Command", "Send"}
core = set(toolkit.__all__) - upstream - {"__version__"}
assert len(core) == 15
assert not any(hasattr(toolkit, n) for n in ("Limits", "Action", "Runtime", "StateGraph", "check"))

# Constructor, method and returned-object signatures, observed without execution.
def signature(obj):
    try:
        return re.sub(r"0x[0-9A-Fa-f]+", "<address>", str(inspect.signature(obj)))
    except (TypeError, ValueError):
        return "(see upstream documentation)"
def public_methods(obj):
    return {name: signature(value) for name, value in inspect.getmembers(obj)
            if not name.startswith("_") and (inspect.isfunction(value) or inspect.ismethod(value))}
surface = ["# API observada del wheel · 2.1.4.dev7", "",
           "15 funciones/constructores propios, cinco reexportaciones originales de LangGraph y __version__. Firmas inspeccionadas en el wheel instalado fuera del checkout. Los métodos heredados de Pydantic/LangGraph pertenecen a esas bibliotecas; no son palabras nuevas ni requisitos del primer tutorial.", ""]
signatures = {}
for name in sorted(core):
    obj = getattr(toolkit, name)
    methods = public_methods(obj) if inspect.isclass(obj) else {}
    signatures[name] = {"signature": signature(obj), "methods": methods}
    surface += ["## " + name, "", "```python", name + signature(obj), "```", ""]
    surface += [f"- `{method}{spec}`" for method, spec in methods.items()] + [""]

def echo(value: int) -> dict:
    return {"value": value}
operation = toolkit.tool(echo)
artifact = toolkit.model_artifact("Qwen/Qwen3-8B")
# Compiled protocol is inspected with the actual supported Pydantic state.
import pydantic  # noqa: E402
class State(pydantic.BaseModel):
    value: int
graph = toolkit.Graph(State)
graph.add_node("echo", operation)
graph.add_edge(toolkit.START, "echo")
graph.add_edge("echo", toolkit.END)
unit = toolkit.System("signature", graph=graph)
returned = {"tool": operation, "skill": toolkit.skill(name="echo", tools=(operation,)),
            "runtime": toolkit.runtime(provider="python-runtime"), "framework": toolkit.framework("native"),
            "policy": toolkit.Agent("actor", runtime=toolkit.runtime(provider="python-runtime"), policy={}).policy,
            "compiled": unit.compile(), "model_artifact": artifact, "model_server": toolkit.model_server(artifact),
            "RunResult.lineage": toolkit.RunResult().lineage(), "RunResult.check_invariants": toolkit.RunResult().check_invariants()}
surface += ["## Objetos devueltos", "", "Las fábricas anteriores devuelven objetos con estos protocolos. Inspeccionarlos no inicia modelos ni servidores. model_construct de Pydantic evita validación y no se usa para configurar la ejecución.", ""]
for name, value in returned.items():
    attributes = list(getattr(type(value), "model_fields", {}))
    if dataclasses.is_dataclass(value):
        attributes += [f.name for f in dataclasses.fields(value) if not f.name.startswith("_")]
    attributes += [n for n, obj in inspect.getmembers(type(value)) if isinstance(obj, property) and not n.startswith("_")]
    item = {"attributes": sorted(set(attributes)), "methods": public_methods(type(value))}
    if isinstance(value, pydantic.BaseModel):
        item["pydantic_schema"] = type(value).model_json_schema()
    signatures.setdefault(name, {})["returned"] = item
    surface += ["### " + name, "", "Atributos: " + ", ".join(f"`{a}`" for a in item["attributes"]) + ".", ""]
    surface += [f"- `{n}{s}`" for n, s in item["methods"].items()] + [""]
surface += ["## LangGraph original", "", "Graph, START, END, Command y Send mantienen su identidad original. El Runtime de LangGraph permanece interno; los nodos y Tools piden `*, context: toolkit.Context`.", ""]
for name in ("add_node", "add_edge", "add_conditional_edges"):
    surface += [f"- `Graph.{name}{signature(getattr(toolkit.Graph, name))}`"]
surface += ["", "[Uso y contratos](API_214.md) · [Runtime/scheduler](RUNTIME_SCHEDULER_214.md)."]
write(E / "api-signatures.json", signatures)
md(ROOT / "docs/API_214_SURFACE.md", surface)

latest = {}
for file in sorted((E / "notebook-runs").glob("*/results.json")):
    for row in read(file):
        if row["profile"] == "offline":
            latest[row["path"]] = row
assert len(latest) == 28 and all(r["passed"] for r in latest.values())
inventory, used, result_rows = [], set(), []
def result_report(path, captured, memories=None):
    records = {}
    for name, payload in captured.items():
        result = toolkit.RunResult(**payload)
        assert result.check_invariants().ok, path
        records[result.execution_id] = {"source_name": name, "status": result.status, "ok": result.ok,
            "human_results": result.human_results(max_steps=5, max_chars=1800),
            "agent_lineage": result.lineage().to_prompt_context(),
            "context_observations": [run.meta["context"] for run in result.walk() if "context" in run.meta]}
    target = E / "lineage" / (path.replace("/", "--") + ".json")
    write(target, {"source": path, "wheel_sha256": wheel_hash, "results": records, "memory_snapshots": memories or {}})
    result_rows.append(f"| [{path}](../{path}) | {len(records)} | {len(memories or {})} | [JSON](../{target.relative_to(ROOT).as_posix()}) |")
for path, row in sorted(latest.items()):
    notebook = read(ROOT / path)
    code = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
    assert hashlib.sha256(code.encode()).hexdigest() == row["code_sha256_before_parameterization"], path
    capture = read(E / row["capture"])
    words = set(capture["grammar"]["combined"]["used"])
    used.update(words)
    tree = ast.parse(code)
    hidden = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
              and (n.module or "").startswith(("examples.", "agentic_systems_studio."))
              and any(a.name in {"run", "build", "demonstrate", "verify", "build_system", "build_conversational_system", "handoffs"} for a in n.names)]
    assert not hidden, path
    calls = [{"call": ast.unparse(n.func), "line": n.lineno, "positional_arguments": len(n.args), "keywords": [k.arg or "**kwargs" for k in n.keywords]}
             for n in ast.walk(tree) if isinstance(n, ast.Call)]
    inventory.append({"path": path, "offline_passed": True, "source_code_sha256": row["code_sha256_before_parameterization"],
        "core_words_observed": sorted(words & core), "upstream_words_observed": sorted(words & upstream),
        "calls_and_parameters_declared": calls, "skipped_cells": row["skipped_cells"], "capture": row["capture"], "hidden_builders": hidden})
    result_report(path, capture.get("run_results", {}), capture.get("memories"))
assert used & core == core, sorted(core - used)
write(ROOT / "docs/NOTEBOOK_INVENTORY_214.json", {"version": toolkit.__version__, "wheel_sha256": wheel_hash, "core_denominator": 15, "core_observed": sorted(used & core), "notebooks": inventory})
md(ROOT / "docs/NOTEBOOK_INVENTORY_214.md", ["# Inventario de notebooks · 2.1.4.dev7", "",
    "22 tutorials + 6 examples: los 28 ejecutaron offline en kernels nuevos con el mismo wheel instalado. Cada composición está visible. Los parámetros del JSON son referencias sintácticas; las palabras core observadas se midieron durante ejecución. Celdas live/local omitidas no quedan validadas.", "",
    "[Métodos y parámetros por notebook](NOTEBOOK_INVENTORY_214.json) · [Firmas](API_214_SURFACE.md) · [Informe](../revisions/2.1.4/grammar-dev7/REPORT.md).", "",
    "| Notebook | Core observado | Celdas omitidas |", "| --- | --- | ---: |",
    *[f"| [{r['path']}](../{r['path']}) | {', '.join('`'+w+'`' for w in r['core_words_observed'])} | {len(r['skipped_cells'])} |" for r in inventory],
    "", "Unión: **15/15**. Vocabulario ejercitado no equivale a todos los parámetros, rutas ni proveedores."])
md(ROOT / "docs/GRAMMAR_COVERAGE_214.md", ["# Cobertura de gramática · 2.1.4.dev7", "", "Core observado en notebooks: **15/15**: " + ", ".join(f"`{w}`" for w in sorted(core)) + ".", "", "Cinco reexportaciones originales de LangGraph: Graph, START, END, Command, Send. Los métodos upstream y los de Pydantic no añaden palabras propias. Esta cifra no certifica todas las ramas ni proveedores.", "", "[Inventario completo](NOTEBOOK_INVENTORY_214.md) · [Reporte de regresiones](../revisions/2.1.4/grammar-dev7/REPORT.md)."])
examples = read(E / "examples-offline.json")
assert sum(r.get("passed") is True for r in examples["rows"]) == 56
assert not any(r.get("passed") is False for r in examples["rows"])
for row in examples["rows"]:
    if row.get("passed") is not True:
        continue
    assert digest(ROOT / row["path"]) == row["source_sha256"], row["path"]
    result_report(row["path"], {str(i): v for i, v in enumerate(row.get("run_results", []))}, {"output": row.get("output", {}).get("memory")} if isinstance(row.get("output"), dict) and row["output"].get("memory") is not None else {})
protocols = read(E / "local-protocols.json")
assert protocols["inference_requests"] == 0 and protocols["wheel_sha256"] == wheel_hash
result_report("examples/patterns/strands_protocol_graph/example.py", {row["protocol"]: row["result"] for row in protocols["rows"]})
md(ROOT / "docs/RUNRESULTS_LINEAGE_214.md", ["# RunResults, Memory y linaje · 2.1.4.dev7", "", "Evidencia del mismo wheel. Cero resultados puede significar configuración/CLI, no una ejecución de Agent. Los fallos esperados y pausas se conservan como tales. human_results es una proyección; el registro completo permanece en las capturas.", "", "| Fuente | RunResults capturados | Snapshots Memory | Evidencia humana/agente |", "| --- | ---: | ---: | --- |", *result_rows,
    "", "[Reporte](../revisions/2.1.4/grammar-dev7/REPORT.md) · [Inventario](NOTEBOOK_INVENTORY_214.md)."])

campaign = ROOT / "revisions/2.1.4/contracts-dev5/campaign-budget.json"
assert digest(campaign) == "6ce1ae54e97e11835598312e56ca403ca7b267478a99ce1bc5c93a0bdbd5b9e6"
previous = ROOT / "revisions/2.1.4/contracts-dev5/builds/03/agentic_systems-2.1.4.dev5-py3-none-any.whl"
assert digest(previous) == "df328e52d7a2660d7b29ce45a40c689766ce99196c02d5672930dd5663bbde34"
previous_dev6 = ROOT / "revisions/2.1.4/grammar-dev6/builds/01/agentic_systems-2.1.4.dev6-py3-none-any.whl"
assert digest(previous_dev6) == "ab41fbb251a04ace7d93b9650754632720d4c12715787b0ac5dbf7eec90f3df9"
tests = {name: sum(int(s.get(name, 0)) for s in ET.parse(E / "offline-junit.xml").getroot().iter("testsuite")) for name in ("tests", "failures", "errors", "skipped")}
assert tests["tests"] == 364 and not any(tests[n] for n in ("failures", "errors", "skipped"))
summary = {"version": toolkit.__version__, "wheel_sha256": wheel_hash, "sdist_sha256": digest(sdist), "installed_outside_checkout": True,
    "python": platform.python_version(), "offline_tests": tests, "offline_notebooks": 28, "offline_examples": 56,
    "local_protocol_example": {"status": "passed", "protocols": [r["protocol"] for r in protocols["rows"]], "inference_requests": 0},
    "core_observed": sorted(core), "core_denominator": 15, "upstream_exports": sorted(upstream),
    "inference_requests_this_revision": 0, "published": False, "campaign_unchanged_sha256": digest(campaign),
    "previous_wheel_unchanged_sha256": digest(previous), "dev6_wheel_unchanged_sha256": digest(previous_dev6), "live_validation_transferred": False,
    "scaffolder": read(E / "scaffolder.json"), "pending": ["live acceptance of dev7 bytes", "CI Python 3.10–3.14", "vLLM GPU", "AWS IAM", "ADA IAM", "durable continuation/memory"]}
write(E / "summary.json", summary)
contracts = [
 ("Graph único", "Identidad con StateGraph original; no exports StateGraph ni check"),
 ("compile prepara", "Compilación sin efectos, records lazy ni casos ejecutados"),
 ("Tools Pydantic", "Binding modelo como nodo y en native/OpenAI Agents/Strands con Python; entradas/salidas inválidas rechazadas"),
 ("SDK OpenAI", "Contrato root sin envoltura de parámetro; validación de JSON crudo antes de efectos y sin coerción previa"),
 ("Eval aislada", "Cada caso tiene su vista de Memory; progreso por episodio interno y sin escritura de producción"),
 ("human_results", "Entradas anidadas reales, estados reales, operaciones semánticas y un ID raíz"),
 ("Environment/rewards", "Métrica explícita en update/state/history; no reward= ni entrenamiento implícito"),
 ("Artefacto independiente", "Wheel/sdist, instalación externa, 118 hashes RECORD y toda la validación ligada al hash")]
md(E / "REPORT.md", ["# Graph y compilación · 2.1.4.dev7", "",
 "Revisión local sin publicar. Graph define, compile prepara, run ejecuta y human_results explica. Agent organiza una capacidad; System coordina la aplicación; Environment procesa episodios. No hay check ni StateGraph como nombres públicos alternativos.", "",
 f"Wheel SHA-256: `{wheel_hash}`. [Wheel](builds/01/{wheel.name}) · [sdist](builds/01/{sdist.name}) · [Instalación](installation.json) · [Snapshot de fuente](source-snapshot.json). El commit identifica la base; los cambios locales quedan identificados por hashes.", "",
 f"Validación con Python **{platform.python_version()}**: **364 pruebas**, **28 notebooks** (22 tutorials + 6 examples), **56 entrypoints** y **1 example MCP/A2A local**. **15/15 palabras core** ejercitadas; cinco objetos originales de LangGraph se informan aparte. [JUnit](offline-junit.xml) · [Examples](examples-offline.json) · [Protocolos](local-protocols.json) · [Resumen](summary.json).", "",
 "## Contratos", "", "| Contrato | Evidencia |", "| --- | --- |", *[f"| {a} | {b} |" for a,b in contracts], "",
 "## Lo que cambió", "",
 "Graph es el StateGraph original de LangGraph bajo un único nombre público. Se retira check y su módulo del SDK. Los constructores conservan validación local; compile comprueba estructura declarada sin ejecutar negocio. No prueba código Python arbitrario.", "",
 "Tools con input_schema y un único parámetro de negocio reciben el modelo Pydantic. Una firma contradictoria se rechaza antes de efectos; como nodo se proyectan los campos del contrato. OpenAI Agents antes generaba una envoltura request; el adaptador ahora expone el contrato raíz y valida argumentos JSON crudos antes del cuerpo, evitando coerción previa del SDK. Regresiones con SDKs reales prueban el mismo modelo Quantity directamente, como nodo y con native/OpenAI Agents/Strands sobre Python, incluidos negativos. No certifican todos los tipos Pydantic ni todos los proveedores live.", "",
 "Eval da a cada caso vistas privadas de Memory, incluidos accesos por closures y comprobaciones. Un Environment del mismo caso observa sus episodios anteriores dentro de esa vista. No se escriben episodios en Memory de producción. Esto no clona sesiones SDK ni aísla efectos externos o archivos.", "",
 "Las entradas de unidades anidadas se guardan como evidencia original. human_results usa estados reales, nombres de negocio y un solo ID raíz; oculta wrappers en esa presentación, manteniendo to_dict/trace/lineage completos. Las decisiones no se imprimen como status.", "",
 "## Notebook y rewards", "",
 "[Notebook explícito ejecutado](../../../examples/checked_composition/01_checked_composition.ipynb): input 5000 → fee 50 → total 5050 → approved; segundo pago 12000 → fee 120 → total 12120 → pending_review. Eval comprueba ambos y mantiene tres episodios en Memory de producción.", "",
 "La recompensa se calcula explícitamente en Environment.update: 1 si la salida coincide con el oráculo del Environment, 0 si no. El oráculo no se pasa al System. State/history registran reward y total_reward=2. No hay reward= público ni entrenamiento automático de una política. [Contrato de Environment](../../../docs/ENVIRONMENT_214.md).", "",
 "## Intentos y límites", "",
 "La primera pasada de notebooks registró un timeout de 40 segundos en common_graph al ejecutarse junto a otros validadores. Se conserva ese intento y se repite el mismo notebook, con el mismo wheel, límites y oráculos, en un proceso aislado: pasó sus 16 celdas. No se relajó el plazo ni se atribuyó un PASS de otro caso. notebook-runs conserva todas las pasadas; el inventario toma la más reciente de cada archivo.", "",
 "Los fallos iniciales de migración, el binding Pydantic OpenAI y los intentos fuente se conservan en source-*-junit.xml y logs. La suite de 364 tests contra el wheel instalado terminó sin fallos, errores ni skips.", "",
 "El scaffolder de CLI/skill generó fuera del checkout un proyecto con Graph; se ejecutó con los tres actores Python y su notebook en un kernel nuevo. [Evidencia](scaffolder.json). Studio pasó su subconjunto de controlador/UI dentro de las 364 pruebas; no se afirma cobertura total de UI o modelos reales. MCP/A2A usó modelos fixture y transportes reales de loopback, con conexiones externas prohibidas y cierre de servicios.", "",
 "**Cero inferencia y cero publicación.** La campaña dev5 conserva 148/150 solicitudes y USD 0.875040 reservados de USD 5, con hash inalterado. Artefactos dev5 y dev6 se conservan intactos. La aceptación live previa no se transfiere a dev7.", "",
 "Quedan pendientes la campaña live del artefacto final, CI Python 3.10–3.14, Bedrock/null y Studio/Bedrock, interoperabilidad Ollama cloud, vLLM, AWS IAM/ADA IAM y persistencia durable. No se promete preempción forzosa, rollback ni una API RL completa.", "",
 "[API](../../../docs/API_214.md) · [Firmas](../../../docs/API_214_SURFACE.md) · [Inventario](../../../docs/NOTEBOOK_INVENTORY_214.md) · [RunResults/Memory/linaje](../../../docs/RUNRESULTS_LINEAGE_214.md)."])
md(ROOT / "docs/LEARNING_VALIDATION_214.md", ["# Validación vigente · 2.1.4.dev7", "", "[Informe del wheel](../revisions/2.1.4/grammar-dev7/REPORT.md) · [Resumen](../revisions/2.1.4/grammar-dev7/summary.json).", "", "364 regresiones, 28 notebooks, 56 entrypoints y un example MCP/A2A local; cero inferencia. Los tres actores ejecutan Python determinista. Las celdas live y servicios omitidos no quedan certificados.", "", "Toda la aceptación live de los nuevos bytes queda pendiente. No se publicó. La evidencia dev5 conserva su identidad y no se transfiere. [Estado](STATUS_214.md) · [Inventario](NOTEBOOK_INVENTORY_214.md)."])
# Upgrade current catalog metadata while retaining original/historical acceptance.
p = ROOT / "examples/catalog.json"
catalog = read(p)
catalog.setdefault("historical_baselines", [])
if catalog["baseline"].get("version") != toolkit.__version__:
    catalog["historical_baselines"].append(catalog["baseline"])
catalog["baseline"] = {"version": toolkit.__version__, "wheel_sha256": wheel_hash}
by_path = {r["path"]: r for r in examples["rows"]}
for entry in catalog["entries"]:
    previous_validation = entry.get("validation", {})
    path = previous_validation.get("entrypoint")
    row = by_path.get(path)
    if row is None:
        continue
    if previous_validation.get("version") != toolkit.__version__:
        entry.setdefault("validation_history", []).append(previous_validation)
    entry["api_version"] = toolkit.__version__
    entry["validation"] = {"version": toolkit.__version__, "status": "offline-passed" if row.get("passed") else "local-protocol-passed", "entrypoint": path, "wheel_sha256": wheel_hash, "report": "revisions/2.1.4/grammar-dev7/REPORT.md"}
catalog.update(api_version=toolkit.__version__, validation_report="revisions/2.1.4/grammar-dev7/REPORT.md", reviewed_at="2026-10-28")
catalog["additional_current_examples"] = ["examples/checked_composition/example.py", "examples/applications/financial_harness/example.py", "examples/applications/financial_harness/progressive.py"]
write(p, catalog)
print(json.dumps({"tests": tests, "notebooks": len(inventory), "examples": 56, "local_protocol_example": 1, "core": len(core), "wheel_sha256": wheel_hash}))
