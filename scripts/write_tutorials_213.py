"""Generate the canonical tutorials for the single 2.1.3 API."""
from pathlib import Path
import textwrap
import nbformat as nb

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "tutorials"
BOOTSTRAP = "import agentic_systems as toolkit\n"
TOOLS = '''@toolkit.tool
def increment(value: int) -> dict:
    """Suma uno de forma determinista."""
    return {"value": value + 1}

@toolkit.tool
def double(value: int) -> dict:
    """Duplica el valor."""
    return {"value": value * 2}

arithmetic = toolkit.skill(name="arithmetic", tools=[increment, double])
increase = toolkit.Action("increase", "increment")
multiply = toolkit.Action("multiply", "double")
'''
FLOW = '''def choose_next(data):
    return "multiply" if data["value"] >= 0 else "END"

def combine(branches):
    return {"value": sum(row["value"] for row in branches.values())}
'''


def write(name, title, explanation, cells):
    content = [nb.v4.new_markdown_cell(f"# {title}\n\n{explanation}\n\nAPI **2.1.3**. Cada ejemplo muestra una entrada y su resultado. Python Runtime realiza trabajo determinista."),
               nb.v4.new_code_cell(BOOTSTRAP)]
    for kind, source in cells:
        source = textwrap.dedent(source).strip()
        content.append(nb.v4.new_markdown_cell(source) if kind == "md" else nb.v4.new_code_cell(source))
    notebook = nb.v4.new_notebook(cells=content, metadata={
        "kernelspec": {"display_name": "Python 3 · Agentic Systems 2.1.3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"}, "agentic_systems": {"version": "2.1.3", "canonical": True},
    })
    for index, cell in enumerate(notebook.cells):
        cell.id = f"{name[:-6]}-{index}"
    nb.write(notebook, HOME / name)


