"""Organize the course; all generated lessons use the installed public API."""
import ast
from pathlib import Path
import textwrap
import nbformat as nb

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'tutorials'
PATHS = {
    '00_api.ipynb': 'core/00_start.ipynb',
    '01_tools_skills.ipynb': 'core/01_tools_skills.ipynb',
    '02_agent_flows.ipynb': 'core/02_agent_flows.ipynb',
    '03_system_flows.ipynb': 'core/03_system_flows.ipynb',
    '04_environment.ipynb': 'core/04_environment.ipynb',
    '05_eval.ipynb': 'core/05_eval.ipynb',
    '06_runtime_framework.ipynb': 'api/01_runtime_framework.ipynb',
    '07_results_limits.ipynb': 'core/06_results_limits.ipynb',
    '08_model_serving.ipynb': 'providers/04_vllm_serving.ipynb',
    '09_order_challenge.ipynb': 'core/07_order_challenge.ipynb',
    '10_contracts_judges.ipynb': 'api/02_contracts_judges.ipynb',
}


def declarations(relative, *, only=None, rename=None):
    tree = ast.parse((ROOT / relative).read_text(encoding='utf-8'))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, 'module', '') or ''
            if module == 'episode_memory.example':
                continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if only and node.name not in only:
                continue
            if rename and node.name in rename:
                node.name = rename[node.name]
        nodes.append(node)
    return ast.unparse(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])))


def cell(source, tags=()):
    return nb.v4.new_code_cell(textwrap.dedent(source).strip(), metadata={'tags': list(tags)})


def write(path, title, text, cells, *, profile='offline'):
    notebook = nb.v4.new_notebook(cells=[nb.v4.new_markdown_cell('# ' + title + '\n\n' + text),
        cell('import agentic_systems as toolkit\nassert toolkit.__version__ == "2.1.3"'), *cells], metadata={
        'kernelspec': {'display_name': 'Python · Agentic Systems 2.1.3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'},
        'agentic_systems': {'version': '2.1.3', 'canonical': True, 'profile': profile}})
    save(path, notebook)


def save(path, notebook):
    target = HOME / path
    target.parent.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(notebook.cells):
        item.id = f'{target.stem}-{index}'
    nb.write(notebook, target)


