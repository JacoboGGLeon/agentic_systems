"""Seal local 2.1.3 evidence; never tags, pushes or publishes anything."""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'revisions/2.1.3/closeout-evidence'
ARTIFACTS = ROOT / 'revisions/2.1.3/closeout-artifacts'
BUILD = ROOT / '.tmp/closeout213-ready'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_once(source, destination):
    if destination.exists():
        assert digest(source) == digest(destination), 'Never replace sealed bytes'
    else:
        shutil.copyfile(source, destination)


def main():
    wheel = next((BUILD / 'dist').glob('*.whl'))
    sdist = next((BUILD / 'dist').glob('*.tar.gz'))
    studio = ARTIFACTS / 'agentic_systems_studio-2.1.3-py3-none-any.whl'
    assert digest(ROOT / 'README.md') == digest(BUILD / 'source/README.md'), 'Frozen SDK README changed'
    with zipfile.ZipFile(wheel) as archive:
        package = {name: archive.read(name) for name in archive.namelist() if name.startswith('agentic_systems/') and not name.endswith('/')}
    assert all((ROOT / 'src' / name).read_bytes() == data for name, data in package.items())
    with tarfile.open(sdist) as archive:
        entries = {member.name.split('/src/', 1)[1]: archive.extractfile(member).read()
                   for member in archive.getmembers() if member.isfile() and '/src/agentic_systems/' in member.name}
    assert all(entries[name] == data for name, data in package.items()), 'sdist package differs from wheel'
    for source in (wheel, sdist):
        copy_once(source, ARTIFACTS / source.name)
    guide = ROOT / 'examples/api_walkthrough/01_api_user_guide.ipynb'
    copy_once(guide, ARTIFACTS / guide.name)
    phases = {name: read(OUTPUT / (name + '.json')) for name in ('matrix', 'features', 'integrated', 'studio', 'studio-ui')}
    assert all(row['all_passed'] and row['wheel_sha256'] == digest(wheel) for row in phases.values())
    assert [row['passed'] for row in phases.values()] == [16, 15, 16, 16, 12]
    books = read(OUTPUT / 'notebooks.json')
    assert books['total'] == books['passed'] == 13
    assert all(row['source_sha256'] == digest(ROOT / row['notebook']) for row in books['notebooks'])
    examples = read(OUTPUT / 'examples.json')
    assert len(examples['reports']) == 15 and all(row['passed'] for row in examples['reports'])
    assert all(row['source_sha256'] == digest(ROOT / 'examples' / row['example'] / 'example.py') for row in examples['reports'])
    adaptations = read(OUTPUT / 'adaptations.json')
    assert adaptations['total'] == adaptations['passed'] == 34
    traces = read(OUTPUT / 'runresults-index.json')
    assert len(traces['records']) == 62 and all(row['status'] == 'captured' for row in traces['records'])
    notebook_inventory = read(ROOT / 'docs/notebook_inventory_213.json')
    assert notebook_inventory['current'] == 13 and notebook_inventory['historical'] == 29
    assert all(data['direct'] for data in notebook_inventory['coverage'].values())
    ledger_path = ROOT / '.tmp/campaign213-final/live-budget.json'
    ledger = read(ledger_path)
    assert digest(ROOT / '.tmp/campaign213/live-budget.json') == ledger['previous_campaign_sha256'], 'Previous allocation was modified'
    reserved = sum((Decimal(row['reserved_usd']) for row in ledger['attempts']), Decimal(0))
    assert len(ledger['attempts']) <= 300 and reserved <= 10
    ledger['snapshot_at'] = datetime.now(timezone.utc).isoformat()
    (OUTPUT / 'budget.json').write_text(json.dumps(ledger, indent=2) + '\n', encoding='utf-8')
    failures = []
    for phase in phases:
        for path in sorted((OUTPUT / phase).rglob('*.json')):
            row = read(path)
            if row.get('passed') is False:
                failures.append({'phase': phase, 'case': row['name'], 'error': row.get('error'), 'evidence': path.relative_to(ROOT).as_posix()})
    (OUTPUT / 'failure-index.json').write_text(json.dumps(failures, indent=2) + '\n', encoding='utf-8')
    offline_issue = {'example': 'provider_framework_conformance', 'source': 'Observed terminal result from the initial concurrent offline run',
                     'code': 'scheduler_timeout', 'message': 'Execution exceeded timeout_s=10.', 'framework': 'openai-agents',
                     'execution_id': 'run-74dfe85ea67a4b01bc4b3e71c1f77569', 'inference_requests': 0,
                     'resolution': 'Explicit runtime and execution timeout of 60 seconds for cold SDK imports; final run passed. SDK defaults unchanged.'}
    (OUTPUT / 'offline-issue.json').write_text(json.dumps(offline_issue, indent=2) + '\n', encoding='utf-8')
    bundle = ARTIFACTS / 'agentic-systems-studio-2.1.3-final-local.zip'
    if not bundle.exists():
        application = ROOT / 'examples/agentic_systems_studio'
        with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name in ('README.md', 'app.py', 'pyproject.toml', '.env.example', 'test_offline.py'):
                archive.write(application / name, 'studio/' + name)
            for folder in ('src', 'tests', 'notebooks'):
                for path in sorted((application / folder).rglob('*')):
                    if path.is_file() and '__pycache__' not in path.parts and not any(part.endswith('.egg-info') for part in path.parts) and path.suffix in {'.py', '.ipynb'}:
                        archive.write(path, 'studio/' + path.relative_to(application).as_posix())
            archive.write(wheel, 'wheels/' + wheel.name)
            archive.write(studio, 'wheels/' + studio.name)
            archive.write(guide, guide.name)
            archive.writestr('README.txt', 'Local validation bundle, not published. Install SDK and Studio wheels plus required optional dependencies.\n'
                'Dependencies are not vendored; an offline installation needs a prepared wheelhouse.\n'
                'No credentials are included. Python is deterministic; external inference requires explicit budget authorization.\n')
    coverage = read(OUTPUT / 'coverage.json')['totals']
    packaging = read(OUTPUT / 'packaging.json')
    installation = read(OUTPUT / 'studio-install.json')
    assert packaging['wheel_sha256'] == digest(wheel) and installation['studio_wheel_sha256'] == digest(studio)
    notebook_rows = []
    for row in notebook_inventory['notebooks']:
        if row['current']:
            grammar = ', '.join(row['analysis']['elements']) or 'API compartida: ' + ', '.join(row['observed_execution_elements'])
            notebook_rows.append(f"| [{row['notebook']}](../../../{row['notebook']}) | {grammar} | Offline: pasa |")
    phase_rows = [f"| {name} | {row['passed']}/{row['planned']} | [JSON]({name}.json) |" for name, row in phases.items()]
    phase_calls = Counter(row['phase'] for row in ledger['attempts'])
    report = f'''# Cierre local de Agentic Systems 2.1.3

La gramática única, el material de aprendizaje y la campaña final están
validados en el alcance descrito. **No se publicó, abrió PR, creó tag ni ejecutó
CI remoto**. La aceptación de release todavía requiere su revisión y CI.

## Qué puede mostrar el README

- **13 notebooks vigentes ejecutados offline**, con un import: `import agentic_systems as toolkit`.
- **49 programas de examples ejecutados**: 34 adaptaciones y 15 programas focalizados/integrados. Algunas adaptaciones solo preparan configuración o usan candidatos/jueces guardados, y así se identifican.
- **313 RunResult raíz offline observados**, con memoria de linaje y JSON completo por fuente. Son límites de ejecución, no aplicaciones independientes ni llamadas facturables.
- **75 escenarios finales online pasan**, incluidos controles Python, capacidades nativas y Studio; versiones, modelos y bytes están fijados en esta evidencia.

El [README de examples](../../../examples/README.md) demuestra `.lineage(...)`
y enlaza el [informe de RunResult y Lineage Memory](../../../docs/RUNRESULTS_LINEAGE_213.md).
El README principal enlaza este cierre. No se traslada certificación histórica
a la revisión actual ni se anuncia éxito universal de cualquier prompt.

## Todos los notebooks

Hay **42 archivos: 13 vigentes y 29 históricos/generados anteriores**. Los
históricos no se reejecutaron. El [inventario exhaustivo](../../../docs/NOTEBOOK_INVENTORY_213.md)
incluye los 42, gramática directa, elementos observados en RunResult, módulos
compartidos, configuración declarada, hashes y evidencia. El
[CSV de llamadas y parámetros](../../../docs/notebook_parameters_213.csv) y el
[JSON](../../../docs/notebook_inventory_213.json) permiten revisar el detalle.

| Notebook vigente | Gramática directa o compartida observada | Estado |
|---|---|---|
{chr(10).join(notebook_rows)}

El [nuevo notebook autónomo](../../../examples/api_walkthrough/01_api_user_guide.ipynb)
reúne la explicación completa: Tool/Skill/Action, seis flujos, run/compile/async,
límites, aprobación de pedidos, memoria, Eval, resultados, tipos, carga portable,
proveedores/frameworks y serving configurado. Sus 17 celdas de código no realizan
inferencia. La instrumentación y las guardas solo se añaden a las copias ejecutadas.

## Validación online del artefacto final

| Fase | Resultado | Evidencia |
|---|---:|---|
{chr(10).join(phase_rows)}

- Proveedores: Python determinista, Ollama `gemma4:31b-cloud`, Bedrock API key `qwen.qwen3-32b-v1:0` en us-east-2 y OpenAI `gpt-4.1-mini`.
- Frameworks: native, LangGraph, OpenAI Agents y Strands. [Identidades sin claves](routes.json).
- Matriz base: Tool certify con 37, serialización e invariantes; 16 combinaciones.
- Integrado: dos pedidos → quote determinista → actor del runtime seleccionado para approve/review → outputs exactos y memoria approved=1. Eval examina la ejecución guardada sin comprar otra ejecución; conserva los resultados y el linaje originales. Pasada final completa: 16/16.
- LangGraph: interrupt, InMemorySaver y Command resume reales, como extensión de aplicación dentro de Action.
- OpenAI Agents: handoff, callback, evento normalizado, SQLiteSession y control negativo de guardrail en cuatro proveedores.
- Strands: MCP Streamable HTTP y A2A JSON-RPC con servicios locales reales y agente remoto determinista; los clientes con proveedor externo sí usan inferencia.
- Interoperabilidad: cuatro actores en un System, con Python y con mezcla Python/OpenAI/Ollama/Bedrock; salida 46 e identidades conservadas.
- Studio backend: 16 combinaciones × tres turnos; recordar LINTERNA y calcular 17×19=323. Widgets AppTest: 12 combinaciones externas. No se afirma que los diez catálogos de razonamiento estén certificados live.

La [evidencia online con memoria de linaje](../../../docs/RUNRESULTS_LINEAGE_213.md#providers-y-frameworks-resultados-online-y-memoria)
separa cada caso y proveedor. Los notebooks continúan siendo offline.

## Fallos encontrados y corregidos

1. El example de conformidad fijaba 10 segundos, incluyendo carga inicial de SDKs bajo carga. El scheduler produjo un fallo explícito; el example declara ahora 60 segundos y conserva resultados en las aserciones. No se cambiaron defaults del SDK. [Registro reducido del fallo observado](offline-issue.json).
2. El límite del integrado aceptaba datos directos y el sobre simple `data`, pero rechazaba el ToolEnvelope completo de Bedrock native/LangGraph. La Tool había devuelto el total y estado correctos. Se reconocen sus campos estructurales y nombre de Tool, se extrae únicamente su data observada y se conserva el sobre original en los eventos.
3. Ese mismo límite lanzaba una excepción al rechazar evidencia y perdía el actor como hijo. Ahora devuelve el RunResult original con un error añadido, conservando datos, uso y eventos. Dos regresiones offline comprueban formatos de sobre y retención de fallos.

Los tres intentos online fallidos anteriores permanecen en el
[índice](failure-index.json) y sus directorios de intentos. El
[resultado diagnóstico](diagnostic-bedrock-result.json) conserva el ToolEnvelope
correcto y el rechazo del límite. La corrección está en la aplicación compartida
por notebook y campaña; no se cambió modelo, proveedor, framework ni wheel para aprobar.

## Resultados, tests y distribución

- SDK: **180 tests**, cobertura por sentencias de la API canónica nueva **{coverage['percent_covered']:.2f}%** ({coverage['num_statements']} sentencias). El motor privado histórico no forma parte de ese porcentaje. [JUnit](tests.xml), [cobertura](coverage.json).
- Studio: **14 tests offline**; límite de evidencia de negocio: **2 regresiones**. [Studio](studio-offline-tests.xml), [regresiones](business-boundary-tests.xml).
- **13/13 notebooks**, **15/15 programas focalizados**, **34/34 adaptaciones** y proyecto generado con **14 contratos**. [Notebooks](notebooks.json), [examples](examples.json), [adaptaciones](adaptations.json), [proyecto](packaging.json).
- Wheel y fuente SDK: **116 archivos idénticos**; los mismos archivos están en el sdist. README embebido congelado y fuente coinciden. Import base mantiene SDKs opcionales lazy.
- Studio instalado: **21 archivos idénticos** al wheel, notebook y health local verificados. [Instalación](studio-install.json).
- Ruff, tres fronteras de arquitectura, escaneo de secretos y revisión de enlaces se ejecutan localmente. El workflow incorpora los 13 notebooks y los nuevos contratos.

## Presupuesto final

Asignación separada autorizada: **USD 10 / 300 llamadas**. Consumo reservado:
**{len(ledger['attempts'])} llamadas / USD {reserved:.6f}**. Restan **{300-len(ledger['attempts'])}
llamadas / USD {Decimal(10)-reserved:.6f}** en el snapshot. Las reservas incluyen
fallos y diagnóstico, y no son facturación observada. Todos los trabajadores
de inferencia terminaron antes del cierre; los hooks siguieron activos durante
su vida. La asignación anterior permanece intacta, con 198 llamadas.

Se reservan bytes UTF-8 + 4096 como cota de input, salida máxima declarada y
25% de margen, a USD 5/M input y USD 20/M output. Los protocolos locales
registrados no se cuentan como inferencia. [Ledger](budget.json).
Intentos por fase: `{dict(phase_calls)}`.

## Artefactos locales y pendientes

- [Wheel SDK](../closeout-artifacts/{wheel.name}): `{digest(wheel)}`.
- [sdist SDK](../closeout-artifacts/{sdist.name}): `{digest(sdist)}`.
- [Wheel Studio](../closeout-artifacts/{studio.name}): `{digest(studio)}`.
- [Notebook descargable](../closeout-artifacts/{guide.name}) · [Studio ZIP limpio](../closeout-artifacts/{bundle.name}).
- [Manifiesto y hashes](manifest.json) · [Proyecto generado limpio](generated-project.zip).

No se incluyeron credenciales ni wheelhouse de dependencias en el ZIP.
Validación local en Python 3.14.2; runners CI y Python 3.10–3.13 siguen pendientes
de ejecución remota. vLLM/Colab GPU, AWS IAM y ADA IAM requieren sus entornos.
No se añadió [ada], ADA Studio ni wallet. El cierre local no equivale a publicación,
certificación empresarial ni garantía de cualquier versión futura de dependencias.
'''
    (OUTPUT / 'REPORT.md').write_text(report, encoding='utf-8')
    paths = set()
    for folder in ('src/agentic_systems', 'tests/v213', 'tutorials', 'examples', 'docs', 'scripts'):
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and path.suffix in {'.py', '.md', '.json', '.csv', '.ipynb', '.toml'} and not any(part in {'history', 'previous', '__pycache__', 'build', 'dist'} or part.endswith('.egg-info') for part in path.parts):
                paths.add(path)
    paths.update(path for path in OUTPUT.rglob('*') if path.is_file() and path.name != 'manifest.json')
    paths.update(path for path in ARTIFACTS.iterdir() if path.is_file())
    paths.update(ROOT / name for name in ('README.md', 'CHANGELOG.md', 'ROADMAP.md', '.github/workflows/quality.yml'))
    manifest = {'version': '2.1.3', 'status': 'local-acceptance-passed-not-published-ci-pending',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'working_tree': 'Uncommitted work preserved; no remote mutation',
        'sdk_wheel_sha256': digest(wheel), 'sdk_sdist_sha256': digest(sdist), 'studio_wheel_sha256': digest(studio),
        'phases': {name: {'passed': row['passed'], 'planned': row['planned'], 'all_passed': row['all_passed']} for name, row in phases.items()},
        'budget': {'attempts': len(ledger['attempts']), 'reserved_usd': str(reserved), 'limits': ledger['limits']},
        'sha256': {path.relative_to(ROOT).as_posix(): digest(path) for path in sorted(paths)}}
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': manifest['status'], 'hashed_files': len(paths), 'online_cases': sum(row['passed'] for row in phases.values()),
                      'budget': manifest['budget'], 'historical_online_failures': len(failures)}))


if __name__ == '__main__':
    main()
