"""Offline CPython cell checks when Jupyter sockets are unavailable; not kernel acceptance."""
import argparse
import ast
import asyncio
import inspect
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def execute(path):
    sys.path[:0] = [str(ROOT), str(ROOT / 'tutorials'),
                   str(ROOT / 'examples/agentic_systems_studio/src'),
                   str(ROOT / 'integrations/ada/src')]
    from _offline import enforce_offline, blocked_attempts
    enforce_offline()
    notebook = json.loads(path.read_text())
    namespace = {'__name__': '__main__'}
    executed = skipped = 0
    for index, cell in enumerate(notebook['cells']):
        if cell['cell_type'] != 'code':
            continue
        if set(cell.get('metadata', {}).get('tags', [])) & {'live', 'local-service'}:
            skipped += 1
            continue
        code = compile(''.join(cell['source']), str(path) + ':' + str(index),
                       'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        value = eval(code, namespace)
        if inspect.isawaitable(value):
            asyncio.run(value)
        executed += 1
    assert blocked_attempts() == 0
    print(json.dumps({'executed': executed, 'skipped': skipped,
                      'mode': 'CPython cells, not Jupyter kernel', 'ok': True}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / '.tmp/notebook-cells.json')
    args = parser.parse_args()
    if args.child:
        execute(args.child)
        return
    paths = sorted((ROOT / 'tutorials').rglob('*.ipynb')) + sorted(
        p for p in (ROOT / 'examples').rglob('*.ipynb') if 'history' not in p.parts)
    rows = []
    for path in paths:
        run = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--child', str(path)],
                             cwd=ROOT, capture_output=True, text=True, timeout=180)
        rows.append({'path': str(path.relative_to(ROOT)), 'ok': run.returncode == 0,
                     'stdout': run.stdout, 'stderr': run.stderr})
        print(rows[-1]['path'], rows[-1]['ok'], flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, indent=2))
    raise SystemExit(0 if all(row['ok'] for row in rows) else 1)


if __name__ == '__main__':
    main()
