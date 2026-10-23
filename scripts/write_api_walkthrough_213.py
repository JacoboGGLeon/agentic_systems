"""Author one self-contained user notebook and its shared application source."""
from pathlib import Path
import textwrap
import nbformat

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'examples/api_walkthrough'

TOOLS = '''@toolkit.tool
def increment(value: int) -> dict:
    return {"value": value + 1}

@toolkit.tool
def double(value: int) -> dict:
    return {"value": value * 2}

arithmetic = toolkit.skill(name="arithmetic", tools=(increment, double), instructions="Usa aritmética exacta.")
increase = toolkit.Action("increase", "increment")
multiply = toolkit.Action("multiply", "double")

def combine(branches):
    return {"value": sum(branch["value"] for branch in branches.values())}

def choose_next(data):
    return "multiply" if data["value"] >= 0 else "END"
'''

UNITS = '''def grammar_units(backend="native"):
    agent_sequence = toolkit.Agent("agent_sequence", toolkit.Sequence((increase, multiply)), skills=(arithmetic,), backend=backend)
    agent_parallel = toolkit.Agent("agent_parallel", toolkit.Parallel((increase, multiply), join=combine), skills=(arithmetic,), backend=backend)
    agent_decision = toolkit.Agent("agent_decision", toolkit.Graph(
        nodes=(("increase", increase), ("multiply", multiply)),
        edges=(("increase", choose_next), ("multiply", "END")), start="increase",
    ), skills=(arithmetic,), backend=backend)

    increaser = toolkit.Agent("increaser", increase, skills=(arithmetic,))
    doubler = toolkit.Agent("doubler", multiply, skills=(arithmetic,))
    system_sequence = toolkit.System("system_sequence", toolkit.Sequence((increaser, doubler)), backend=backend)
    system_parallel = toolkit.System("system_parallel", toolkit.Parallel((increaser, doubler), join=combine), backend=backend)
    system_decision = toolkit.System("system_decision", toolkit.Graph(
        nodes=(("increase", increaser), ("multiply", doubler)),
        edges=(("increase", choose_next), ("multiply", "END")), start="increase",
    ), backend=backend)
    return (agent_sequence, agent_parallel, agent_decision, system_sequence, system_parallel, system_decision)
'''

ORDER_TOOLS = '''@toolkit.tool
def quote(units: int, unit_price: int) -> dict:
    if units <= 0 or unit_price < 0:
        raise ValueError("Cantidad o precio inválidos")
    return {"total": units * unit_price}

@toolkit.tool
def approve(total: int) -> dict:
    return {"total": total, "status": "approved"}

@toolkit.tool
def review(total: int) -> dict:
    return {"total": total, "status": "manual_review"}

pricing = toolkit.skill(name="pricing", tools=(quote,))
decisions = toolkit.skill(name="decisions", tools=(approve, review))

def route_order(data):
    return "approve" if data["total"] <= 1000 else "review"

records = ({"units": 2, "unit_price": 100}, {"units": 3, "unit_price": 500})
expected = [{"total": 200, "status": "approved"}, {"total": 1500, "status": "manual_review"}]
'''

BUILD = '''def build_orders(backend="native", *, runtime=None, framework=None):
    quoter = toolkit.Agent("quoter", toolkit.Action("quote", "quote"), skills=(pricing,))
    approver = toolkit.Agent("approver", toolkit.Action("approve", "approve"), skills=(decisions,))
    reviewer = toolkit.Agent("reviewer", toolkit.Action("review", "review"), skills=(decisions,))
    if runtime is not None:
        approver = runtime_step("approver", approve, runtime, framework)
        reviewer = runtime_step("reviewer", review, runtime, framework)
    return toolkit.System("orders", toolkit.Graph(
        nodes=(("quote", quoter), ("approve", approver), ("review", reviewer)),
        edges=(("quote", route_order), ("approve", "END"), ("review", "END")), start="quote",
    ), backend=backend)

def build_day(backend="native", *, runtime=None, framework=None):
    return toolkit.Environment("day", build_orders(backend, runtime=runtime, framework=framework),
        records=records, memory={"approved": 0},
        update=lambda memory, record, result: {
            "approved": memory["approved"] + int(result.data["status"] == "approved")
        })

def check_day(result, case):
    valid = result.data["outputs"] == expected and result.data["summary"]["memory"] == {"approved": 1}
    return {"ok": valid, "issues": [] if valid else ["Resultados o memoria incorrectos"],
            "metrics": {"approved": result.data["summary"]["memory"]["approved"]}}

def evaluate_day(unit):
    return toolkit.Eval("orders_acceptance", unit,
        cases=({"input": {}, "expected": {"ok": True}},), checks=(check_day,))
'''

