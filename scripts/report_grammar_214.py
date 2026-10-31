"""Report the dev6 grammar from its installed wheel and offline evidence."""
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
E = ROOT / "revisions/2.1.4/grammar-dev6"
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
assert toolkit.__version__ == "2.1.4.dev6" and Path(toolkit.__file__).resolve().is_relative_to(SITE)
wheel = ROOT / installation["wheel"]
wheel_hash = digest(wheel)
assert wheel_hash == installation["wheel_sha256"]
with zipfile.ZipFile(wheel) as archive:
    for name in archive.namelist():
        if name.startswith("agentic_systems/") and not name.endswith("/"):
            assert archive.read(name) == (SITE / name).read_bytes() == (ROOT / "src" / name).read_bytes(), name
sdist = wheel.with_name("agentic_systems-2.1.4.dev6.tar.gz")
with tarfile.open(sdist) as archive:
    for member in archive.getmembers():
        if not member.isfile():
            continue
        relative = Path(*Path(member.name).parts[1:])
        if str(relative).replace("\\", "/").startswith("src/agentic_systems/") or relative.name in {"README.md", "CHANGELOG.md", "pyproject.toml"}:
            assert archive.extractfile(member).read() == (ROOT / relative).read_bytes(), member.name
upstream = {"StateGraph", "START", "END", "Command", "Send"}
core = set(toolkit.__all__) - upstream - {"__version__"}
assert len(core) == 16
assert not any(hasattr(toolkit, n) for n in ("Limits", "Action", "Runtime"))

# Constructor, method and returned-object signatures, observed without execution.
def signature(obj):
    try:
        return re.sub(r"0x[0-9A-Fa-f]+", "<address>", str(inspect.signature(obj)))
    except (TypeError, ValueError):
        return "(see upstream documentation)"
def public_methods(obj):
    return {name: signature(value) for name, value in inspect.getmembers(obj)
            if not name.startswith("_") and (inspect.isfunction(value) or inspect.ismethod(value))}
surface = ["# API observada del wheel · 2.1.4.dev6", "",
           "16 funciones/constructores propios, cinco reexportaciones originales de LangGraph y __version__. Firmas inspeccionadas en el wheel instalado fuera del checkout. Los métodos heredados de Pydantic/LangGraph pertenecen a esas bibliotecas; no son palabras nuevas ni requisitos del primer tutorial.", ""]
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
graph = toolkit.StateGraph(State)
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
surface += ["## LangGraph original", "", "StateGraph, START, END, Command y Send mantienen su identidad original. El Runtime de LangGraph permanece interno; los nodos y Tools piden `*, context: toolkit.Context`.", ""]
for name in ("add_node", "add_edge", "add_conditional_edges"):
    surface += [f"- `StateGraph.{name}{signature(getattr(toolkit.StateGraph, name))}`"]
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
write(ROOT / "docs/NOTEBOOK_INVENTORY_214.json", {"version": toolkit.__version__, "wheel_sha256": wheel_hash, "core_denominator": 16, "core_observed": sorted(used & core), "notebooks": inventory})
md(ROOT / "docs/NOTEBOOK_INVENTORY_214.md", ["# Inventario de notebooks · 2.1.4.dev6", "",
    "22 tutorials + 6 examples: los 28 ejecutaron offline en kernels nuevos con el mismo wheel instalado. Cada composición está visible. Los parámetros del JSON son referencias sintácticas; las palabras core observadas se midieron durante ejecución. Celdas live/local omitidas no quedan validadas.", "",
    "[Métodos y parámetros por notebook](NOTEBOOK_INVENTORY_214.json) · [Firmas](API_214_SURFACE.md) · [Informe](../revisions/2.1.4/grammar-dev6/REPORT.md).", "",
    "| Notebook | Core observado | Celdas omitidas |", "| --- | --- | ---: |",
    *[f"| [{r['path']}](../{r['path']}) | {', '.join('`'+w+'`' for w in r['core_words_observed'])} | {len(r['skipped_cells'])} |" for r in inventory],
    "", "Unión: **16/16**. Vocabulario ejercitado no equivale a todos los parámetros, rutas ni proveedores."])
