"""Verify installed Studio bytes, notebook and local server; no inference."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import sys
import zipfile

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
import agentic_systems_studio
from agentic_systems_studio.server import start_studio_server

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / os.environ.get('AGENTIC_213_EVIDENCE_DIR', 'revisions/2.1.3/closeout-evidence')
wheel = ROOT / 'revisions/2.1.3/closeout-artifacts/agentic_systems_studio-2.1.3-py3-none-any.whl'
installed = Path(agentic_systems_studio.__file__).parent
assert 'site-packages' in installed.parts, installed
with zipfile.ZipFile(wheel) as archive:
    expected = {name.removeprefix('agentic_systems_studio/'): archive.read(name)
                for name in archive.namelist() if name.startswith('agentic_systems_studio/') and not name.endswith('/')}
assert all((installed / name).read_bytes() == data for name, data in expected.items())
for path in installed.rglob('*.py'):
    if path.name not in {'__init__.py', 'protocol_server.py'}:
        importlib.import_module('agentic_systems_studio.' + '.'.join(path.relative_to(installed).with_suffix('').parts))

source = ROOT / 'examples/agentic_systems_studio/notebooks/01_studio.ipynb'
notebook = nbformat.read(source, as_version=4)
bootstrap = nbformat.v4.new_code_cell(
    'import sys as __harness_sys\n'
    + '__harness_sys.path.insert(0, ' + repr(str(ROOT / 'tutorials')) + ')\n'
    + 'from _offline import enforce_offline as __guard, blocked_attempts as __attempts\n__guard()')
bootstrap.metadata = {'tags': ['validation-only', 'hide-input']}
notebook.cells.insert(0, bootstrap)
notebook.cells.append(nbformat.v4.new_code_cell('assert __attempts() == 0\nassert answer.ok'))
manager = KernelManager(kernel_name='python3')
manager.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
client = NotebookClient(notebook, km=manager, timeout=90, resources={'metadata': {'path': str(ROOT)}})
try:
    client.execute()
    nbformat.write(notebook, OUTPUT / 'studio-notebook.ipynb')
finally:
    if client.kc is not None:
        client.kc.stop_channels()
    if manager.has_kernel:
        manager.shutdown_kernel(now=True)

os.environ['AGENTIC_SYSTEMS_ENV_FILE'] = str(ROOT / '.env')
os.environ.setdefault('AGENTIC_213_BUDGET_FILE', str(ROOT / '.tmp/campaign213-final/live-budget.json'))
with socket.socket() as candidate:
    candidate.bind(('127.0.0.1', 0))
    port = candidate.getsockname()[1]
server = start_studio_server(port=port, log_dir=ROOT / '.tmp/studio213-installed', stop_previous=False)
payload = {'version': '2.1.3', 'studio_wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
           'installed_files_equal_wheel': len(expected), 'package_file': str(agentic_systems_studio.__file__),
           'notebook_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'notebook_code_cells': 2, 'notebook_passed': True, 'server_health_passed': True,
           'local_url': server.local_url, 'pid': server.process.pid, 'inference_requests': 0}
(OUTPUT / 'studio-install.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
print(json.dumps(payload), flush=True)