write("00_api.ipynb", "Una sola API", "Un solo import, una forma de construir cada concepto y RunResult como salida común.", [
    ("code", '''agent = toolkit.Agent("total", toolkit.Action("sum", lambda data: {"total": sum(data["values"])}))
result = agent.run({"values": [2, 3, 5]})
result.data
'''),
    ("md", """Agent y System reciben un flujo: Sequence, Parallel o Graph. Las decisiones son funciones Python en las conexiones. `run(input)` ejecuta; `compile()` es preparación opcional, no otro modo de construir. Skills aportan capacidades. Environment entrega registros y Eval comprueba expectativas. El catálogo completo de API está en `docs/API_213.md`."""),
])
write("01_tools_skills.ipynb", "Tools y Skills", "Input 3 → Tool increment resuelta en la Skill → output 4.", [
    ("code", TOOLS),
    ("code", '''agent = toolkit.Agent(name="incrementer", flow=increase, skills=(arithmetic,))
result = agent.run({"value": 3})
assert result.ok and result.data == {"value": 4}
print({"input": {"value": 3}, "process": "Skill arithmetic → increment", "output": result.data})'''),
    ("md", """Una Skill no se ejecuta. Se asocia con `skills=(arithmetic,)`; Action resuelve la Tool por nombre. `load_skill(path)` carga una Skill portable escrita con esta misma API; requiere `SKILL.md` y `skill.py` con `build_skill()`. Es carga desde archivo, no una segunda gramática de construcción."""),
    ("code", '''from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder)
    (path / "SKILL.md").write_text("# Arithmetic", encoding="utf-8")
    (path / "skill.py").write_text("import agentic_systems as toolkit\\n@toolkit.tool\\ndef inc(value:int)->dict:\\n    return {'value':value+1}\\ndef build_skill():\\n    return toolkit.skill(name='loaded',tools=[inc])\\n", encoding="utf-8")
    loaded = toolkit.load_skill(path)
    loaded_agent = toolkit.Agent("loaded", toolkit.Action("inc", "inc"), skills=(loaded,))
    assert loaded_agent.run({"value": 3}).data == {"value": 4}
print("Skill portable cargada y ejecutada mediante Agent")'''),
])
write("02_agent_flows.ipynb", "Agent: secuencia, paralelo y decisiones", "El propietario cambia su flujo; conserva el mismo run y el mismo RunResult.", [
    ("code", TOOLS + "\n" + FLOW),
    ("code", '''for backend in ("native", "langgraph"):
    sequential = toolkit.Agent("sequential", toolkit.Sequence((increase, multiply)), skills=(arithmetic,), backend=backend)
    parallel = toolkit.Agent("parallel", toolkit.Parallel((increase, multiply), join=combine), skills=(arithmetic,), backend=backend)
    decision = toolkit.Agent("decision", toolkit.Graph(
        start="increase", nodes=(("increase", increase), ("multiply", multiply)),
        edges=(("increase", choose_next), ("multiply", "END")),
    ), skills=(arithmetic,), backend=backend)
    for agent, expected in ((sequential, 8), (parallel, 10), (decision, 8)):
        result = agent.run({"value": 3})
        assert result.ok and result.data == {"value": expected}
        print(backend, agent.name, {"input": 3, "output": result.data})
    assert decision.run({"value": -3}).data == {"value": -2}'''),
    ("md", """Secuencia: 3 → 4 → 8. Paralelo: el mismo 3 alimenta dos ramas → 4 y 6 → join suma 10. Decisión: 3 → 4 → multiply → 8; −3 → −2 → END. La condición recibe la salida del nodo anterior. El backend LangGraph construye un StateGraph real; no cambia el proveedor de agentes anidados."""),
])
write("03_system_flows.ipynb", "System: coordinar Agents", "Los mismos tres flujos, ahora con Agents como pasos.", [
    ("code", TOOLS + "\n" + FLOW),
    ("code", '''for backend in ("native", "langgraph"):
    incrementer = toolkit.Agent("incrementer", increase, skills=(arithmetic,), backend=backend)
    doubler = toolkit.Agent("doubler", multiply, skills=(arithmetic,), backend=backend)
    sequential = toolkit.System("sequential", toolkit.Sequence((incrementer, doubler)), backend=backend)
    parallel = toolkit.System("parallel", toolkit.Parallel((incrementer, doubler), join=combine), backend=backend)
    decision = toolkit.System("decision", toolkit.Graph(
        start="increase", nodes=(("increase", incrementer), ("multiply", doubler)),
        edges=(("increase", choose_next), ("multiply", "END")),
    ), backend=backend)
    for system, expected in ((sequential, 8), (parallel, 10), (decision, 8)):
        result = system.run({"value": 3})
        assert result.ok and result.data == {"value": expected}
        print(backend, system.name, result.data)
    assert decision.run({"value": -3}).data == {"value": -2}'''),
])
write("04_environment.ipynb", "Environment: episodios y pasos", "Dos inputs → la misma unidad por paso → dos outputs e historia de episodio.", [
    ("code", TOOLS),
    ("code", '''agent = toolkit.Agent("calculator", toolkit.Sequence((increase, multiply)), skills=(arithmetic,))
application = toolkit.System("team", toolkit.Sequence((agent,)))
episode = toolkit.Environment(name="two_steps", unit=application, records=({"value": 3}, {"value": -3}))
result = episode.run()
assert result.ok and result.data["outputs"] == [{"value": 8}, {"value": -4}]
assert result.data["summary"]["memory"] == {"processed": 2}
print({"input": [3, -3], "process": "un paso por registro", "output": result.data["outputs"]})'''),
    ("md", """Cada run abre un episodio nuevo. Sin observe, cada registro es el input. observe y update conectan memoria real entre pasos; stop permite terminar el episodio. Las transiciones están en `result.data['history']` y las ejecuciones de las unidades en `result.children`."""),
])
write("05_eval.ipynb", "Eval: medir resultados", "Inputs y expectativas → ejecución y comparación exacta → informe de casos.", [
    ("code", TOOLS),
    ("code", '''agent = toolkit.Agent("calculator", toolkit.Sequence((increase, multiply)), skills=(arithmetic,))
cases = ({"input": {"value": 3}, "expected": {"ok": True, "data": {"value": 8}}},
         {"input": {"value": -3}, "expected": {"ok": True, "data": {"value": -4}}})
result = toolkit.Eval(name="contract", unit=agent, cases=cases).run()
assert result.ok and result.data["passed"] == 2
wrong = toolkit.Eval("negative", agent, ({"input": {"value": 3}, "expected": {"data": {"value": 999}}},)).run()
assert not wrong.ok and wrong.data["failed"] == 1 and wrong.children[0].ok
print({"passed": result.data["passed"], "wrong_expectation_detected": not wrong.ok})'''),
    ("md", """Eval comprueba `expected.ok` y `expected.data` exactos y conserva las ejecuciones evaluadas. Rechaza claves de expectativas desconocidas. Es validación determinista, sin juez LLM. Eval recibe Agent, System o Environment. Los checks y el juez explícito se explican en 10; sin judge no hay inferencia de evaluación."""),
])
write("06_runtime_framework.ipynb", "Runtime y Framework", "Provider configura dónde se ejecuta un modelo; framework configura el loop del Agent. Backend configura su flujo.", [
    ("code", TOOLS),
    ("code", '''for name in ("native", "langgraph", "openai-agents", "strands"):
    agent = toolkit.Agent(
        name="operator", runtime=toolkit.runtime(provider="python-runtime"),
        framework=toolkit.framework(name), skills=(arithmetic,),
    )
    agent.compile()  # prepara sin instanciar ni llamar al proveedor
    result = agent.run({"tool": "increment", "input": {"value": 3}})
    assert result.ok and result.data["value"] == 4
    print(name, result.data)'''),
    ("md", """El mismo constructor Agent sirve para un flujo o para un actor con runtime explícito. Para incluir razonamiento en un flujo, coloca ese Agent como uno de sus pasos. No se infiere un proveedor ni se permite fallback automático. Las siguientes configuraciones **se declaran y no se ejecutan**: no acreditan compatibilidad live."""),
    ("code", '''configured_only = {
    name: toolkit.runtime(provider=name)
    for name in ("openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime")
}
assert set(configured_only) == {"openai-runtime", "ollama-runtime", "bedrock-runtime", "vllm-runtime"}
print({name: "configurado; no ejecutado" for name in configured_only})'''),
])
write("07_results_limits.ipynb", "RunResult, límites y preparación", "Resultado serializable y linaje en todos los límites de ejecución.", [
    ("code", TOOLS),
    ("code", '''import json
agent = toolkit.Agent("calculator", toolkit.Sequence((increase, multiply)), skills=(arithmetic,))
compiled = agent.compile()
result = compiled.run({"value": 3}, limits=toolkit.Limits(max_actions=2, timeout_s=10))
assert result.ok
encoded = json.loads(json.dumps(result.to_dict(), allow_nan=False))
assert toolkit.RunResult(**encoded).data == {"value": 8}
for node in result.walk():
    for child in node.children:
        assert child.parent_execution_id == node.execution_id
limited = agent.run({"value": 3}, limits=toolkit.Limits(max_actions=1))
assert not limited.ok
print({"output": result.data, "lineage_nodes": len(list(result.walk())), "limit_detected": not limited.ok})'''),
    ("md", """`compile()` no ejecuta Tools ni condiciones. `run()` lo llama internamente. Ambos caminos devuelven el mismo contrato; compile es preparación opcional, no otro constructor. Los límites son cooperativos y comparten reservas entre componentes; no matan un callback Python bloqueado. Agent/System también ofrecen `arun` con el mismo resultado."""),
])
write("08_model_serving.ipynb", "Artefacto y servidor de modelo", "Declarar e inspeccionar recursos no inicia un servidor ni ejecuta inferencia.", [
    ("code", '''artifact = toolkit.model_artifact("example/local-model")
server = toolkit.model_server(artifact, profile="fast")
description = server.inspect()
print(description)
assert description is not None'''),
    ("md", """`model_artifact` describe identidad y procedencia del modelo. `model_server` configura un recurso de serving con ciclo de vida explícito; `start` requiere otro trabajo y acceso al entorno GPU. Este tutorial solo inspecciona la configuración. El Agent recibe el endpoint mediante runtime; no se cambia su gramática."""),
])
write("09_order_challenge.ipynb", "Challenge completo: pedidos", "Tools → Skills → varios Agents → System con decisiones; Environment y Eval sobre la misma declaración.", [
    ("code", '''from lesson_examples import build_order_system as build_system, verify_orders as verify
import inspect
from IPython.display import Markdown, display
display(Markdown("```python\\n" + inspect.getsource(build_system) + "\\n```"))
reports = [verify(backend) for backend in ("native", "langgraph")]
assert all(report["cases_passed"] == 7 for report in reports)
for report in reports:
    for case in report["cases"]:
        print(report["backend"], case["name"], case["output"])
assert [c["output"] for c in reports[0]["cases"]] == [c["output"] for c in reports[1]["cases"]]
print("14/14 contratos; Environment y Eval 6 casos por backend; fallo técnico conservado")'''),
])



