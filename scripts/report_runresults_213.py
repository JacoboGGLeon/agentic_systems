"""Publish compact observed results and lineage with complete JSON evidence links."""
import hashlib
import json
from pathlib import Path
import agentic_systems as toolkit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'revisions/2.1.3/closeout-evidence'
DOC = ROOT / 'docs/RUNRESULTS_LINEAGE_213.md'
EXCLUDED = {'history', 'dist', 'build', '__pycache__', '.ipynb_checkpoints'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def compact(value, depth=0):
    if depth >= 3:
        return f'[{len(value)} elementos; ver JSON]' if isinstance(value, (list, dict)) else value
    if isinstance(value, dict):
        selected = list(value.items())[:8]
        return {key: compact(item, depth + 1) for key, item in selected}
    if isinstance(value, list):
        return [compact(item, depth + 1) for item in value[:3]] + ([f'{len(value)-3} más; ver JSON'] if len(value) > 3 else [])
    if isinstance(value, str) and len(value) > 250:
        return value[:250] + '… [ver JSON]'
    return value


def walk(result):
    yield result
    for child in result.get('children', []):
        yield from walk(child)


def link(path):
    return '../' + path.relative_to(ROOT).as_posix()


def find_results(value):
    if isinstance(value, dict):
        if 'execution_id' in value and 'children' in value and 'ok' in value:
            yield value
        else:
            for item in value.values():
                yield from find_results(item)
    elif isinstance(value, list):
        for item in value:
            yield from find_results(item)


def describe(title, source, evidence, payload):
    rows = payload.get('results', [])
    lines = ['## ' + title, '', f'[Fuente]({link(source)}) · [RunResult y lineage completos]({link(evidence)})', '',
             f"Resultados raíz observados: **{len(rows)}**. Las ejecuciones hijas se conservan dentro de sus padres.", '']
    if not rows:
        lines += ['**Sin RunResult ni lineage de ejecución.** Este ejemplo configura, inspecciona o genera archivos. No se fabricó una ejecución para completar la tabla.', '']
        return lines
    lines += ['| Execution ID | ok | Unidad | Eventos de Tools en el árbol | Ejecuciones en el árbol | Invariantes |', '|---|---|---|---:|---:|---|']
    for row in rows:
        result = row['run_result']
        nodes = list(walk(result))
        events = sum(len(node.get('tool_events', [])) for node in nodes)
        unit = str(result.get('meta', {}).get('name', result.get('engine', ''))).replace('|', '\\|')
        lines.append(f"| `{result['execution_id']}` | {result['ok']} | {unit} | {events} | {len(nodes)} | {row.get('invariants', {}).get('ok', 'no disponible')} |")
    # Show one complete business trajectory in compact form; every other result
    # remains individually indexed above and present in the linked JSON.
    representative = max(rows, key=lambda row: len(list(walk(row['run_result']))))
    result, memory = representative['run_result'], representative.get('lineage_memory')
    view = {key: result.get(key) for key in ('execution_id', 'ok', 'engine', 'model')}
    view.update({'data': compact(result.get('data')), 'usage': compact(result.get('usage')), 'errors': compact(result.get('errors'))})
    lines += ['', 'RunResult representativo, proyección resumida:', '', '```json', json.dumps(view, ensure_ascii=False, indent=2), '```', '']
    if memory is not None:
        steps = memory.get('steps', [])
        memory_view = {key: compact(memory.get(key)) for key in ('name', 'ok', 'question', 'goal', 'answer', 'usage', 'schema_version')}
        memory_view['total_steps'] = len(steps)
        memory_view['steps_sample'] = [{'kind': item.get('kind'), 'title': item.get('title'), 'summary': compact(item.get('summary'))}
                                       for item in steps[:8]]
        lines += ['Lineage memory de esa misma ejecución, proyección resumida:', '', '```json', json.dumps(memory_view, ensure_ascii=False, indent=2), '```', '']
    else:
        lines += ['Lineage no disponible: `' + str(representative.get('lineage_error')) + '`.', '']
    return lines


def main():
    notebooks = read(OUTPUT / 'notebooks.json')['notebooks']
    sections, records = [], []
    for source in sorted((ROOT / 'examples').rglob('example.py')):
        if EXCLUDED.intersection(source.relative_to(ROOT).parts):
            continue
        evidence = source.parent / 'evidence/runresults.json'
        title = source.parent.relative_to(ROOT).as_posix()
        if not evidence.exists():
            records.append({'source': title, 'status': 'missing-capture', 'root_results': 0})
            sections += ['## ' + title, '', 'Captura pendiente. No se declara validado por este informe.', '']
            continue
        payload = read(evidence)
        records.append({'source': title, 'status': 'captured', 'root_results': len(payload['results']),
                        'evidence': evidence.relative_to(ROOT).as_posix()})
        sections += describe(title, source, evidence, payload)
    sections += ['# Tutorials y notebooks de examples', '']
    for row in notebooks:
        source = ROOT / row['notebook']
        assert row['source_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
        evidence = ROOT / row['runresults_evidence']
        payload = read(evidence)
        records.append({'source': row['notebook'], 'status': 'captured', 'root_results': len(payload['results']),
                        'evidence': evidence.relative_to(ROOT).as_posix()})
        sections += describe(row['notebook'], source, evidence, payload)
    online = []
    destination = OUTPUT / 'online-lineage'
    destination.mkdir(exist_ok=True)
    for phase in ('matrix', 'features', 'integrated', 'studio', 'studio-ui'):
        summary = OUTPUT / (phase + '.json')
        if not summary.exists():
            continue
        phase_data = read(summary)
        for source in sorted((ROOT / phase_data['attempt_directory']).glob('*.json')):
            if source.name == 'summary.json':
                continue
            raw = read(source)
            results = []
            for result in find_results(raw.get('report', {})):
                restored = toolkit.RunResult(**result)
                results.append({'run_result': result, 'lineage_memory': restored.lineage(name=phase + '/' + raw['name']).to_dict(),
                                'invariants': restored.check_invariants().to_dict()})
            target = destination / (phase + '--' + source.name)
            target.write_text(json.dumps({'source_evidence': source.relative_to(ROOT).as_posix(), 'results': results}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            online.append({'phase': phase, 'case': raw['name'], 'passed': raw['passed'], 'root_results': len(results),
                           'evidence': target.relative_to(ROOT).as_posix(), 'wheel_sha256': phase_data['wheel_sha256']})
    total_roots = sum(row['root_results'] for row in records)
    lines = ['# RunResult y Lineage Memory: evidencia de 2.1.3', '',
             'Cada ejecución conserva qué produjo y cómo llegó al resultado. Este informe presenta proyecciones pequeñas de los RunResult y de su memoria de linaje; cada sección enlaza el JSON íntegro con todos los resultados y sus hijos.', '',
             f"Cobertura: **{len(records)} unidades de documentación/ejemplo**, **{total_roots} resultados raíz offline observados**. Las fichas y wrappers que reutilizan una declaración se identifican por su fuente; estos conteos no son aplicaciones independientes ni llamadas facturables.", '',
             'Los `ok=False` se muestran: existen controles negativos, entradas inválidas y fallos deliberados. Que el example pase sus aserciones no significa que todos sus candidatos deban aprobar. Los ejemplos de configuración o scaffolding pueden tener cero RunResult y cero lineage; se indican expresamente.', '',
             'Environment.memory mantiene el estado del episodio. Lineage Memory describe la ejecución registrada, sus pasos, decisiones y evidencia; se obtiene mediante `result.lineage(...).to_dict()`. Los límites del validador observan los resultados sin sustituir sus valores. Las proyecciones de este MD abrevian colecciones y texto; los JSON conservan la evidencia completa.', '',
             '[Inventario de notebooks y gramática](NOTEBOOK_INVENTORY_213.md) · [Cierre, presupuesto y artefactos](../revisions/2.1.3/closeout-evidence/REPORT.md)', '',
             '# Examples: programas ejecutables', '']
    lines += sections
    lines += ['# Providers y frameworks: resultados online y memoria', '',
              'La campaña externa conserva resultados por combinación; no convierte los notebooks offline en ejecuciones de modelos. Los servicios MCP/A2A son locales reales con agentes remotos deterministas. El uso de inferencia se contabiliza en el ledger, sin sumar árboles anidados como si fueran llamadas nuevas.', '',
              '| Fase | Caso | Pasa | RunResult raíz | Evidencia completa con lineage |', '|---|---|---|---:|---|']
    lines += [f"| {row['phase']} | {row['case']} | {row['passed']} | {row['root_results']} | [JSON](../{row['evidence']}) |" for row in online]
    lines += ['', '# Historia', '', 'Los 29 notebooks históricos se enumeran en el inventario. Sus resultados anteriores se preservan; no se recapturaron ni se presentan como evidencia del wheel 2.1.3 actual. GPU/vLLM, AWS IAM y ADA IAM conservan la prueba en su entorno como pendiente.', '']
    DOC.write_text('\n'.join(lines), encoding='utf-8')
    (OUTPUT / 'runresults-index.json').write_text(json.dumps({'records': records, 'online': online, 'offline_root_results': total_roots}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'units': len(records), 'offline_root_results': total_roots, 'missing_capture': [r['source'] for r in records if r['status'] == 'missing-capture'], 'online_cases': len(online)}))


if __name__ == '__main__':
    main()