md(ROOT / "docs/GRAMMAR_COVERAGE_214.md", ["# Cobertura de gramática · 2.1.4.dev6", "", "Core observado en notebooks: **16/16**: " + ", ".join(f"`{w}`" for w in sorted(core)) + ".", "", "Cinco reexportaciones originales de LangGraph: StateGraph, START, END, Command, Send. Los métodos upstream y los de Pydantic no añaden palabras propias. Esta cifra no certifica todas las ramas ni proveedores.", "", "[Inventario completo](NOTEBOOK_INVENTORY_214.md) · [Reporte de regresiones](../revisions/2.1.4/grammar-dev6/REPORT.md)."])
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
md(ROOT / "docs/RUNRESULTS_LINEAGE_214.md", ["# RunResults, Memory y linaje · 2.1.4.dev6", "", "Evidencia del mismo wheel. Cero resultados puede significar configuración/CLI, no una ejecución de Agent. Los fallos esperados y pausas se conservan como tales. human_results es una proyección; el registro completo permanece en las capturas.", "", "| Fuente | RunResults capturados | Snapshots Memory | Evidencia humana/agente |", "| --- | ---: | ---: | --- |", *result_rows,
    "", "[Reporte](../revisions/2.1.4/grammar-dev6/REPORT.md) · [Inventario](NOTEBOOK_INVENTORY_214.md)."])

campaign = ROOT / "revisions/2.1.4/contracts-dev5/campaign-budget.json"
assert digest(campaign) == "6ce1ae54e97e11835598312e56ca403ca7b267478a99ce1bc5c93a0bdbd5b9e6"
previous = ROOT / "revisions/2.1.4/contracts-dev5/builds/03/agentic_systems-2.1.4.dev5-py3-none-any.whl"
assert digest(previous) == "df328e52d7a2660d7b29ce45a40c689766ce99196c02d5672930dd5663bbde34"
tests = {name: sum(int(s.get(name, 0)) for s in ET.parse(E / "offline-junit.xml").getroot().iter("testsuite")) for name in ("tests", "failures", "errors", "skipped")}
assert tests["tests"] == 353 and not any(tests[n] for n in ("failures", "errors", "skipped"))
summary = {"version": toolkit.__version__, "wheel_sha256": wheel_hash, "sdist_sha256": digest(sdist), "installed_outside_checkout": True,
    "python": platform.python_version(), "offline_tests": tests, "offline_notebooks": 28, "offline_examples": 56,
    "local_protocol_example": {"status": "passed", "protocols": [r["protocol"] for r in protocols["rows"]], "inference_requests": 0},
    "core_observed": sorted(core), "core_denominator": 16, "upstream_exports": sorted(upstream),
    "inference_requests_this_revision": 0, "published": False, "campaign_unchanged_sha256": digest(campaign),
    "previous_wheel_unchanged_sha256": digest(previous), "live_validation_transferred": False,
    "scaffolder": read(E / "scaffolder.json"), "pending": ["live acceptance of dev6 bytes", "CI Python 3.10–3.14", "vLLM GPU", "AWS IAM", "ADA IAM", "durable continuation/memory"]}
write(E / "summary.json", summary)
contracts = [
 ("1. Sin Limits/limits=/max_actions", "Exports y firmas negativas; runtime rechaza opciones retiradas"),
 ("2. Anidamiento independiente del conteo", "12 envoltorios y grafo de 260 nodos; mismo resultado sin cuota"),
 ("3. Plazo y controles", "Plazo compartido, scheduler/reintentos, intentos observados y consumo; timeout cooperativo"),
 ("4. Context directo", "Tools/nodos sync/async, Memory seleccionada y aislamiento de linaje entre ramas"),
 ("5. Contratos estrictos", "Proyección explícita, ausencias y null requerido; no defaults de reparación"),
 ("6. Continuaciones y Eval", "Trabajo completado conservado; pausa/reanudación; Eval rechaza pausa"),
 ("7. Material y scaffolder", "28 notebooks, 56 entrypoints, MCP/A2A local; proyecto generado con tres actores Python; skill validada"),
 ("8. Artefacto independiente", "Wheel/sdist nuevos, instalación externa, 119 hashes RECORD y suite offline del wheel")]
