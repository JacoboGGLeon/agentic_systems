"""Stage reviewable teaching sources; apply at most five reviewed files per call."""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "revisions/2.1.4/contracts-dev5/teaching-review"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def without_main(source):
    tree = ast.parse(source)
    tree.body = [n for n in tree.body if not isinstance(n, ast.If)]
    return ast.unparse(tree) + "\n"


def notebook(title, source, execution, *, intro="", execution_tags=()):
    import nbformat
    cells = [nbformat.v4.new_markdown_cell("# " + title + " · 2.1.4.dev5\n\n" + intro)]
    for node in ast.parse(source).body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        text = ast.get_source_segment(source, node)
        # AST source segments omit decorators, which are part of the public lesson.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.decorator_list:
            start = node.decorator_list[0].lineno - 1
            text = "\n".join(source.splitlines()[start:node.end_lineno])
        cells.append(nbformat.v4.new_code_cell(text))
    cells.append(nbformat.v4.new_code_cell(execution, metadata={"tags": list(execution_tags)}))
    return nbformat.writes(nbformat.v4.new_notebook(cells=cells, metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    }))


class Unqualify(ast.NodeTransformer):
    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id in {"tools", "skills"}:
            return ast.copy_location(ast.Name(("skill_" if node.value.id == "skills" else "") + node.attr, node.ctx), node)
        return self.generic_visit(node)


def order_source():
    body = []
    for path in ("tools", "skills", "system", "verification"):
        tree = ast.parse(read(f"examples/order_fulfillment/{path}.py"))
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.level:
                continue
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue
            if path == "skills" and isinstance(node, ast.Assign):
                node.targets[0].id = "skill_" + node.targets[0].id
            if isinstance(node, ast.FunctionDef) and node.name in {"catalog", "load_cases"}:
                filename = "catalog.json" if node.name == "catalog" else "cases.json"
                data = json.loads(read("examples/order_fulfillment/fixtures/" + filename))
                node.body = [ast.Return(ast.parse(repr(data), mode="eval").body)]
            body.append(Unqualify().visit(node))
    body.insert(0, ast.ImportFrom(module="tutorials._offline", names=[ast.alias(name="blocked_attempts")], level=0))
    body.append(ast.parse("def run():\n    return verify()\n").body[0])
    return ast.unparse(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))) + "\n"


