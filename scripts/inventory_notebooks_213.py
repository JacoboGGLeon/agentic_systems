"""Inventory every notebook, separating source references from execution evidence."""
import ast
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'revisions/2.1.3/closeout-evidence'
PUBLIC = ('tool', 'skill', 'load_skill', 'Action', 'Agent', 'System', 'Sequence', 'Parallel', 'Graph',
          'Environment', 'Eval', 'Limits', 'RunResult', 'runtime', 'framework', 'model_artifact', 'model_server', '__version__')
PROVIDERS = {'python-runtime', 'openai-runtime', 'ollama-runtime', 'bedrock-runtime', 'vllm-runtime'}
FRAMEWORKS = {'native', 'langgraph', 'openai-agents', 'strands'}
SEARCH = (ROOT, ROOT / 'examples', ROOT / 'tutorials', ROOT / 'examples/agentic_systems_studio/src')
RETURN_TYPES = {'tool': 'Tool', 'skill': 'Skill', 'load_skill': 'Skill', 'runtime': 'Runtime', 'framework': 'Framework',
                'model_artifact': 'Artifact', 'model_server': 'Server'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module_path(name, parent=None, level=0):
    relative = name.replace('.', '/')
    if level and parent:
        base = parent.parent
        for _ in range(level - 1):
            base = base.parent
        roots = (base,)
    else:
        roots = SEARCH
    for base in roots:
        for candidate in (base / (relative + '.py'), base / relative / '__init__.py'):
            if candidate.is_file():
                return candidate
    return None


def analyze(source, parent=None):
    result = {'elements': set(), 'legacy': set(), 'members': set(), 'calls': [], 'aliases': set(),
              'providers': set(), 'frameworks': set(), 'imports': [], 'parse_errors': []}
    sanitized = '\n'.join('' if line.lstrip().startswith(('!', '%', '?')) else line for line in source.splitlines())
    try:
        tree = ast.parse(sanitized)
    except SyntaxError as exc:
        result['parse_errors'].append({'line': exc.lineno, 'message': exc.msg})
        return result
    aliases, bindings = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'agentic_systems':
                    aliases[alias.asname or alias.name] = 'sdk'
                    result['aliases'].add(alias.asname or alias.name)
                else:
                    imported = module_path(alias.name, parent)
                    if imported:
                        result['imports'].append(imported)
        elif isinstance(node, ast.ImportFrom):
            if node.module == 'agentic_systems':
                for alias in node.names:
                    bindings[alias.asname or alias.name] = alias.name
            elif node.module and node.module.startswith('agentic_systems.'):
                result['legacy'].add('from ' + node.module)
                if node.module == 'agentic_systems.cli':
                    result['elements'].add('CLI')
                    result['legacy'].discard('from ' + node.module)
            else:
                imported = module_path(node.module or '', parent, node.level)
                if imported:
                    result['imports'].append(imported)
                # Resolve from-package imports of modules as well as functions.
                for alias in node.names:
                    name = ((node.module + '.') if node.module else '') + alias.name
                    candidate = module_path(name, parent, node.level)
                    if candidate:
                        result['imports'].append(candidate)
    def expression(node):
        if isinstance(node, ast.Name):
            return aliases.get(node.id, bindings.get(node.id))
        if isinstance(node, ast.Attribute):
            owner = expression(node.value)
            if owner:
                return node.attr if owner == 'sdk' else owner + '.' + node.attr
        if isinstance(node, ast.Call):
            name = expression(node.func)
            if name:
                base = name.split('.')[0]
                if name in RETURN_TYPES:
                    return RETURN_TYPES[name]
                if name.endswith(('.run', '.arun')):
                    return 'RunResult'
                if name.endswith('.compile'):
                    return 'Captured' if base in {'Environment', 'Eval'} else 'Compiled'
                if name == 'RunResult.lineage':
                    return 'Lineage'
                if name == 'RunResult.check_invariants':
                    return 'Validation'
                return base if base in PUBLIC else None
        return None
    # A small fixed point resolves assignments across notebook cells without execution.
    for _ in range(5):
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = expression(node.value)
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if value:
                    for target in targets:
                        if isinstance(target, ast.Name):
                            bindings[target.id] = value
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in PROVIDERS:
                result['providers'].add(node.value)
            if node.value in FRAMEWORKS:
                result['frameworks'].add(node.value)
        if isinstance(node, (ast.Attribute, ast.Name)):
            name = expression(node)
            if name:
                base = name.split('.')[0]
                if base in PUBLIC:
                    result['elements'].add(base)
                if '.' in name and base != 'sdk':
                    result['members'].add(name)
                if isinstance(node, ast.Attribute) and expression(node.value) == 'sdk' and node.attr not in PUBLIC:
                    result['legacy'].add(node.attr)
        if isinstance(node, ast.Call):
            name = expression(node.func)
            if name:
                result['calls'].append({'member': name, 'line': node.lineno, 'positional_arguments': len(node.args),
                    'keywords': [kw.arg or '**kwargs' for kw in node.keywords]})
    return result


def referenced(imports):
    visited, elements = set(), set()
    queue = [(path, 0) for path in imports]
    while queue:
        path, depth = queue.pop()
        if path in visited or depth > 6 or ROOT not in path.parents:
            continue
        if 'history' in path.parts or 'src/agentic_systems/' in path.as_posix():
            continue
        visited.add(path)
        data = analyze(path.read_text(encoding='utf-8'), path)
        elements.update(data['elements'])
        queue.extend((item, depth + 1) for item in data['imports'])
    return sorted(elements), sorted(path.relative_to(ROOT).as_posix() for path in visited)


def serializable(data):
    return {key: sorted(value) if isinstance(value, set) else value for key, value in data.items() if key != 'imports'}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    evidence_path = OUTPUT / 'notebooks.json'
    evidence = json.loads(evidence_path.read_text(encoding='utf-8')) if evidence_path.exists() else {'notebooks': []}
    executions = {row['notebook']: row for row in evidence['notebooks']}
    paths = sorted(path for folder in ('tutorials', 'examples') for path in (ROOT / folder).rglob('*.ipynb')
                   if not {'.ipynb_checkpoints', '__pycache__'}.intersection(path.parts))
    rows, member_rows = [], []
    for path in paths:
        notebook = nbformat.read(path, as_version=4)
        fragments, skipped = [], []
        for index, cell in enumerate(notebook.cells):
            if cell.cell_type != 'code':
                continue
            source = '\n'.join('' if line.lstrip().startswith(('!', '%', '?')) else line for line in cell.source.splitlines())
            try:
                if cell.source.lstrip().startswith('%%'):
                    raise SyntaxError('Cell magic; static Python analysis skipped')
                ast.parse(source)
                fragments.append(source)
            except SyntaxError as exc:
                skipped.append({'cell': index, 'message': str(exc)})
        source = '\n\n'.join(fragments)
        data = analyze(source, path)
        data['skipped_cells'] = skipped
        shared, files = referenced(data['imports'])
        current = not {'history', 'dist', 'build'}.intersection(path.relative_to(ROOT).parts)
        record = executions.get(path.relative_to(ROOT).as_posix())
        matched = bool(record and record['passed'] and record['source_sha256'] == digest(path))
        title = next((line.lstrip('# ').strip() for cell in notebook.cells if cell.cell_type == 'markdown'
                      for line in cell.source.splitlines() if line.startswith('# ')), path.stem)
        row = {'notebook': path.relative_to(ROOT).as_posix(), 'title': title, 'current': current, 'source_sha256': digest(path),
            'code_cells': sum(c.cell_type == 'code' for c in notebook.cells),
            'stored_outputs': sum(bool(c.get('outputs')) for c in notebook.cells if c.cell_type == 'code'),
            'analysis': serializable(data), 'referenced_elements': shared, 'referenced_sources': files,
            'offline': 'passed-current-source' if matched else 'pending-current-source' if current else 'historical-not-rerun',
            'execution_evidence': record['executed_notebook'] if matched else None,
            'online': 'external related campaign; notebook itself is offline' if current else 'historical scope only'}
        observed = set()
        capture_path = ROOT / record['runresults_evidence'] if matched and record.get('runresults_evidence') else None
        if capture_path and capture_path.exists():
            captured = json.loads(capture_path.read_text(encoding='utf-8'))
            def observe(value):
                if not isinstance(value, dict):
                    return
                observed.add('RunResult')
                kind = value.get('meta', {}).get('kind')
                kinds = {'agent': 'Agent', 'system': 'System', 'action': 'Action', 'sequence': 'Sequence',
                         'parallel': 'Parallel', 'graph': 'Graph', 'environment': 'Environment', 'eval': 'Eval'}
                if kind in kinds:
                    observed.add(kinds[kind])
                if value.get('meta', {}).get('skills'):
                    observed.add('skill')
                if kind == 'model':
                    observed.update(('runtime', 'framework'))
                if value.get('tool_events'):
                    observed.add('tool')
                for child in value.get('children', []):
                    observe(child)
            for item in captured['results']:
                observe(item['run_result'])
        row['observed_execution_elements'] = sorted(observed)
        rows.append(row)
        for call in data['calls']:
            member_rows.append({'notebook': row['notebook'], 'current': current, **call})
    duplicates = defaultdict(list)
    for row in rows:
        duplicates[row['source_sha256']].append(row['notebook'])
    coverage = {name: {'direct': [r['notebook'] for r in rows if r['current'] and name in r['analysis']['elements']],
                       'referenced': [r['notebook'] for r in rows if r['current'] and name in r['referenced_elements']]}
                for name in PUBLIC}
    payload = {'version': '2.1.3', 'total': len(rows), 'current': sum(r['current'] for r in rows),
        'historical': sum(not r['current'] for r in rows), 'method': 'Static AST analysis and source-hash-matched offline evidence; imported-file references do not prove an executed path',
        'limitations': ['Dynamic getattr, generated code, runtime dispatch and environment values may not be statically resolved.',
                       'Literal provider/framework strings indicate declared configuration or mentions, not successful inference.',
                       'Stored outputs in historical notebooks are not a new acceptance attestation.',
                       'Current code uses toolkit; historical notebook imports and outputs are preserved.'],
        'coverage': coverage, 'duplicates_by_bytes': [paths for paths in duplicates.values() if len(paths) > 1], 'notebooks': rows}
    (ROOT / 'docs/notebook_inventory_213.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (ROOT / 'docs/notebook_parameters_213.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['notebook', 'current', 'member', 'line', 'positional_arguments', 'keywords'])
        writer.writeheader()
        for row in member_rows:
            writer.writerow({**row, 'keywords': ', '.join(row['keywords'])})
    lines = ['# Inventario exhaustivo de notebooks 2.1.3', '',
        f"Se encontraron **{payload['total']} notebooks: {payload['current']} vigentes y {payload['historical']} históricos/generados**. Se incluyen las copias históricas, sin contarlas como ejemplos adicionales vigentes.", '',
        'La gramática directa se obtiene del AST de las celdas. Las referencias compartidas recorren archivos importados del proyecto; pueden incluir funciones que ese notebook no ejecuta. La ejecución offline exige coincidencia del hash del source. Los nombres de proveedor/framework son configuración declarada, no evidencia live.', '',
        '[JSON completo](notebook_inventory_213.json) · [Llamadas, métodos y parámetros usados](notebook_parameters_213.csv) · [Informe de cierre](../revisions/2.1.3/closeout-evidence/REPORT.md)', '']
    for label, predicate in [('Tutorials vigentes', lambda r: r['current'] and r['notebook'].startswith('tutorials/')),
                             ('Examples vigentes', lambda r: r['current'] and r['notebook'].startswith('examples/')),
                             ('Históricos y generados anteriores', lambda r: not r['current'])]:
        lines += ['## ' + label, '', '| Notebook | Gramática directa | Observada en RunResult | Referencias en módulos importados (no equivale a enseñanza) | Providers/frameworks declarados | Estado |', '|---|---|---|---|---|---|']
        for row in rows:
            if not predicate(row):
                continue
            direct = ', '.join(row['analysis']['elements']) or 'Sin llamadas directas al SDK'
            if not row['current'] and row['analysis']['legacy']:
                direct += '; anteriores: ' + ', '.join(row['analysis']['legacy'])
            shared = ', '.join(row['referenced_elements']) or '—'
            choices = ', '.join(row['analysis']['providers'] + row['analysis']['frameworks']) or 'Dinámico/no declarado'
            state = 'Offline: pasa' if row['offline'] == 'passed-current-source' else 'Pendiente' if row['current'] else 'Historia; no reejecutado'
            observed = ', '.join(row['observed_execution_elements']) or 'Sin ejecución de unidades observada'
            lines.append(f"| [{row['notebook']}](../{row['notebook']}) | {direct} | {observed} | {shared} | {choices} | {state} |")
        lines.append('')
    lines += ['## Cobertura por palabra de la API', '', '| Elemento | Notebooks con referencia directa | Con referencia en archivos compartidos |', '|---|---:|---:|']
    lines += [f"| `{name}` | {len(data['direct'])} | {len(data['referenced'])} |" for name, data in coverage.items()]
    lines += ['', 'El JSON conserva la lista inversa por elemento, miembros, keywords por llamada, aliases, errores de parseo, hashes y módulos compartidos. El CSV permite filtrar cada método y parámetro usado. Esta cobertura no implica enseñar cada valor posible de los parámetros.', '', '## Límites y pendientes', '']
    lines += ['- ' + item for item in payload['limitations']]
    lines += ['', 'vLLM/Colab, AWS IAM y ADA IAM mantienen la validación en su entorno como pendiente. OpenAI, Ollama y Bedrock API key se contrastan con los cuatro frameworks en la campaña externa. El notebook de usuario permanece seguro de ejecutar offline.', '']
    (ROOT / 'docs/NOTEBOOK_INVENTORY_213.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'total': payload['total'], 'current': payload['current'], 'historical': payload['historical'],
                      'offline_passed': sum(r['offline'] == 'passed-current-source' for r in rows),
                      'direct_api_coverage': [name for name, data in coverage.items() if data['direct']]}))


if __name__ == '__main__':
    main()