# Add focused sections without duplicating the application declarations.
def extend(name, sections):
    path = HOME / name
    notebook = nb.read(path, as_version=4)
    for kind, source in sections:
        cell = nb.v4.new_markdown_cell(textwrap.dedent(source).strip()) if kind == "md" else nb.v4.new_code_cell(textwrap.dedent(source).strip())
        notebook.cells.insert(-1, cell)
    for index, cell in enumerate(notebook.cells):
        cell.id = f"{name[:-6]}-{index}"
    nb.write(notebook, path)

extend("00_api.ipynb", [
    ("md", "Para generar un proyecto completo, consulta [la CLI](../docs/CLI_213.md). El primer recorrido solo necesita construir, ejecutar y observar el resultado."),
])
extend("01_tools_skills.ipynb", [
    ("md", "Los parámetros canónicos de contrato son input_schema y output_schema. Este ejemplo usa modelos Pydantic con StrictInt. Tool expone run, arun e inspect; no tiene compile. Una Skill expone instrucciones y capacidades, no otro ejecutor."),
    ("code", "from lesson_examples import validated_increment as validated\nassert validated.run({'value':3}).data == {'value':4}\nassert (await validated.arun({'value':3})).data == {'value':4}\nassert not validated.run({'value':'invalid'}).ok\nprint(validated.inspect())"),
    ("code", "from portable_skills.example import run as portable_example\nreport = portable_example()\nprint({'input':report['input'], 'process':report['process'], 'output':report['output']['data']})"),
])
extend("02_agent_flows.ipynb", [
    ("md", "Graph también admite ciclos limitados. La condición es una función normal; max_visits evita un ciclo ilimitado. El límite y las excepciones conservan los resultados anteriores."),
    ("code", "loop = toolkit.Agent('loop', toolkit.Graph(nodes=(('inc', increase),), edges=(('inc', lambda d: 'inc' if d['value'] < 3 else 'END'),), start='inc', max_visits=4), skills=(arithmetic,))\nassert loop.run({'value':0}).data == {'value':3}\nprint(loop.inspect())"),
])
extend("04_environment.ipynb", [
    ("md", "Input: importes 2, 3, 100. Proceso: observe combina registro y memoria; update conserva el total; stop termina al llegar a 5. Output: 2 y 5, sin procesar 100. La declaración se comparte con examples/episode_memory."),
    ("code", "from lesson_examples import build_episode\nimport inspect\nprint(inspect.getsource(build_episode))\nepisode = build_episode()\nprepared = episode.compile()\nresult = prepared.run()\nassert result.ok and result.data['summary']['memory'] == {'total':5}\nassert result.data['summary']['terminated']\nassert (await episode.arun()).data['outputs'] == result.data['outputs']\nassert (await prepared.arun()).data['outputs'] == result.data['outputs']\nprint({'input':list(episode.records),'process':prepared.inspect(),'output':result.data['outputs']})"),
])
extend("05_eval.ipynb", [
    ("md", "Eval puede medir un episodio completo. Un check recibe el RunResult y el caso y devuelve {ok, issues}. El reward de este ejemplo se calcula a partir del total final; no hay un segundo evaluador de Environment."),
    ("code", "from lesson_examples import build_episode\nevaluation = toolkit.Eval('episode',build_episode(),({'input':{},'expected':{'ok':True}},), checks=(lambda result,case: {'ok':result.data['summary']['memory']['total']==5,'issues':[]},))\nassert evaluation.run().ok\nassert (await evaluation.arun()).ok\nassert (await evaluation.compile().arun()).ok\nprint(evaluation.inspect())"),
])
extend("06_runtime_framework.ipynb", [
    ("md", "Los límites internos del actor se declaran en runtime. Limits limita el flujo completo. framework recibe opciones nativas mediante agent_kwargs y run_kwargs; las claves del ag no pueden sobrescribirse. Tener un SDK instalado o configurado no acredita un proveedor live."),
    ("code", "configured = toolkit.runtime(provider='bedrock-runtime',model='explicit-configured-only',region='us-east-1',endpoint='https://fixture.invalid',api_key='fixture-secret',timeout_s=30,max_retries=1,max_tool_calls=3,max_turns=8,max_tokens=128,backoff_s=0.1,max_concurrency=2)\nassert 'fixture-secret' not in str(configured.inspect())\nprint(configured.inspect())\noptions = toolkit.framework('openai-agents',agent_kwargs={'handoff_description':'configured-only'},run_kwargs={'context':{'tenant':'fixture'}})\nprint(options.inspect())"),
])
extend("07_results_limits.ipynb", [
    ("code", "assert (await agent.arun({'value':3})).data == result.data\nassert (await compiled.arun({'value':3})).data == result.data\nassert result.check_invariants().ok\nassert result.trace('full') == result.to_dict()\nmemory = result.lineage(name='calculator',question='What happened?',goal='Explain',tags=['offline'],metadata={'tutorial':7},max_tool_rows=2)\nprint(memory.explain())\nprint(memory.to_prompt_context(max_chars=500))\nprint(result.trace())"),
    ("md", "to_dict es el esquema de intercambio; RunResult(**payload) restaura ese contrato. walk recorre la jerarquía, trace resume ejecución y lineage proyecta evidencia para explicación. Los contadores de Tools e inferencia son distintos. raw_responses no contiene objetos SDK ni credenciales. Los timeouts son cooperativos, no cancelación fuerte."),
])
extend("08_model_serving.ipynb", [
    ("code", "from lesson_examples import serving_example\nprint(serving_example())"),
    ("md", "Después de preparar un entorno GPU, el ciclo es server.start(), server.health(), server.stop(). Este notebook no los llama. La suite offline comprueba ese ciclo con proceso y HTTP simulados. endpoint.url y endpoint.model alimentan runtime; no hay server.runtime ni otra forma de construir el Agent. extra_args no puede duplicar parámetros gestionados."),
])
write("10_contracts_judges.ipynb", "Contratos, salida estructurada y juez explícito", "Separa contrato de actor, esquema de salida y evaluación de calidad. Todos los ejemplos ejecutados aquí son deterministas.", [
    ("md", "contract declara evidencia de Tools y salida; policy declara comportamiento, runtime los límites del actor. output_schema es JSON Schema portable y sus referencias son locales. all_of, any_of, allowed, forbidden y min_count pertenecen al mismo tool_expectation; no hay helpers expect ni must_call alternativo."),
    ("code", "from lesson_examples import contracts_example\nreport = contracts_example()\nassert len(report['output'])==4\nfor row in report['output']:\n    print(row['framework'],row['positive']['ok'],row['negative']['ok'])\nprint(report['validation'])"),
    ("md", "Eval combina las expectativas, los checks y el juez requerido mediante AND. El juez es un Agent normal; recibe input, expected, resultado y evidencia. La rúbrica fija criterios y threshold. Los criterios fallidos requieren hallazgos con evidencia; un ok inconsistente no se acepta. Este juez es una fixture de protocolo: no valida semántica de ningún modelo."),
    ("code", "from lesson_examples import evaluation_example\nreport = evaluation_example()\nassert report['output']['ok'] and not report['negative']['ok'] and report['episode']['ok']\nprint({'positive':report['output']['ok'],'negative':report['negative']['ok'],'judge':report['judge_validation']})"),
])
print("Generated 11 canonical tutorials from the implemented 2.1.3 API")
