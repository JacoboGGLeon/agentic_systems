"""Execute current adaptations; application learners only import run()."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'examples/agentic_systems_studio/src'))
sys.path.insert(0, str(ROOT / 'tutorials'))
sys.path.insert(0, str(ROOT / 'scripts'))


def execute(identifier):
    catalog = json.loads((ROOT / 'examples/catalog.json').read_text(encoding='utf-8'))
    entry = next(item for item in catalog['entries'] if item['id'] == identifier)
    if identifier != 'strands_protocol_graph':
        from _offline import enforce_offline
        enforce_offline()
    import capture_runresults_213 as capture
    capture.install()
    result = importlib.import_module('examples.' + entry['group'] + '.' + identifier + '.example').run()
    payload = result.to_dict() if hasattr(result, 'to_dict') else result
    json.dumps(payload, allow_nan=False)
    source = ROOT / 'examples' / entry['group'] / identifier / 'example.py'
    directory = source.parent / 'evidence'
    directory.mkdir(exist_ok=True)
    capture.save(directory / 'runresults.json', 'examples/' + entry['group'] + '/' + identifier)
    previous = directory / 'current.json'
    if previous.exists():
        archive = directory / 'previous'
        archive.mkdir(exist_ok=True)
        target = archive / (hashlib.sha256(previous.read_bytes()).hexdigest() + '.json')
        if not target.exists():
            target.write_bytes(previous.read_bytes())
    (directory / 'current.json').write_text(json.dumps({'example': identifier, 'example_passed': True,
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'inference_requests': 0,
        'scope': 'offline contract or configuration; no model-generation/semantic/IAM/GPU certification',
        'output': payload}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case')
    args = parser.parse_args()
    if args.case:
        execute(args.case)
        return
    catalog = json.loads((ROOT / 'examples/catalog.json').read_text(encoding='utf-8'))
    entries = [entry for entry in catalog['entries'] if 'historical_validation' in entry]
    assert len(entries) == 34
    reports = []
    for entry in entries:
        process = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--case', entry['id']],
            cwd=ROOT, text=True, capture_output=True, encoding='utf-8', errors='replace', timeout=180,
            env={**os.environ, 'OPENAI_AGENTS_DISABLE_TRACING': '1', 'OTEL_SDK_DISABLED': 'true'})
        passed = process.returncode == 0
        reports.append({'example': entry['id'], 'passed': passed, 'error': process.stderr[-3000:] if not passed else None})
        print(json.dumps({'example': entry['id'], 'passed': passed}), flush=True)
    output = ROOT / os.environ.get('AGENTIC_213_EVIDENCE_DIR', 'revisions/2.1.3/framework-evidence')
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'adaptations.json'
    target.write_text(json.dumps({'version': '2.1.3', 'total': len(reports), 'passed': sum(r['passed'] for r in reports),
        'inference_requests': 0, 'reports': reports}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(0 if all(row['passed'] for row in reports) else 1)


if __name__ == '__main__':
    main()