md(E / "REPORT.md", ["# Gramática única y comprobación · 2.1.4.dev6", "", "Revisión local sin publicar. Un Agent organiza una capacidad; un System coordina la aplicación. Ambos pueden tener grafos originales LangGraph; Environment añade su grafo episódico. check valida construcción, no semántica del negocio.", "",
 f"Wheel SHA-256: `{wheel_hash}`. [Wheel](builds/01/{wheel.name}) · [sdist](builds/01/{sdist.name}) · [Instalación](installation.json) · [Snapshot de fuente/commit](source-snapshot.json). El commit identifica la base; los cambios locales quedan identificados por hashes, no por atribuirlos al commit antiguo.", "",
 f"Aceptación offline con Python **{platform.python_version()}**: **353 pruebas**, **28/28 notebooks (22 tutorials + 6 examples)**, **56/56 entrypoints**, más **1 example MCP/A2A local** con SDK fixture y cero inferencia. **16/16 palabras core** ejercitadas; cinco reexportaciones LangGraph se informan aparte. [JUnit](offline-junit.xml) · [Examples](examples-offline.json) · [Protocolos](local-protocols.json) · [Resumen](summary.json).", "",
 "## Contratos y evidencia", "", "| Contrato | Comprobación |", "| --- | --- |", *[f"| {a} | {b} |" for a,b in contracts], "",
 "## Cambios y hallazgos", "", "Se retiran Limits, Action y Runtime públicos. runtime mantiene proveedor y scheduler; run(timeout_s=...) fija el plazo raíz. nodes_observed es telemetría. Tools y nodos leen *, context: toolkit.Context. check acepta los seis componentes y fábricas sync/async, devolviendo el componente original sin ejecutar el trabajo.", "",
 "Los nodos que llaman a child.run y devuelven una proyección conservan todos los resultados hijos. Una composición que ya incluye un hijo no lo duplica en el árbol. Las regresiones comprueban eventos, identidad, fallos descartados por el nodo y proyecciones de negocio. Los reintentos conservan intentos previos completos y suman consumo; no duplican toda la traza en el camino normal sin reintentos. Un timeout informa intentos reales y puede dejar un trabajador pendiente; un RunResult es una fotografía, por lo que el contador externo debe seguir activo hasta su terminación.", "",
 "La migración corrigió proyecciones Pydantic y captura de variables de nodos creados en un bucle. El ejemplo de ciclo de vida pasó de la cuota retirada a un timeout controlado. El ejemplo de instalación actualiza los exports esperados; su fallo original y repetición quedan conservados. Los intentos fuente fallidos y el guard de procesos corregido para el formato Windows están en attempts/ y source-validation/. No se relajan oráculos ni contratos para obtener PASS.", "",
 "El proyecto generado por CLI y skill ejecutó native/OpenAI Agents/Strands con Python y su notebook en kernel nuevo. [Evidencia](scaffolder.json). Studio pasó controlador, memoria y UI dentro de las 353 regresiones; esto no acredita todas las interacciones de UI ni LM reales. [MCP/A2A](local-protocols.json) usa transportes de loopback reales y modelos fixture, con conexiones externas prohibidas; ambos servicios se cierran al terminar.", "",
 "## Alcance y pendientes", "", "**Cero inferencia nueva y cero publicación.** La campaña dev5 conserva exactamente su hash: 148/150 solicitudes, USD 0.875040 reservados de USD 5. El wheel dev5 build03 conserva su hash. La aceptación live anterior no se atribuye a dev6.", "",
 "Los tests prueban contratos de los proveedores y SDK con fixtures. OpenAI, Bedrock, Ollama cloud/GPU y vLLM no se vuelven a consultar. Bedrock/null, interoperabilidad Ollama cloud, Studio/Bedrock e IAM/ADA mantienen su trabajo live pendiente; vLLM continúa aplazado. CI Python 3.10–3.14 no se ejecutó en esta tarea. Memory y continuación siguen siendo locales al proceso; no se promete persistencia durable, preempción ni rollback.", "",
 "[Ejemplo explícito](../../../examples/checked_composition/01_checked_composition.ipynb) · [API](../../../docs/API_214.md) · [Firmas](../../../docs/API_214_SURFACE.md) · [Inventario](../../../docs/NOTEBOOK_INVENTORY_214.md) · [RunResults/Memory/linaje](../../../docs/RUNRESULTS_LINEAGE_214.md)."])
md(ROOT / "docs/LEARNING_VALIDATION_214.md", ["# Validación vigente · 2.1.4.dev6", "", "[Informe del wheel](../revisions/2.1.4/grammar-dev6/REPORT.md) · [Resumen](../revisions/2.1.4/grammar-dev6/summary.json).", "", "353 regresiones, 28 notebooks, 56 entrypoints y un example MCP/A2A local; cero inferencia. Los tres actores ejecutan Python determinista. Las celdas live y servicios omitidos no quedan certificados.", "", "Toda la aceptación live de los nuevos bytes queda pendiente. No se publicó. La evidencia dev5 conserva su identidad y no se transfiere. [Estado](STATUS_214.md) · [Inventario](NOTEBOOK_INVENTORY_214.md)."])
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
    entry["validation"] = {"version": toolkit.__version__, "status": "offline-passed" if row.get("passed") else "local-protocol-passed", "entrypoint": path, "wheel_sha256": wheel_hash, "report": "revisions/2.1.4/grammar-dev6/REPORT.md"}
catalog.update(api_version=toolkit.__version__, validation_report="revisions/2.1.4/grammar-dev6/REPORT.md", reviewed_at="2026-10-28")
catalog["additional_current_examples"] = ["examples/checked_composition/example.py", "examples/applications/financial_harness/example.py", "examples/applications/financial_harness/progressive.py"]
write(p, catalog)
print(json.dumps({"tests": tests, "notebooks": len(inventory), "examples": 56, "local_protocol_example": 1, "core": len(core), "wheel_sha256": wheel_hash}))
