"""Run full local-service/UI lessons with zero authorized model calls."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.request import urlopen
import nbformat
import agentic_systems as toolkit
from agentic_systems_studio.budget import CampaignBudget
import agentic_systems_studio.lab.protocols as transport
import capture_runresults_213 as capture

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / os.environ['AGENTIC_213_EVIDENCE_DIR']


def main():
    assert toolkit.__version__ == '2.1.3' and 'site-packages' in Path(toolkit.__file__).parts
    attempt = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    destination = OUTPUT / 'local-lessons' / attempt
    destination.mkdir(parents=True)
    budget = CampaignBudget(destination / 'zero-budget.json', {}, 'local-lessons', usd=0, requests=0)
    budget.install()
    original = transport.local_service

    @contextmanager
    def guarded_service(kind, budget=None):
        # Add only the process's real ephemeral protocol port to the zero-call guard.
        with original(kind, zero_guard) as endpoint:
            yield endpoint

    zero_guard = budget
    transport.local_service = guarded_service
    capture.install()
    rows = []
    for name in ('tutorials/frameworks/03_strands.ipynb', 'examples/agentic_systems_studio/notebooks/01_studio.ipynb'):
        path = ROOT / name
        notebook = nbformat.read(path, 4)
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        scope = {'__name__': '__main__'}
        capture.clear()
        error, health = None, None
        directory = ROOT / '.tmp/learning-local' / attempt / path.stem
        directory.mkdir(parents=True)
        previous = Path.cwd()
        os.chdir(directory)
        try:
            for index, cell in enumerate(notebook.cells):
                if cell.cell_type == 'code':
                    exec(compile(cell.source, name + ':' + str(index), 'exec'), scope)
            if 'session' in scope:
                server = scope['session']
                with urlopen(server.local_url + '_stcore/health', timeout=15) as response:
                    health = {'url': server.local_url, 'status': response.status, 'body': response.read().decode()}
                assert health['status'] == 200 and health['body'] == 'ok'
        except Exception as exc:
            error = {'type': type(exc).__name__, 'message': str(exc)[-4000:]}
        finally:
            if 'session' in scope:
                scope['session'].server.stop()
            os.chdir(previous)
        evidence = destination / (path.stem + '-runresults.json')
        capture.save(evidence, name)
        row = {'notebook': name, 'passed': error is None, 'error': error, 'source_sha256': source_hash,
               'runresults_evidence': evidence.relative_to(ROOT).as_posix(), 'server_health': health,
               'scope': 'All original code cells; local services/UI; zero authorized inference; installed SDK and Studio'}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    assert budget.summary()['attempts'] == 0
    summary = {'total': len(rows), 'passed': sum(r['passed'] for r in rows), 'inference_requests': 0, 'rows': rows}
    (destination / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    (OUTPUT / 'local-lessons.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    assert all(row['passed'] for row in rows)


if __name__ == '__main__':
    main()
