"""Generate current API/learning reports from dev5 artifact-bound evidence."""
import ast
import dataclasses
from decimal import Decimal
import hashlib
import inspect
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "revisions/2.1.4/contracts-dev5"
SITE = ROOT / ".tmp/candidate214-dev5-build02/site-packages"
sys.path.insert(0, str(SITE))
import agentic_systems as toolkit  # noqa: E402


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def md(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert toolkit.__version__ == "2.1.4.dev5" and Path(toolkit.__file__).resolve().is_relative_to(SITE)
wheel = E / "builds/02/agentic_systems-2.1.4.dev5-py3-none-any.whl"
wheel_hash = digest(wheel)
with zipfile.ZipFile(wheel) as archive:
    for name in archive.namelist():
        if name.startswith("agentic_systems/") and not name.endswith("/"):
            assert archive.read(name) == (SITE / name).read_bytes(), name
            assert archive.read(name) == (ROOT / "src" / name).read_bytes(), name
    assert not any("__pycache__" in name or name.endswith(".pyc") for name in archive.namelist())
write(E / "builds/02/hashes.json", {p.name: digest(p) for p in wheel.parent.iterdir() if p.suffix in {".whl", ".gz"}})
upstream = {"StateGraph", "START", "END", "Runtime", "Command", "Send"}
core = set(toolkit.__all__) - upstream - {"__version__"}
latest = {}
for file in sorted((E / "notebook-runs").glob("*/results.json")):
    for row in read(file):
        latest[(row["path"], row["profile"], row["framework"])] = {**row, "results_file": file.relative_to(ROOT).as_posix()}
offline = {key[0]: value for key, value in latest.items() if key[1] == "offline"}
assert len(offline) == 27 and all(r["passed"] for r in offline.values())
assert all(r.get("capture_schema") == "recursive-results-memory.v2" for r in offline.values())
examples = read(E / "examples-offline.json")
assert sum(r["passed"] is True for r in examples["rows"]) == 54
assert not examples["offline_guard_blocked_attempts"]
assert read(E / "local-protocols.json")["inference_requests"] == 0
inventory, used, lineage_rows, visibility = [], set(), [], []


def result_report(path, captured, memories=None):
    results = {}
    for name, payload in captured.items():
        value = toolkit.RunResult(**payload)
        assert value.check_invariants().ok
        contexts = [r.meta["context"] for r in value.walk() if "context" in r.meta]
        results[value.execution_id] = {"source_name": name, "status": value.status, "ok": value.ok,
            "human_results": value.human_results(max_steps=4, max_chars=1600),
            "agent_lineage": value.lineage().to_prompt_context(), "context_memory_observations": contexts}
    target = E / "lineage" / (path.replace("/", "--") + ".json")
    write(target, {"source": path, "wheel_sha256": wheel_hash, "results": results, "memory_snapshots": memories or {}})
    observed = sum(bool(c.get("episode_ids") or c.get("memory_revision") is not None)
                   for r in results.values() for c in r["context_memory_observations"])
    lineage_rows.append(f"| [{path}](../{path}) | {len(results)} | {len(memories or {})} / {observed} | [JSON](../{target.relative_to(ROOT).as_posix()}) |")


for path, row in sorted(offline.items()):
    nb = read(ROOT / path)
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    assert hashlib.sha256(code.encode()).hexdigest() == row["code_sha256_before_parameterization"], path
    tree = ast.parse(code)
    hidden = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
              and (n.module or "").startswith(("examples.", "agentic_systems_studio."))
              and any(a.name in {"run", "build", "verify", "demonstrate", "build_system", "build_conversational_system", "handoffs"} for a in n.names)]
    assert not hidden, path
    captured = read(E / row["capture"].replace("\\", "/"))
    words = set(captured["grammar"]["combined"]["used"])
    used.update(words)
    declared = sorted({n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                       and isinstance(n.value, ast.Name) and n.value.id == "toolkit"})
    calls = [{"call": ast.unparse(n.func), "parameters": [k.arg or "**kwargs" for k in n.keywords]}
             for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    item = {"path": path, "offline_passed": True, "core_words_observed": sorted(words & core),
            "upstream_words_observed": sorted(words & upstream), "toolkit_attributes_declared": declared,
            "calls_and_parameters": calls, "skipped_cells": row["skipped_cells"],
            "source_sha256": row["code_sha256_before_parameterization"], "evidence": row["results_file"],
            "capture": row["capture"], "hidden_builder_imports": hidden}
    inventory.append(item)
    visibility.append({"path": path, "toolkit_attributes": declared, "hidden_builders": hidden})
    result_report(path, captured.get("run_results", {}), captured.get("memories"))
for row in examples["rows"]:
    if row["passed"] is True:
        assert digest(ROOT / row["path"]) == row["source_sha256"], row["path"]
        result_report(row["path"], {str(i): r for i, r in enumerate(row.get("run_results", []))})
write(E / "visibility-after.json", visibility)
write(ROOT / "docs/NOTEBOOK_INVENTORY_214.json", {"version": toolkit.__version__, "wheel_sha256": wheel_hash,
    "core_denominator": len(core), "core_observed": sorted(used & core), "notebooks": inventory})
md(ROOT / "docs/NOTEBOOK_INVENTORY_214.md", ["# Inventario de notebooks · 2.1.4.dev5", "",
    "22 tutorials + 5 examples ejecutados offline con el mismo wheel. Cada construcción relevante está visible. Celdas live/local omitidas no quedan validadas por esta pasada. La cobertura cuenta llamadas reales y distingue el init compartido de Pydantic.", "",
    "[Métodos y parámetros por notebook](NOTEBOOK_INVENTORY_214.json) · [Firmas](API_214_SURFACE.md) · [Informe](../revisions/2.1.4/contracts-dev5/REPORT.md).", "",
    "| Notebook | Vocabulario core observado | Celdas omitidas offline |", "| --- | --- | ---: |",
    *[f"| [{r['path']}](../{r['path']}) | {', '.join('`'+w+'`' for w in r['core_words_observed'])} | {len(r['skipped_cells'])} |" for r in inventory], "",
    f"Unión core: **{len(used & core)}/{len(core)}**. No equivale a cubrir todos los parámetros, ramas o proveedores."])
md(ROOT / "docs/RUNRESULTS_LINEAGE_214.md", ["# RunResults, linaje y Memory · 2.1.4.dev5", "",
    "Evidencia del wheel dev5; todos los RunResults capturados pasan invariantes. Los controles negativos conservan sus fallos esperados. Se capturan resultados anidados en reports, sin contar sus hijos como experimentos independientes. JSON incluye human_results, linaje para agentes y contexto/revisiones de Memory observados.", "",
    "La columna Memory distingue snapshots capturados de observaciones de contexto con revisión/episodios. Cero significa ausencia de esa captura, no una memoria inventada ni prueba de que nunca se usó. Los casos de configuración/CLI pueden no producir RunResult.", "",
    "| Archivo | RunResults únicos | Memory snapshots / observaciones | Evidencia |", "| --- | ---: | ---: | --- |", *lineage_rows,
    "", "MCP/A2A tiene un [perfil local separado](../revisions/2.1.4/contracts-dev5/local-protocols.json), sin LM. [Alcance online](../revisions/2.1.4/contracts-dev5/REPORT.md)."])
md(ROOT / "docs/GRAMMAR_COVERAGE_214.md", ["# Cobertura de gramática · 2.1.4.dev5", "",
    f"Los notebooks ejecutan **{len(used & core)}/{len(core)}** constructores/funciones propios: " + ", ".join(f"`{w}`" for w in sorted(used & core)) + ".", "",
    "LangGraph aporta seis reexportaciones originales. Su API de métodos no se cuenta como palabras nuevas propias. La medición no es certificación exhaustiva de semántica, parámetros, proveedores ni GPU.", "",
    "[Inventario](NOTEBOOK_INVENTORY_214.md) · [Firmas](API_214_SURFACE.md)."])

surface, signatures = ["# API observada del wheel · 2.1.4.dev5", "", "17 constructores/funciones core, seis reexportaciones de LangGraph y __version__. No se añadieron constructores. Pydantic se importa directamente. Las firmas provienen del wheel instalado, sin inferencia."], {}
for name in sorted(core):
    obj = getattr(toolkit, name)
    signature = re.sub(r"0x[0-9A-Fa-f]+", "<address>", str(inspect.signature(obj)))
    methods = {n: str(inspect.signature(v)) for n, v in inspect.getmembers(obj)
               if not n.startswith("_") and inspect.isfunction(v)} if inspect.isclass(obj) else {}
    signatures[name] = {"signature": signature, "methods": methods}
    surface.extend(["", "## " + name, "", "```python", name + signature, "```", *[f"- `{n}{s}`" for n, s in methods.items()]])
factories = {"runtime": toolkit.runtime(provider="python-runtime"), "framework": toolkit.framework("native"),
             "Limits": toolkit.Limits(), "policy": toolkit.Agent("schema", runtime=toolkit.runtime(provider="python-runtime"), policy={}).policy}
for name, value in factories.items():
    signatures.setdefault(name, {})["pydantic_schema"] = value.model_json_schema()
def echo_schema(value: int) -> dict:
    return {"value": value}
sample_tool = toolkit.tool(echo_schema)
artifact = toolkit.model_artifact("Qwen/Qwen2.5-0.5B-Instruct", revision="main")
returned = {**factories, "tool": sample_tool,
            "skill": toolkit.skill(name="schema", tools=(sample_tool,)),
            "model_artifact": artifact, "model_server": toolkit.model_server(artifact),
            "RunResult.lineage": toolkit.RunResult().lineage(),
            "RunResult.check_invariants": toolkit.RunResult().check_invariants()}
surface.extend(["", "## Objetos devueltos y protocolo Pydantic", "",
    "Inspección sin inferencia ni inicio de servidores. Las clases privadas no se construyen directamente. Los métodos heredados de Pydantic se identifican como tales; model_construct omite validación y no se usa para configurar ejecuciones."])
for name, value in returned.items():
    members = {}
    for method in dir(type(value)):
        if method.startswith("_"):
            continue
        member = getattr(type(value), method)
        if inspect.isfunction(member) or inspect.ismethod(member):
            try:
                members[method] = str(inspect.signature(member))
            except (TypeError, ValueError):
                members[method] = "(signature unavailable)"
    attrs = list(getattr(type(value), "model_fields", {}))
    if dataclasses.is_dataclass(value):
        attrs += [field.name for field in dataclasses.fields(value) if not field.name.startswith("_")]
    attrs += [n for n, member in inspect.getmembers(type(value)) if isinstance(member, property) and not n.startswith("_")]
    signatures.setdefault(name, {})["returned_object"] = {"attributes": sorted(set(attrs)), "methods": members}
    surface.extend(["", "### " + name, "", "Atributos: " + ", ".join(f"`{a}`" for a in sorted(set(attrs))) + ".", "",
                    *[f"- `{n}{sig}`" for n, sig in members.items()]])
surface.extend(["", "## Contratos Pydantic", "", "runtime/framework/Limits y policy usan validación Pydantic. Los objetos devueltos admiten model_dump, model_dump_json y model_json_schema; otros métodos heredados pertenecen al protocolo Pydantic. La policy no tiene constructor raíz nuevo. Los secretos se excluyen de los datos serializados. Objetos SDK vivos se describen, no se reconstruyen desde JSON.", "",
    "El programa devuelto por compile ofrece run/arun, inspect y resume/aresume. Continuaciones locales al proceso. [Controles y precedencia](RUNTIME_SCHEDULER_214.md).", "",
    "## LangGraph", "", "StateGraph, START, END, Runtime, Command y Send son los objetos originales. [API de usuario y objetos de fábricas](API_214.md)."])
write(E / "api-signatures.json", signatures)
md(ROOT / "docs/API_214_SURFACE.md", surface)

online, all_attempts = {}, []
for path in sorted((E / "online").glob("*/results.json")):
    payload = read(path)
    assert payload["wheel_sha256"] == wheel_hash
    for row in payload["rows"]:
        item = {**row, "evidence": path.relative_to(ROOT).as_posix()}
        online[(row["name"], row["route"], row["framework"])] = item
        all_attempts.append(item)
ledger = read(E / "campaign-budget.json")
budget = {"requests": len(ledger["attempts"]), "request_limit": ledger["limits"]["requests"],
          "reserved_usd": str(sum((Decimal(r["reserved_usd"]) for r in ledger["attempts"]), Decimal(0))),
          "usd_limit": ledger["limits"]["usd"]}
assert budget["requests"] <= 150 and Decimal(budget["reserved_usd"]) <= 5
tests = {key: sum(int(s.get(key, 0)) for s in ET.parse(E / "offline-junit.xml").getroot().iter("testsuite"))
         for key in ("tests", "errors", "failures", "skipped")}
assert tests["errors"] == tests["failures"] == tests["skipped"] == 0
summary = {"version": toolkit.__version__, "wheel_sha256": wheel_hash, "build": "02", "published": False,
    "offline_tests": tests, "offline_notebooks": len(offline), "offline_examples": 54, "local_protocol_examples": 1,
    "core_words_observed": len(used & core), "core_denominator": len(core), "budget": budget,
    "online_latest": list(online.values()), "online_all_attempts": all_attempts,
    "online_latest_failures": [r for r in online.values() if not r["passed"] and not r.get("not_attempted")],
    "online_pending": [r for r in online.values() if r.get("not_attempted")]}
write(E / "summary.json", summary)
lines = ["# Contratos y aprendizaje explícito · 2.1.4.dev5", "", "Candidata local sin publicar. LangGraph orquesta; runtime y scheduler conservan el control del actor. Pydantic valida configuración y estados. Se eliminaron imports de constructores ocultos en la enseñanza, sin añadir vocabulario raíz.", "",
    f"Wheel SHA-256: `{wheel_hash}`. [Wheel](builds/02/{wheel.name}) · [sdist](builds/02/agentic_systems-2.1.4.dev5.tar.gz) · [Hashes](builds/02/hashes.json).", "",
    f"Offline: **{tests['tests']} pruebas**, **27/27 notebooks**, **54/54 entrypoints** y **1 perfil MCP/A2A local sin LM**. [JUnit](offline-junit.xml) · [Ejemplos](examples-offline.json) · [Visibilidad](visibility-after.json).", "",
    f"Vocabulario propio ejercitado: **{len(used & core)}/{len(core)}**. La cifra no acredita cada parámetro ni todas las rutas.", "",
    "## Online: resultados de cada escenario", "", "Todos se vinculan al mismo wheel. Los primeros fallos de autenticación Bedrock y todos los intentos permanecen en el [resumen](summary.json). La tabla usa el intento más reciente del mismo caso/ruta/actor; no sustituye un caso por otro.", "",
    "| Escenario | Ruta | Actor | Resultado |", "| --- | --- | --- | --- |"]
for row in online.values():
    status = "PASS" if row["passed"] else "PENDIENTE (no ejecutado)" if row.get("not_attempted") else "FAIL"
    lines.append(f"| {row['name']} | {row['route']} | {row['framework']} | {status} |")
lines.extend(["", f"Consumo: **{budget['requests']}/150 solicitudes**, **USD {budget['reserved_usd']}/5 reservados**. Reserva conservadora, no factura. [Contador](campaign-budget.json). La campaña anterior no se reinició ni modificó.", "",
    "## Correcciones y límites", "", "Build 01 queda conservado como intento anterior. Se corrigió en build 02 la proyección Strands que perdía campos de negocio cuando una Tool devolvía text. Tres regresiones con SDKs reales/Python verifican text, answer, evidence, nulos y un ok de negocio. Se repitieron pruebas sobre los nuevos bytes; la evidencia build 01 no los certifica.", "",
    "El primer ejemplo conversacional tenía un esquema history abierto incompatible con Tools estrictas: se declaró Message con Pydantic. El ejemplo de controles tenía deadlines de 2/5 segundos insuficientes para imports en kernel frío; ahora usa 30/60. Las pruebas específicas de timeout/reintento conservan sus límites pequeños y sus negativos. Los intentos originales permanecen en attempts/ y notebook-runs/.", "",
    "Las 15 pruebas de negocio online son proyecciones de sus Tools con entradas/oráculos exactos y asignación rotativa; no son todas las combinaciones ni una ejecución LM de todos los grafos originales. Los grafos deterministas completos están ejecutados offline. Studio online prueba controlador, historial y calculadora, no todos los recorridos de UI.", "",
    "vLLM está aplazado por decisión del usuario. AWS IAM y ADA IAM, persistencia durable, recuperación tras reinicio, API RL completa y streaming público no quedan certificados. Un fallo obligatorio de negocio sigue bloqueando aceptación; un PASS básico no lo resuelve. CI Python 3.10–3.14 y promoción de artefactos estables siguen pendientes.", "",
    "[Runtime/scheduler](../../../docs/RUNTIME_SCHEDULER_214.md) · [System/harness](../../../docs/SYSTEM_HARNESS_214.md) · [Ruta de aprendizaje](../../../docs/LEARNING_PATH_214.md) · [Inventario](../../../docs/NOTEBOOK_INVENTORY_214.md) · [RunResults/Memory/linaje](../../../docs/RUNRESULTS_LINEAGE_214.md)."])
md(E / "REPORT.md", lines)
md(ROOT / "docs/LEARNING_VALIDATION_214.md", ["# Validación vigente · 2.1.4.dev5", "",
    "La fuente de resultados es el [informe del wheel dev5](../revisions/2.1.4/contracts-dev5/REPORT.md) y su [resumen completo](../revisions/2.1.4/contracts-dev5/summary.json).", "",
    f"Offline: {tests['tests']} pruebas, 27 notebooks, 54 entrypoints y un perfil de protocolos locales sin inferencia. Online: {sum(r['passed'] for r in online.values())} escenarios recientes aprobados, {sum(not r['passed'] and not r.get('not_attempted') for r in online.values())} fallidos y {sum(bool(r.get('not_attempted')) for r in online.values())} pendientes sin ejecutar; revisar cada caso en el informe.", "",
    "La matriz básica no certifica todos los escenarios avanzados. vLLM está aplazado; IAM/ADA no están certificados. La aceptación estable exige resolver fallos obligatorios, CI multiversión y artefactos sellados. No se publicó.", "",
    "Las cifras dev3/dev4 conservan su identidad en revisions/. [Estado](STATUS_214.md) · [Release](RELEASE_214.md)."])
print(json.dumps({"offline_tests": tests, "notebooks": 27, "examples": 54, "core": len(used & core), "online_latest": len(online), "online_passed": sum(r['passed'] for r in online.values()), "budget": budget, "wheel_sha256": wheel_hash}))
