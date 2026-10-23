"""Execute the real provider notebooks against four frameworks, with a shared cap."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
import agentic_systems as toolkit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / os.environ['AGENTIC_213_EVIDENCE_DIR']
WHEEL_SHA = 'b09785bc75faa97d15b4cf4c1fc25b18741319ce1b8024641c9597930115b283'


def main():
    assert toolkit.__version__ == '2.1.3' and 'site-packages' in Path(toolkit.__file__).parts
    wheel = ROOT / 'revisions/2.1.3/closeout-artifacts/agentic_systems-2.1.3-py3-none-any.whl'
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == WHEEL_SHA
    with zipfile.ZipFile(wheel) as archive:
        assert all((Path(toolkit.__file__).parent / name.removeprefix('agentic_systems/')).read_bytes() == archive.read(name)
                   for name in archive.namelist() if name.startswith('agentic_systems/') and not name.endswith('/'))
    ledger_path = Path(os.environ['AGENTIC_213_BUDGET_FILE']).resolve()
    initial = json.loads(ledger_path.read_text(encoding='utf-8'))
    assert initial['limits'] == {'usd': 10, 'requests': 300}
    assert initial['campaign'] == '213-learning'
    attempt = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    destination = OUTPUT / 'live-notebooks' / attempt
    destination.mkdir(parents=True)
    plan = [(name, framework) for name in ('01_openai', '02_ollama', '03_bedrock')
            for framework in ('native', 'langgraph', 'openai-agents', 'strands')]
    frozen = {'wheel_sha256': WHEEL_SHA, 'cases': [{'notebook': 'tutorials/providers/' + name + '.ipynb',
        'source_sha256': hashlib.sha256((ROOT / 'tutorials/providers' / (name + '.ipynb')).read_bytes()).hexdigest(),
        'framework': framework, 'oracle': 'Required actual certify Tool event, unchanged input value=37, invariants and serializable RunResult'}
        for name, framework in plan], 'routes': initial['routes'], 'limits': initial['limits']}
    (destination / 'frozen-plan.json').write_text(json.dumps(frozen, indent=2) + '\n', encoding='utf-8')
    rows = []
    for name, framework in plan:
        path = ROOT / 'tutorials/providers' / (name + '.ipynb')
        identity = name + '--' + framework
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        notebook = nbformat.read(path, 4)
        capture = destination / (identity + '-runresults.json')
        bootstrap = nbformat.v4.new_code_cell(
            'import sys, os\nfrom pathlib import Path\n'
            + 'sys.path.insert(0, ' + repr(str(ROOT / 'scripts')) + ')\n'
            + 'from agentic_systems_studio.environment import load_studio_environment\n'
            + 'load_studio_environment(' + repr(str(ROOT / '.env')) + ')\n'
            + 'from agentic_systems_studio.budget import ensure_budget\n'
            + '__budget = ensure_budget()\n__budget.phase = ' + repr('notebook-' + identity) + '\n'
            + 'import capture_runresults_213 as __capture\n__capture.install()',
            metadata={'tags': ['validation-only']})
        notebook.cells.insert(0, bootstrap)
        # Parameterize only the framework, after the visible runtime declaration.
        index = next(i for i, c in enumerate(notebook.cells) if c.cell_type == 'code' and 'framework = "native"' in c.source)
        notebook.cells.insert(index + 1, nbformat.v4.new_code_cell('framework = ' + repr(framework), metadata={'tags': ['validation-only', 'parameters']}))
        footer = nbformat.v4.new_code_cell('__capture.save(' + repr(str(capture)) + ', ' + repr(path.relative_to(ROOT).as_posix()) + ')', metadata={'tags': ['validation-only']})
        notebook.cells.append(footer)
        manager = KernelManager(kernel_name='python3')
        manager.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
        client = NotebookClient(notebook, km=manager, timeout=240, resources={'metadata': {'path': str(path.parent)}})
        error = None
        try:
            client.execute()
        except Exception as exc:
            error = {'type': type(exc).__name__, 'message': str(exc)[-6000:]}
        finally:
            # A failed cell must not discard results produced before it.
            if error and client.kc is not None:
                try:
                    client.execute_cell(footer, len(notebook.cells) - 1)
                except Exception:
                    pass
            if client.kc is not None:
                client.kc.stop_channels()
            if manager.has_kernel:
                manager.shutdown_kernel(now=False)
        target = destination / (identity + '.ipynb')
        nbformat.write(notebook, target)
        assert source_hash == hashlib.sha256(path.read_bytes()).hexdigest()
        ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
        row = {'notebook': path.relative_to(ROOT).as_posix(), 'framework': framework, 'passed': error is None,
               'source_sha256': source_hash, 'error': error, 'evidence': target.relative_to(ROOT).as_posix(),
               'runresults': capture.relative_to(ROOT).as_posix() if capture.exists() else None,
               'requests_so_far': len(ledger['attempts'])}
        rows.append(row)
        (destination / (identity + '.json')).write_text(json.dumps(row, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: row[k] for k in ('notebook', 'framework', 'passed', 'requests_so_far')}), flush=True)
    summary = {'version': toolkit.__version__, 'wheel_sha256': WHEEL_SHA, 'planned': len(plan), 'executed': len(rows),
               'passed': sum(row['passed'] for row in rows), 'rows': rows}
    (destination / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    (OUTPUT / 'live-notebooks.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    assert all(row['passed'] for row in rows), 'Live notebook failures are retained and block complete acceptance'


if __name__ == '__main__':
    main()