RUNTIME_STEP = '''def observed_tool_data(output, tool_name):
    if isinstance(output, dict) and set(output) == {"data"}:
        return output["data"]
    if (isinstance(output, dict) and {"kind", "tool_name", "ok", "data"}.issubset(output)
            and output["kind"] == "object" and output["tool_name"] == tool_name and output["ok"] is True):
        return output["data"]
    return output

def runtime_step(name, operation, runtime, framework):
    # Pass business data from observed Tool evidence; preserve the original actor.
    from dataclasses import replace
    import json
    actor = toolkit.Agent(name, runtime=runtime, framework=framework,
        skills=(toolkit.skill(name=name + "_capability", tools=(operation,)),),
        instructions="Call " + operation.name + " exactly once. Copy the supplied total unchanged. Only the Tool determines the status.",
        contract={"tool_expectation": {"all_of": [operation.name]}, "completion": "when_required_tools_satisfied"},
        policy={"repair": False})
    def execute(data):
        request = ({"tool": operation.name, "input": data} if runtime.provider == "python-runtime" else
                   "Call exactly " + operation.name + " with these unchanged arguments: " + json.dumps(data))
        result = actor.run(request, limits=toolkit.Limits(timeout_s=180))
        if not result.ok:
            return result
        events = [event for node in result.walk() for event in node.tool_events if event.name == operation.name and event.ok]
        if len(events) != 1 or events[0].input != data:
            return replace(result, ok=False, errors=(*result.errors, {"code": "business_boundary_rejected", "message": "Expected one Tool invocation with unchanged business input"}))
        output = observed_tool_data(events[0].output, operation.name)
        expected_status = "approved" if operation.name == "approve" else "manual_review"
        if output != {"total": data["total"], "status": expected_status}:
            return replace(result, ok=False, errors=(*result.errors, {"code": "business_boundary_rejected", "message": "Observed Tool evidence violates the business contract", "observed": output}))
        return replace(result, data=output)
    return toolkit.Agent(name + "_boundary", toolkit.Action(name, execute))
'''

RUN = '''def run():
    rows = []
    for backend in ("native", "langgraph"):
        for unit, value in zip(grammar_units(backend), (8, 10, 8, 8, 10, 8)):
            direct = unit.run({"value": 3})
            assert direct.ok and direct.data == unit.compile().run({"value": 3}).data == {"value": value}
            rows.append({"backend": backend, "unit": unit.name, "output": direct.data})
        episode = build_day(backend)
        result = episode.run()
        evaluation = evaluate_day(episode).run()
        assert result.ok and result.data["outputs"] == expected and evaluation.ok
    return {"rows": rows, "output": result.data["outputs"], "memory": result.data["summary"]["memory"], "inference_requests": 0}
'''


