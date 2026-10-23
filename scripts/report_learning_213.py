"""Report the current learning campaign without replacing the published snapshot."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import agentic_systems as toolkit
from report_runresults_213 import describe, find_results

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / os.environ['AGENTIC_213_EVIDENCE_DIR']


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def link(path):
    return '../' + path.relative_to(ROOT).as_posix()


def main():
    assert toolkit.__version__ == '2.1.3' and 'site-packages' in Path(toolkit.__file__).parts
    books = read(OUTPUT / 'notebooks.json')
    live = read(OUTPUT / 'live-notebooks.json') if (OUTPUT / 'live-notebooks.json').exists() else {'rows': []}
    local = read(OUTPUT / 'local-lessons.json') if (OUTPUT / 'local-lessons.json').exists() else {'rows': []}
    ledger = read(ROOT / '.tmp/campaign213-learning/live-budget.json')
    reserved = sum((Decimal(x['reserved_usd']) for x in ledger['attempts']), Decimal(0))
    assert len(ledger['attempts']) <= 300 and reserved <= 10
    assert hashlib.sha256((ROOT / '.tmp/campaign213-final/live-budget.json').read_bytes()).hexdigest() == ledger['previous_campaign_sha256']
    canonical = read(OUTPUT / 'examples.json')['reports']
    adapted = read(OUTPUT / 'adaptations.json')['reports']
    phases = {name: read(OUTPUT / (name + '.json')) for name in ('features', 'integrated', 'studio', 'studio-ui') if (OUTPUT / (name + '.json')).exists()}
    lines = ['# Validación de tutorials y examples · 2.1.3', '',
        'Campaña independiente, posterior al release. Se usa el wheel **publicado 2.1.3** instalado sin modo editable. '
        'La documentación y las fuentes didácticas pueden mejorar; no se reemplazan los artefactos publicados ni la evidencia original.', '',
        '**Wheel SHA-256:** `b09785bc75faa97d15b4cf4c1fc25b18741319ce1b8024641c9597930115b283`.', '',
        f"Examples: **{sum(r['passed'] for r in canonical) + sum(r['passed'] for r in adapted)}/{len(canonical) + len(adapted)}** programas offline. "
        f"Notebooks: **{books['passed']}/{books['total']}** con sus secciones offline verificadas. Las celdas omitidas se indican por notebook. "
        f"Rutas live de notebooks: **{sum(r['passed'] for r in live['rows'])}/{len(live['rows'])}**.", '',
        f"Presupuesto autorizado: USD 10 y 300 llamadas. Registradas **{len(ledger['attempts'])} llamadas** y **USD {reserved} reservados**. "
        'Las reservas son cotas conservadoras, no facturación. Se incluyen fallos, reintentos y Ollama; no se descuenta ningún intento.', '',
        '[RunResult y Lineage Memory por unidad](RUNRESULTS_LINEAGE_213.md) · [Inventario de gramática](NOTEBOOK_INVENTORY_213.md) · '
        '[Evidencia original publicada](../revisions/2.1.3/closeout-evidence/REPORT.md)', '',
        '## Modelos y endpoints', '', '| Provider | Modelo | Endpoint |', '|---|---|---|']
    for provider, route in ledger['routes'].items():
        lines.append(f"| {provider} | `{route['model']}` | `{route['endpoint']}` |")
    lines += ['', 'Python Runtime es el control determinista. Bedrock usa bearer/API key; no se infiere validación IAM de este resultado.', '',
              '## Notebooks vigentes', '', '| Notebook | Offline | Live / servicio local / interfaz | Evidencia |', '|---|---|---|---|']
    for row in books['notebooks']:
        path = ROOT / row['notebook']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['source_sha256'], row['notebook']
        external = [r for r in live['rows'] if r['notebook'] == row['notebook'] and r['source_sha256'] == row['source_sha256']]
        services = [r for r in local['rows'] if r['notebook'] == row['notebook'] and r['source_sha256'] == row['source_sha256']]
        note = '; '.join([f"{sum(r['passed'] for r in external)}/{len(external)} frameworks live" if external else '',
                          'Servicios/UI: ' + ('pasa' if all(r['passed'] for r in services) else 'falla') if services else '']).strip('; ')
        if not note:
            note = 'No requiere inferencia; configuración GPU pendiente' if 'vllm' in row['notebook'] else 'Sin inferencia; alcance del notebook'
        offline = 'Pasa' if row['passed'] else 'Falla'
        if row.get('skipped_sections'):
            offline += f"; {len(row['skipped_sections'])} celdas de otro perfil omitidas"
        lines.append(f"| [{row['notebook']}]({link(path)}) | {offline} | {note} | [Copia ejecutada]({link(ROOT / row['executed_notebook'])}) |")
    lines += ['', '## Proveedores × frameworks: ejecución de las celdas originales', '', '| Provider notebook | native | LangGraph | OpenAI Agents | Strands |', '|---|---|---|---|---|']
    for name in ('01_openai', '02_ollama', '03_bedrock'):
        cells = []
        for framework in ('native', 'langgraph', 'openai-agents', 'strands'):
            rows = [r for r in live['rows'] if r['notebook'].endswith(name + '.ipynb') and r['framework'] == framework]
            cells.append(('Pasa' if rows[0]['passed'] else 'Falla') if rows else 'Pendiente')
        lines.append('| ' + name + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', 'Input: pedir `certify(37)`. Proceso: el modelo debe invocar la Tool con el entero exacto; se exigen eventos reales, invariantes y RunResult serializable. '
        'Output: evidencia de certify y lineage. El arnés solo parametriza el framework en una copia de validación; no sustituye modelo, proveedor, actor ni respuesta.', '',
        '## Aplicaciones y capacidades específicas', '', '| Grupo | Pasan / planificados | Input → proceso → output |', '|---|---:|---|']
    explanations = {'features': 'Transferencia a especialista y petición bloqueada → handoff/guardrail/sesión; MCP/A2A locales → evidencia remota; checkpoint → pausa/reanudación; cuatro actores → recorrido exacto.',
        'integrated': 'Pedidos de 200 y 1500 → cotización, decisión y Tool approve/review, Environment y Eval sobre la ejecución observada → approved/manual_review y memoria approved=1.',
        'studio': 'Proyecto LINTERNA y cálculo 17×19 → tres turnos con historial y calculadora → nombre conservado y 323.',
        'studio-ui': 'Seleccionar provider/framework y enviar 17×19 en widgets reales → chat y Tool safe_calculate → 323 y RunResult correcto.'}
    for name, report in phases.items():
        lines.append(f"| [{name}]({link(OUTPUT / (name + '.json'))}) | {report['passed']}/{report['planned']} | {explanations[name]} |")
    lines += ['', 'Los grupos incluyen controles Python sin inferencia. Son escenarios definidos, no una garantía sobre cualquier conversación o modelo. '
        'El juez fixture valida el protocolo y los oráculos exactos comprueban aritmética, herramientas y memoria; esta campaña no declara un benchmark semántico general.', '',
        '## Cada example ejecutable', '', '| Fuente | Resultado | Input → proceso → output y RunResult/lineage |', '|---|---|---|']
    sections, indexed = [], []
    excluded = {'history', 'dist', 'build', '__pycache__'}
    for source in sorted((ROOT / 'examples').rglob('example.py')):
        if excluded.intersection(source.relative_to(ROOT).parts):
            continue
        relative = source.parent.relative_to(ROOT / 'examples')
        directory = OUTPUT / 'example-results' / relative
        record = directory / ('current.json' if len(relative.parts) > 1 else 'run.json')
        evidence = directory / 'runresults.json'
        assert record.is_file() and evidence.is_file(), source
        value = read(record)
        assert hashlib.sha256(source.read_bytes()).hexdigest() == value['source_sha256']
        result = read(evidence)
        assert result['source'] == source.parent.relative_to(ROOT).as_posix()
        lines.append(f"| [{source.parent.relative_to(ROOT).as_posix()}]({link(source)}) | Pasa offline | [Informe completo]({link(record)}) · [RunResult/lineage]({link(evidence)}) |")
        sections += describe(source.parent.relative_to(ROOT).as_posix(), source, evidence, result)
        indexed.append({'source': source.relative_to(ROOT).as_posix(), 'evidence': evidence.relative_to(ROOT).as_posix(), 'roots': result['root_results']})
    for row in books['notebooks']:
        if row.get('runresults_evidence'):
            evidence = ROOT / row['runresults_evidence']
            sections += describe(row['notebook'] + ' · perfil offline', ROOT / row['notebook'], evidence, read(evidence))
    for row in live['rows']:
        if row.get('runresults'):
            evidence = ROOT / row['runresults']
            sections += describe(row['notebook'] + ' · live · ' + row['framework'], ROOT / row['notebook'], evidence, read(evidence))
    for row in local['rows']:
        evidence = ROOT / row['runresults_evidence']
        sections += describe(row['notebook'] + ' · servicios locales/UI', ROOT / row['notebook'], evidence, read(evidence))
    derived = OUTPUT / 'derived-lineage'
    derived.mkdir(exist_ok=True)
    for phase, report in phases.items():
        for case in report['rows']:
            source = ROOT / report['attempt_directory'] / (case['name'] + '.json')
            raw = read(source)
            values = list(find_results(raw.get('report', {})))
            roots = []
            for value in values:
                result = toolkit.RunResult(**value)
                try:
                    memory, error = result.lineage(name=phase + '/' + case['name']).to_dict(), None
                except Exception as exc:
                    memory, error = None, {'type': type(exc).__name__, 'message': str(exc)}
                roots.append({'run_result': value, 'lineage_memory': memory, 'lineage_error': error,
                              'invariants': result.check_invariants().to_dict()})
            evidence = derived / (phase + '--' + case['name'] + '.json')
            payload = {'source': source.relative_to(ROOT).as_posix(), 'root_results': len(roots), 'results': roots,
                       'scope': 'Lineage derived offline from the unchanged observed live RunResult; no candidate or judge re-execution'}
            evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            sections += describe(phase + ' · ' + case['name'], source, evidence, payload)
    lines += ['', 'Los 34 experimentos anteriores se ejecutaron como adaptaciones actuales. Los casos con entradas suministradas, respuestas guardadas o jueces fixture '
        'conservan ese alcance; ejecutar su código no transforma esa evidencia en generación live. Los fallos controlados forman parte de los contratos esperados.', '',
        '## Checks adicionales', '', '| Suite | Tests | Fallos / errores |', '|---|---:|---:|']
    for name in ('tests.xml', 'studio-tests.xml', 'integrity-tests.xml', 'business-tests.xml', 'learning-tests.xml'):
        path = OUTPUT / name
        if path.exists():
            tree = ET.parse(path).getroot()
            suites = [tree] if tree.tag == 'testsuite' else list(tree.iter('testsuite'))
            tests = sum(int(s.get('tests', 0)) for s in suites)
            failures = sum(int(s.get('failures', 0)) + int(s.get('errors', 0)) for s in suites)
            lines.append(f"| [{name}]({link(path)}) | {tests} | {failures} |")
    lines += ['', '## Incidencias y correcciones didácticas', '',
        '- La primera ejecución restringida no pudo completar kernels/subprocesos y protocolos locales. Se repitió con acceso al transporte local; no hubo inferencia en ese intento.',
        '- Se corrigió el orden de una celda de Skills al retirar un import auxiliar. Se conserva la copia fallida.',
        '- Las variables existentes usan también *_MODEL: los notebooks aceptan *_MODEL_ID o *_MODEL para el mismo modelo explícito. Los intentos previos fallaron antes del transporte y consumieron cero llamadas.',
        '- El recorrido con cuatro SDKs declara 180 s para incluir su preparación en un kernel frío; se conserva el intento que agotó el plazo de 10 s.',
        '- La captura distingue el ejemplo canónico y la adaptación con el mismo nombre en directorios separados. No se atribuye la evidencia de uno al otro.', '',
        '- La comprobación estática de nombres detectó una referencia de runtime que no pertenecía al challenge offline. Se retiró esa opción incompleta y se reejecutó la lección; no cambió el SDK.',
        '- Un intento del arnés local encontró un directorio temporal bloqueado por Windows después de completar MCP/A2A. El arnés conserva ahora sus directorios de trabajo; se verificaron apertura y cierre de Studio. Los errores de fixtures restringidos también se conservaron antes de repetirlos en un directorio permitido.', '',
        '## Límites y procedencia', '',
        '- vLLM/Colab GPU, AWS IAM y ADA IAM: ejecución en su entorno pendiente. Sus ejemplos solo validan configuración y contratos offline.',
        '- No se modificó el código del SDK o Studio publicado. No se creó otra versión, tag ni publicación.',
        '- La copia original de la documentación y notebooks aprobados se conserva en published-learning-source.zip y se verifica contra el manifiesto original. La aceptación de este material usa hashes actuales separados.',
        '- Los intentos y las copias ejecutadas permanecen en los directorios de evidencia; no se borra un fallo para mostrar solo el intento posterior.', '',
        f"Generado: {datetime.now(timezone.utc).isoformat()}.", '']
    (ROOT / 'docs/LEARNING_VALIDATION_213.md').write_text('\n'.join(lines), encoding='utf-8')
    prefix = ['# RunResult y Lineage Memory · material actual 2.1.3', '',
        'Ejecuciones observadas contra el wheel publicado. Cada sección enlaza resultados completos, linaje e invariantes. '
        'Las salidas con ok=False pueden ser fallos controlados exigidos por el ejemplo. No se inventa un resultado para una configuración sin ejecución.', '',
        '[Alcance, modelos, presupuesto y pruebas live](LEARNING_VALIDATION_213.md). '
        'El informe anterior aprobado sigue dentro del archivo published-learning-source.zip; no se mezcla su aceptación con estas fuentes.', '']
    (ROOT / 'docs/RUNRESULTS_LINEAGE_213.md').write_text('\n'.join(prefix + sections), encoding='utf-8')
    (OUTPUT / 'learning-index.json').write_text(json.dumps({'version': '2.1.3', 'examples': indexed,
        'notebooks': books['total'], 'budget': {'attempts': len(ledger['attempts']), 'reserved_usd': str(reserved)}}, indent=2) + '\n', encoding='utf-8')
    sources = [ROOT / row['notebook'] for row in books['notebooks']] + [ROOT / row['source'] for row in indexed]
    manifest = {'schema_version': 'agentic_systems.learning-validation-213.v1', 'version': '2.1.3',
        'sdk_wheel_sha256': 'b09785bc75faa97d15b4cf4c1fc25b18741319ce1b8024641c9597930115b283',
        'identity_note': 'Current learning sources are identified by content hashes; the original published tag remains unchanged.',
        'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)},
        'budget_sha256': hashlib.sha256((OUTPUT / 'budget.json').read_bytes()).hexdigest(),
        'evidence_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUTPUT.rglob('*'))
                            if p.is_file() and p.name != 'learning-manifest.json'}}
    (OUTPUT / 'learning-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'examples': len(indexed), 'notebooks': books['total'], 'attempts': len(ledger['attempts']), 'reserved_usd': str(reserved)}))


if __name__ == '__main__':
    main()