def organize():
    episode = declarations('examples/episode_memory/example.py', only={'build'}, rename={'build': 'build_episode'})
    typed = declarations('examples/tool_contracts/example.py', only=set())
    typed = typed[:typed.index('\ndef run(')].replace('def increment(', 'def validated(')
    contracts = declarations('examples/agent_contracts/example.py', rename={'run': 'contracts_example'})
    evaluation = declarations('examples/evaluation_checks/example.py', rename={'run': 'evaluation_example'})
    serving = declarations('examples/model_serving/example.py', rename={'run': 'serving_example'})
    for old, new in PATHS.items():
        path = HOME / old
        book = nb.read(path, as_version=4)
        for item in book.cells:
            if item.cell_type == 'code':
                source = item.source
                source = source.replace('from lesson_examples import validated_increment as validated', typed)
                source = source.replace('from lesson_examples import build_episode', episode)
                source = source.replace('from lesson_examples import serving_example', serving)
                source = source.replace('from lesson_examples import contracts_example', contracts)
                source = source.replace('from lesson_examples import evaluation_example', episode + '\n\n' + evaluation)
                if 'from portable_skills.example import run' in source:
                    source = ''  # The visible load_skill declaration below covers this once.
                if 'from lesson_examples import build_order_system' in source:
                    orders = (ROOT / 'examples/api_walkthrough/example.py').read_text(encoding='utf-8')
                    orders = orders[orders.index('@toolkit.tool\ndef quote'):orders.index('\ndef observed_tool_data')]
                    orders = orders.replace('backend="native", *, runtime=None, framework=None', 'backend="native"')
                    orders = orders.replace('''    if runtime is not None:
        approver = runtime_step("approver", approve, runtime, framework)
        reviewer = runtime_step("reviewer", review, runtime, framework)
''', '')
                    orders = orders.replace('build_orders(backend, runtime=runtime, framework=framework)', 'build_orders(backend)')
                    source = orders + '\n\nfor backend in ("native", "langgraph"):\n    day = build_day(backend)\n    result = day.run()\n    evaluation = evaluate_day(day).run()\n    assert result.ok and evaluation.ok and check_day(result, {})["ok"]\n    print({"backend": backend, "input": list(records), "process": "quote → decision → approve/review → memory → Eval", "output": result.data})'
                item.source = source
            else:
                item.source = item.source.replace('../docs/', '../../docs/').replace('en 10;', 'en [contratos](../api/02_contracts_judges.ipynb);')
        book.metadata['agentic_systems']['profile'] = 'offline'
        book.cells = [item for item in book.cells if item.source.strip()]
        save(new, book)
        path.unlink()

    operation = '''@toolkit.tool
def certify(value: int) -> dict:
    """Conserva el entero como evidencia exacta."""
    return {"value": value, "verified": True}

evidence = toolkit.skill(name="evidence", tools=(certify,))
'''
    actor = '''actor = toolkit.Agent(
    "verification", runtime=runtime, framework=toolkit.framework(framework),
    skills=(evidence,), instructions="Call certify exactly once with value=37.",
    contract={"tool_expectation": {"all_of": ["certify"]},
              "completion": "when_required_tools_satisfied"},
    policy={"repair": False},
)
request = {"tool": "certify", "input": {"value": 37}} if runtime.provider == "python-runtime" else "Call certify with value=37."
result = actor.run(request, limits=toolkit.Limits(timeout_s=180))
assert result.ok and result.check_invariants().ok, result.to_dict()
events = [event for node in result.walk() for event in node.tool_events]
assert any(e.name == "certify" and e.ok and e.input.get("value") == 37 for e in events)
print({"input": request, "process": "runtime + framework → certify → Tool evidence", "output": result.data})
print(result.lineage(name="verification").explain())'''
    write('providers/00_python.ipynb', 'Python Runtime',
          'Input: entero 37. Proceso: el runtime despacha la Tool indicada sin modelo de lenguaje. Output: evidencia verificable. No requiere credenciales.',
          [cell(operation), cell('runtime = toolkit.runtime(provider="python-runtime")\nframework = "native"'), cell(actor)])
    specs = [('01_openai', 'openai-runtime', 'OPENAI', 'OpenAI API key'),
             ('02_ollama', 'ollama-runtime', 'OLLAMA', 'Ollama'),
             ('03_bedrock', 'bedrock-runtime', 'BEDROCK', 'Bedrock API key')]
    for name, provider, prefix, title in specs:
        config = f'''import os
runtime = toolkit.runtime(
    provider={provider!r}, model=os.getenv({(prefix + '_MODEL_ID')!r}) or os.environ[{(prefix + '_MODEL')!r}],
    api_key=os.environ[{('AWS_BEARER_TOKEN_BEDROCK' if prefix == 'BEDROCK' else prefix + '_API_KEY')!r}],
    endpoint=os.getenv({(prefix + '_BASE_URL')!r}),
    region=(os.getenv("AWS_REGION") or os.environ["AWS_DEFAULT_REGION"]) if {prefix!r} == "BEDROCK" else None,
    max_tokens=256, max_turns=5, max_tool_calls=3, max_retries=0, timeout_s=60,
)
framework = "native"
print({{"provider": runtime.provider, "configuration": "explicit; credentials omitted"}})'''
        write('providers/' + name + '.ipynb', title,
            'Input: pedir certify(37). Proceso: el modelo debe invocar la Tool; las aserciones exigen su evento real. Output: RunResult con evidencia y linaje.\n\n'
            'Este notebook **sí ejecuta inferencia** al ejecutar todas las celdas. Configura las variables indicadas en tu entorno antes de abrir Jupyter. No imprime claves, no elige otro modelo y no reintenta. '
            'El validador offline omite las celdas marcadas live; solo la campaña autorizada acredita su ejecución. [Preparación](../../INSTALL.md).',
            [cell(operation), cell(config, ('live',)), cell(actor, ('live',))], profile='live')

    checkpoint = declarations('examples/agentic_systems_studio/src/agentic_systems_studio/lab/checkpoint.py')
    write('frameworks/01_langgraph.ipynb', 'LangGraph: checkpoint y reanudación',
        'Input: gasto de 280. Proceso: LangGraph interrumpe, guarda el estado y recibe una aprobación explícita. Output: paused=True, después approved=True. '
        'La Action conecta esa capacidad nativa con RunResult. No requiere un modelo.',
        [cell(checkpoint), cell('report = run()\nprint({"input": report["input"], "paused": report["paused"]["data"], "output": report["resumed"]["data"]})')])
    for path, title, feature in [('02_openai_agents', 'OpenAI Agents: handoff, sesión y guardrail', 'handoffs'),
                                 ('03_strands', 'Strands: MCP y A2A', 'protocols')]:
        cells = [cell(operation), cell('runtime = toolkit.runtime(provider="python-runtime")\nframework = ' + repr('openai-agents' if feature == 'handoffs' else 'strands')), cell(actor)]
        cells += [nb.v4.new_markdown_cell('La siguiente sección reutiliza el laboratorio instalado de **Studio 2.1.3**, distribuido por separado. '
            'Aquí se prueba la capacidad específica del SDK; la API común anterior sigue siendo Agent(runtime=..., framework=...). '
            '[Implementación completa](../../examples/agentic_systems_studio/src/agentic_systems_studio/lab/probes.py). '
            'En modo Python se verifica el protocolo con un modelo determinista; el modelo externo se valida en la campaña live.')]
        if feature == 'handoffs':
            cells += [cell('from agentic_systems_studio.lab.probes import handoffs\nreport = handoffs("python-runtime")\nassert report["handoff_callback"] and not report["guardrail_negative"]["ok"]\nprint(report["handoff_callback"])')]
        else:
            cells += [cell('from agentic_systems_studio.lab.probes import protocols\nfor protocol in ("mcp", "a2a"):\n    report = protocols("python-runtime", protocol, None)\n    assert report["result"]["ok"]\n    print(report["protocol"])', ('local-network',))]
        write('frameworks/' + path + '.ipynb', title,
            'Input → Agent con runtime explícito → Tool y RunResult. Después, el laboratorio muestra la capacidad distintiva del framework. '
            'Instala el extra del framework y Studio para la segunda sección. No hay fallback de proveedor.', cells)
    write('frameworks/04_interoperability.ipynb', 'Los cuatro frameworks en un System',
        'Input: value=42 y trail vacío. Proceso: native → LangGraph → OpenAI Agents → Strands, cada uno incrementa y firma el recorrido. '
        'Output: value=46 y los cuatro nombres ordenados. Python Runtime ejecuta el control sin inferencia; la campaña también prueba proveedores mixtos. '
        'La declaración está en [el ejemplo compartido](../../examples/agentic_systems_studio/src/agentic_systems_studio/lab/interop.py).',
        [nb.v4.new_markdown_cell('Este recorrido carga cuatro SDKs. Se declara un plazo de 180 s para incluir su preparación; el plazo habitual de Limits es 10 s y puede agotarse en un kernel frío.'),
         cell('from agentic_systems_studio.lab.interop import build\nframeworks = ("native", "langgraph", "openai-agents", "strands")\napp = build({name: toolkit.runtime(provider="python-runtime") for name in frameworks})\nresult = app.run({"value": 42, "trail": []}, limits=toolkit.Limits(timeout_s=180))\nassert result.ok and result.data == {"value": 46, "trail": list(frameworks), "validated": True}, result.to_dict()\nprint(result.data)\nprint(result.lineage(name="four_frameworks").explain())')])


if __name__ == '__main__':
    organize()