def main():
    HOME.mkdir(parents=True, exist_ok=True)
    cells = []
    def md(source):
        cells.append(nbformat.v4.new_markdown_cell(textwrap.dedent(source).strip()))
    def code(source):
        cells.append(nbformat.v4.new_code_cell(textwrap.dedent(source).strip()))
    md('''# Agentic Systems 2.1.3: de una operación a una aplicación

Un import, una interfaz de ejecución y resultados observables. Este notebook es
autónomo: todas sus celdas ejecutables son offline. Los proveedores externos solo
se configuran e inspeccionan. No se inicia GPU ni se realiza inferencia.

Recorrido: Tool → Skill → Action → Agent/System y flujos → Environment → Eval.
Después: resultados, contratos, configuración, Skills portables y serving.
''')
    code('import agentic_systems as toolkit\nassert toolkit.__version__ == "2.1.3"')
    md('## Una operación y una capacidad\nInput 3 → increment → output 4. Skill agrupa operaciones e instrucciones; Action coloca una operación en un flujo.')
    code(TOOLS)
    code('result = increment.run({"value": 3})\nassert result.ok and result.data == {"value": 4}\nresult.data')
    md('## Agent y System: los mismos tres flujos\nAgent organiza sus pasos; System coordina unidades. Sequence entrega el resultado al siguiente paso. Parallel entrega el mismo input a las ramas y combina sus salidas. Graph decide con una función Python.')
    code(UNITS)
    code('''rows = []
for backend in ("native", "langgraph"):
    for unit, expected_value in zip(grammar_units(backend), (8, 10, 8, 8, 10, 8)):
        result = unit.run({"value": 3})
        assert result.ok and result.data == {"value": expected_value}
        rows.append({"backend": backend, "unit": unit.name, "input": {"value": 3}, "output": result.data})
rows''')
    md('## run, compile, async y límites\nrun ejecuta; compile prepara la misma declaración; inspect describe. Compile e inspect no invocan modelos. Los límites son cooperativos.')
    code('''unit = grammar_units()[0]
prepared = unit.compile()
assert prepared.run({"value": 3}).data == unit.run({"value": 3}).data
assert (await prepared.arun({"value": 3})).data == {"value": 8}
result = unit.run({"value": 3}, limits=toolkit.Limits(max_actions=2, timeout_s=10))
assert result.ok
result.data''')
    md('## Integrado: aprobar o revisar pedidos\nDos pedidos sintéticos. Importes enteros: cantidad × precio. Hasta 1000 se aprueba; por encima se clasifica para revisión manual. El ejemplo registra decisiones; no transfiere dinero ni envía mensajes.')
    code(ORDER_TOOLS)
    code(BUILD)
    code('''day = build_day()
result = day.run()
assert result.ok and result.data["outputs"] == expected
{"input": list(records), "process": "quote → decisión → approve/review", "output": result.data["outputs"], "memory": result.data["summary"]["memory"]}''')
    md('## Evaluar el episodio\nEnvironment reinicia memoria en cada run. Eval vuelve a ejecutar un episodio nuevo; comprueba outputs y memoria. El check conserva una métrica approved. Aquí no hay juez de lenguaje.')
    code('''report = evaluate_day(day).run()
assert report.ok and report.data["passed"] == 1
{"ok": report.ok, "passed": report.data["passed"], "total": report.data["total"]}''')
    md('## Resultados y evidencia\nRunResult conserva data/text/final, errores, uso, eventos y ejecuciones hijas. to_dict permite intercambio JSON; walk recorre los hijos y lineage resume la evidencia.')
    code('''payload = result.to_dict()
restored = toolkit.RunResult(**payload)
assert restored.to_dict() == payload and restored.check_invariants().ok
{"data": restored.data["outputs"], "executions": len(list(restored.walk())), "lineage": restored.lineage(name="orders").to_dict()}''')
    md('## Tipos de entrada y salida\nLos contratos de Tool aceptan modelos Pydantic. El caso incorrecto debe fallar y conservar evidencia.')
    code('''from pydantic import BaseModel, StrictInt

class Quantity(BaseModel):
    value: StrictInt

@toolkit.tool(input_schema=Quantity, output_schema=Quantity)
def typed_increment(data: Quantity) -> Quantity:
    return Quantity(value=data.value + 1)

assert typed_increment.run({"value": 3}).data == {"value": 4}
assert not typed_increment.run({"value": "invalid"}).ok''')
    md('## Cargar una Skill portable\nload_skill lee una carpeta con SKILL.md y skill.py; build_skill devuelve una Skill. La carga ejecuta ese código Python local. Este ejemplo crea una carpeta temporal y no depende de rutas del repositorio.')
    code('''from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder)
    (path / "SKILL.md").write_text("# Arithmetic", encoding="utf-8")
    (path / "skill.py").write_text("import agentic_systems as toolkit\\n@toolkit.tool\\ndef inc(value:int)->dict:\\n    return {'value':value+1}\\ndef build_skill():\\n    return toolkit.skill(name='loaded',tools=(inc,))\\n", encoding="utf-8")
    loaded = toolkit.load_skill(path)
    worker = toolkit.Agent("portable", toolkit.Action("inc", "inc"), skills=(loaded,))
    assert worker.run({"value": 3}).data == {"value": 4}''')
    md('## Proveedor y framework\nbackend ejecuta el flujo de Agent/System. framework selecciona el adaptador del actor con runtime. Los nombres de proveedor son python-runtime, openai-runtime, ollama-runtime, bedrock-runtime y vllm-runtime. Los frameworks son native, langgraph, openai-agents y strands. Esta celda solo declara e inspecciona un actor; no lo ejecuta.')
    code('''model = toolkit.runtime(provider="openai-runtime", model="gpt-4.1-mini", max_tokens=256)
actor = toolkit.Agent("assistant", runtime=model, framework=toolkit.framework("openai-agents"),
    instructions="Responde usando la evidencia disponible.",
    contract={"output_schema": {"type": "object"}}, policy={"repair": False})
actor.compile().inspect()''')
    md('## La misma aplicación con actores de runtime\nLa aplicación puede recibir runtime y framework explícitos. La cotización sigue siendo determinista. El límite de aplicación siguiente verifica la llamada y usa la salida observada del Tool, conservando el actor y sus eventos. No hay inferencia en este notebook: la demostración usa python-runtime. La matriz online se ejecuta fuera del notebook, con presupuesto persistente.')
    code(RUNTIME_STEP)
    code('''python_day = build_day(runtime=toolkit.runtime(provider="python-runtime"), framework=toolkit.framework("native"))
assert python_day.run(limits=toolkit.Limits(timeout_s=60)).data["outputs"] == expected''')
    md('## Modelo desplegable y servidor\nmodel_artifact describe el modelo; model_server prepara su configuración. command es una propiedad. El ciclo operativo es start/health/stop; no se ejecuta en este notebook.')
    code('''artifact = toolkit.model_artifact("my-org/my-model")
server = toolkit.model_server(artifact)
{"artifact": artifact.inspect(), "server": server.inspect(), "command": server.command}''')
    md('''## CLI y evaluación avanzada

`agentic-systems version`, `api` y `doctor` inspeccionan; `new my_project` genera
un proyecto nuevo. No es necesario usarlos para ejecutar estos ejemplos.

Eval admite `judge=otro_agent` y `rubric` con criterios y threshold. Un juez con
modelo requiere inferencia al ejecutar el Eval. Expectativas, checks y juez se
combinan mediante AND. Los controles de protocolo del juez están en tutorials/10.

Las capacidades propias de OpenAI Agents (handoff, sesión, guardrail), LangGraph
(checkpoint/resume) y Strands (MCP/A2A) tienen pruebas externas específicas. No
se convierten en opciones portables por aceptar un diccionario de configuración.

Consulta `docs/API_213_SURFACE.md` para todas las firmas y
`docs/NOTEBOOK_INVENTORY_213.md` para el inventario y la evidencia por notebook.
''')
    for index, cell in enumerate(cells):
        cell.id = f'api-walkthrough-{index:02d}'
    notebook = nbformat.v4.new_notebook(cells=cells, metadata={
        'kernelspec': {'display_name': 'Python 3 · Agentic Systems 2.1.3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'}, 'agentic_systems': {'version': '2.1.3', 'canonical': True, 'inference': 'offline-only'}})
    nbformat.write(notebook, HOME / '01_api_user_guide.ipynb')
    (HOME / 'example.py').write_text('"""Shared declarations used by the user notebook and final validation."""\nimport agentic_systems as toolkit\n\n'
        + '\n\n'.join((TOOLS, UNITS, ORDER_TOOLS, BUILD, RUNTIME_STEP, RUN)), encoding='utf-8')
    (HOME / 'README.md').write_text('''# Toda la API, desde el usuario

Abre [01_api_user_guide.ipynb](01_api_user_guide.ipynb). Es autónomo y todas sus
celdas ejecutables son offline. Incluye los seis flujos y una aprobación de
pedidos con Tools, Skills, Agents, System, Environment y Eval.

```python
from examples.api_walkthrough.example import run

report = run()
report
```

La declaración de pedidos se comparte con la validación online; la configuración
del proveedor es explícita. El notebook no llama a proveedores externos.
[Inventario exhaustivo](../../docs/NOTEBOOK_INVENTORY_213.md).
''', encoding='utf-8')
    print(f'Wrote {len(cells)} cells and the shared application source.')


if __name__ == '__main__':
    main()
