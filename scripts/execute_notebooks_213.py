"""Execute every current teaching notebook in fresh offline kernels."""
import hashlib
import json
import os
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
import agentic_systems as toolkit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / os.environ.get('AGENTIC_213_EVIDENCE_DIR', 'revisions/2.1.3/closeout-evidence')
EXCLUDED = {'history', 'dist', 'build', '__pycache__', '.ipynb_checkpoints'}


def main():
    assert toolkit.__version__ == '2.1.3' and 'site-packages' in Path(toolkit.__file__).parts
    paths = sorted(path for folder in ('tutorials', 'examples') for path in (ROOT / folder).rglob('*.ipynb')
                   if not EXCLUDED.intersection(path.relative_to(ROOT).parts))
    selected = os.environ.get('AGENTIC_213_NOTEBOOK_ONLY')
    if selected:
        paths = [p for p in paths if p.relative_to(ROOT).as_posix() == selected]
        assert len(paths) == 1
    destination = OUTPUT / 'executed-notebooks'
    destination.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, path in enumerate(paths):
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        notebook = nbformat.read(path, as_version=4)
        code_cells = sum(cell.cell_type == 'code' for cell in notebook.cells)
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                cell.execution_count, cell.outputs = None, []
        bootstrap = nbformat.v4.new_code_cell(
            'import sys as __harness_sys\nfrom pathlib import Path as __harness_Path\n'
            + '__harness_sys.path.insert(0, ' + repr(str(ROOT / 'tutorials')) + ')\n'
            + '__harness_sys.path.insert(0, ' + repr(str(ROOT / 'scripts')) + ')\n'
            + 'from _offline import enforce_offline as __guard, blocked_attempts as __blocked\n__guard()\n'
            + 'import capture_runresults_213 as __capture\n__capture.install()\n'
            + 'import agentic_systems as __harness_toolkit\nassert __harness_toolkit.__version__ == "2.1.3"\n'
            + 'assert "site-packages" in __harness_Path(__harness_toolkit.__file__).parts')
        bootstrap.metadata = {'tags': ['validation-only', 'hide-input']}
        notebook.cells.insert(0, bootstrap)
        runresults = OUTPUT / 'notebook-runresults' / f'{index:02d}-{path.stem}.json'
        notebook.cells.append(nbformat.v4.new_code_cell('__capture.save(' + repr(str(runresults)) + ', ' + repr(path.relative_to(ROOT).as_posix()) + ')\nassert __blocked() == 0', metadata={'tags': ['validation-only', 'hide-input']}))
        manager = KernelManager(kernel_name='python3')
        manager.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
        client = NotebookClient(notebook, km=manager, timeout=120, resources={'metadata': {'path': str(path.parent)}})
        failure = None
        try:
            client.execute()
        except Exception as exc:
            failure = {'type': type(exc).__name__, 'message': str(exc)[-5000:]}
        finally:
            if client.kc is not None:
                client.kc.stop_channels()
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
        target = destination / f'{index:02d}-{path.name}'
        nbformat.write(notebook, target)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source_hash, 'Source changed during execution'
        row = {'notebook': path.relative_to(ROOT).as_posix(), 'passed': failure is None, 'error': failure,
               'source_sha256': source_hash, 'code_cells': code_cells, 'validation_only_cells': 2,
               'executed_notebook': target.relative_to(ROOT).as_posix(), 'executed_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
               'inference_requests': 0}
        row['runresults_evidence'] = runresults.relative_to(ROOT).as_posix() if runresults.exists() else None
        rows.append(row)
        print(json.dumps({k: v for k, v in row.items() if k not in {'error'}}, ensure_ascii=False), flush=True)
        if failure:
            print(json.dumps(failure, ensure_ascii=False), flush=True)
    report_path = OUTPUT / 'notebooks.json'
    if selected and report_path.exists():
        previous = json.loads(report_path.read_text(encoding='utf-8'))['notebooks']
        replaced = {row['notebook'] for row in rows}
        rows = [row for row in previous if row['notebook'] not in replaced] + rows
        rows.sort(key=lambda row: row['notebook'])
    report_path.write_text(json.dumps({'version': toolkit.__version__, 'package_file': toolkit.__file__,
        'total': len(rows), 'passed': sum(row['passed'] for row in rows), 'notebooks': rows, 'inference_requests': 0}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert all(row['passed'] for row in rows)


if __name__ == '__main__':
    main()