def build_previews():
    sources = {}
    grammar = read("examples/grammar_tour/example.py")
    for path in ("examples/flow_semantics/example.py", "examples/unified_grammar/example.py", "examples/applications/unified_grammar/example.py"):
        sources[path] = grammar
    sources["examples/framework_interop/example.py"] = read("examples/agentic_systems_studio/src/agentic_systems_studio/lab/interop.py")
    sources["examples/api_walkthrough/example.py"] = without_main(read("examples/api_214/application.py")) + "\ndef run():\n    return demonstrate()\n"
    sources["examples/order_fulfillment/example.py"] = order_source()
    episode = ast.parse(read("examples/episode_memory/example.py"))
    episode.body = [n for n in episode.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and getattr(n, "name", "") != "run"]
    class Names(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id in {"State", "Output", "build"}:
                node.id = {"State": "EpisodeState", "Output": "EpisodeOutput", "build": "build_episode"}[node.id]
            return node
        def visit_ClassDef(self, node):
            node.name = "Episode" + node.name
            return self.generic_visit(node)
        def visit_FunctionDef(self, node):
            node.name = "build_episode"
            return self.generic_visit(node)
    explicit_episode = ast.unparse(Names().visit(episode))
    evaluation = read("examples/evaluation_checks/example.py").replace("from examples.episode_memory.example import build as build_episode", explicit_episode)
    sources["examples/evaluation_checks/example.py"] = evaluation
    lifecycle = read("examples/execution_lifecycle/example.py").replace("from examples.grammar_tour.example import build", "import pydantic\n\nclass State(pydantic.BaseModel):\n    value: int\n\n@toolkit.tool\ndef increment(value: int) -> dict:\n    return {'value': value + 1}\n\n@toolkit.tool\ndef double(value: int) -> dict:\n    return {'value': value * 2}")
    lifecycle = lifecycle.replace("    unit = build()[0]", "    graph = toolkit.StateGraph(State)\n    graph.add_node('increase', increment)\n    graph.add_node('double', double)\n    graph.add_edge(toolkit.START, 'increase')\n    graph.add_edge('increase', 'double')\n    graph.add_edge('double', toolkit.END)\n    unit = toolkit.Agent('lifecycle', graph=graph)")
    sources["examples/execution_lifecycle/example.py"] = lifecycle
    controls = read("examples/execution_controls/example.py")
    studio = read(".tmp/studio-teaching-dev5.py")
    sources["examples/agentic_systems_studio/example.py"] = studio
    # Notebook construction is visible locally, including functions called later.
    specs = [
        ("tutorials/api/01_runtime_framework.ipynb", "Runtime, scheduler y framework", read("examples/validation/provider_framework_conformance/example.py"), "report = run()\nassert len(report['rows']) == 3\nprint([(row['framework'], row['result']['data']) for row in report['rows']])", "Un proveedor selecciona ejecución; un framework implementa el actor. El scheduler sigue aplicando límites y reintentos dentro del runtime. Los tres SDKs se prueban con Python determinista, sin LM."),
        ("tutorials/api/02_contracts_judges.ipynb", "Contratos, checks y juez fixture", evaluation, "report = run()\nassert report['output']['ok'] and not report['negative']['ok']\nresult = toolkit.RunResult(**report['output'])\nprint(result.human_results())", "Input value=3 → Agent calcula 4 → Eval exige el resultado y un check. El negativo espera 999 y falla aunque el juez fixture sea optimista. Environment se evalúa por separado; no es un juez semántico."),
        ("tutorials/core/07_order_challenge.ipynb", "Pedidos: siete Agents y decisiones", sources["examples/order_fulfillment/example.py"], "report = run()\nassert report['cases_passed'] == 7\nprint([(case['name'], case['ok'], case['output']) for case in report['cases']])\nresult = toolkit.RunResult(**report['cases'][0]['result'])\nprint(result.human_results())", "Se ven Tools, Skills, estados, Agents y el System completo. Input siete casos → validación → precio/inventario en paralelo → política → recibo. Environment y Eval comprueban salidas, fallos controlados y linaje. Los datos son fixtures locales, sin pedidos reales."),
        ("tutorials/frameworks/04_interoperability.ipynb", "Tres actores en un System", without_main(sources["examples/framework_interop/example.py"]), "report = run()\nresult = toolkit.RunResult(**report['output'])\nassert result.data['value'] == 45\nprint(result.human_results())", "Input 42 → cada Tool suma uno y registra native, OpenAI Agents o Strands → 45. Son SDKs reales con Python determinista. La declaración completa está aquí; no es una prueba de razonamiento LM."),
        ("examples/context_memory_lineage/01_context_memory_lineage.ipynb", "Context, Memory y linaje", read("examples/context_memory_lineage/application.py"), "report = demonstrate()\nresult = toolkit.RunResult(**report['run_results'][1])\nprint(result.human_results())\nprint(report['agent_lineage'])", "Input pedido de 125 MXN → normalizar, consultar Context y decidir → revisión. La segunda ejecución observa Memory; State y linaje conservan responsabilidades distintas. Las declaraciones y aserciones están visibles."),
        ("tutorials/api/03_execution_controls.ipynb", "Runtime y scheduler: control de ejecución", controls, "report = run()\nresult = toolkit.RunResult(**report['output'])\nprint(result.human_results())\nprint(report['runtime'])", "Input value=3 → scheduler acota el actor → System conserva resultado y evidencia. Runtime define tiempo/reintentos/turnos/Tools; Limits acota la ejecución compuesta. Un timeout no garantiza detener un trabajador. Las ramas del grafo son una decisión distinta de max_concurrency del actor."),
        ("examples/agentic_systems_studio/notebooks/01_studio.ipynb", "Studio: gramática de conversación visible", studio, "report = run()\nresult = toolkit.RunResult(**report['rows'][0]['second'])\nprint(result.human_results())", "System conversacional mínimo con los tres SDKs y Python. Input mensaje/historia → Agent y Tool → texto e historia observada. No certifica todos los controles de la interfaz. El servidor real se abre en el perfil local; instalación, controlador completo y UI tienen pruebas separadas."),
    ]
    for path, title, source, execution, intro in specs:
        sources[path] = notebook(title, source, execution, intro=intro)
    import nbformat
    studio_nb = json.loads(sources["examples/agentic_systems_studio/notebooks/01_studio.ipynb"])
    studio_nb["cells"].append(nbformat.v4.new_markdown_cell("## Interfaz real: perfil local separado\n\nRequiere instalar Studio. Este bloque comprueba inicio/parada, no todos los controles UI."))
    studio_nb["cells"].append(nbformat.v4.new_code_cell("from agentic_systems_studio.server import start_studio_server\nserver = start_studio_server(port=8503, log_dir='.tmp/studio-dev5-notebook', stop_previous=False)\ntry:\n    print(server.local_url)\nfinally:\n    server.stop()", metadata={"tags": ["local-service"]}))
    sources["examples/agentic_systems_studio/notebooks/01_studio.ipynb"] = json.dumps(studio_nb, ensure_ascii=False, indent=1)
    strands = json.loads(read("tutorials/frameworks/03_strands.ipynb"))
    strands["cells"][6]["source"] = [without_main(read("examples/patterns/strands_protocol_graph/example.py")) + "\nimport asyncio\nreport = await asyncio.to_thread(run)\nprint(report)\n"]
    sources["tutorials/frameworks/03_strands.ipynb"] = json.dumps(strands, ensure_ascii=False, indent=1)
    handoffs = json.loads(read("tutorials/frameworks/02_openai_agents.ipynb"))
    handoffs["cells"][5]["source"] = ["## Handoff, sesión y guardrail reales\n\nLa construcción SDK y toolkit está visible. Necesita OpenAI configurado y campaña autorizada. Esta celda live se omite offline; el guardrail negativo bloquea antes del modelo."]
    handoffs["cells"][6]["source"] = [read(".tmp/openai-handoff-dev5.py")]
    sources["tutorials/frameworks/02_openai_agents.ipynb"] = json.dumps(handoffs, ensure_ascii=False, indent=1)
    common = json.loads(read("examples/common_graph/01_common_graph.ipynb"))
    common["cells"][17]["source"] = [ast.get_source_segment(read("examples/common_graph/resources.py"), next(n for n in ast.parse(read("examples/common_graph/resources.py")).body if isinstance(n, ast.ClassDef) and n.name == "QuoteState")) + "\n" + "".join(common["cells"][17]["source"]).replace("from examples.common_graph.resources import QuoteState\n", "")]
    app = without_main(read("examples/common_graph/application.py"))
    common["cells"][23]["source"] = [app + "\nreports = [demonstrate(name) for name in ('native', 'openai-agents', 'strands')]\nfor report in reports:\n    print(report['framework'], report['output'])\n"]
    common["cells"][27]["source"] = ["".join(common["cells"][27]["source"]).replace("from examples.common_graph.application import build_system, CASE\n", "")]
    sources["examples/common_graph/01_common_graph.ipynb"] = json.dumps(common, ensure_ascii=False, indent=1) + "\n"
    # All current notebooks adopt the source revision without changing historical evidence.
    paths = list((ROOT / "tutorials").rglob("*.ipynb")) + [p for p in (ROOT / "examples").rglob("*.ipynb") if "history" not in p.parts]
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        content = sources.get(relative, path.read_text(encoding="utf-8"))
        nb = json.loads(content)
        for cell in nb["cells"]:
            cell["source"] = ["".join(cell["source"]).replace("2.1.4.dev4", "2.1.4.dev5")]
            if cell["cell_type"] == "code":
                cell["outputs"], cell["execution_count"] = [], None
        sources[relative] = json.dumps(nb, ensure_ascii=False, indent=1) + "\n"
    return sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", nargs="+")
    args = parser.parse_args()
    manifest_path = STAGE / "manifest.json"
    if args.apply:
        assert len(args.apply) <= 5, "Review and apply at most five files per batch"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for path in args.apply:
            row = manifest[path]
            target = ROOT / path
            assert (digest(target.read_bytes()) if target.exists() else None) == row["before"], "Source changed after preview: " + path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((STAGE / path).read_bytes())
            print("Applied reviewed source:", path)
        return
    sources = build_previews()
    manifest = {}
    for path, after in sources.items():
        target = ROOT / path
        before = target.read_bytes() if target.exists() else b""
        staged = STAGE / path
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text(after, encoding="utf-8")
        if path.endswith(".py"):
            ast.parse(after)
        else:
            for cell in json.loads(after)["cells"]:
                code = "".join(cell["source"])
                if cell["cell_type"] == "code" and "await " not in code:
                    ast.parse(code)
        diff = "".join(difflib.unified_diff(before.decode("utf-8").splitlines(True), after.splitlines(True), fromfile=path, tofile=path))
        (staged.parent / (staged.name + ".diff")).write_text(diff, encoding="utf-8")
        manifest[path] = {"before": digest(before) if target.exists() else None, "after": digest(staged.read_bytes()), "diff_lines": len(diff.splitlines())}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
