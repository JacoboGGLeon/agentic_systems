"""Verify the recorded learning campaign without credentials or inference."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'revisions/2.1.3/learning-evidence-elevated'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((EVIDENCE / 'learning-manifest.json').read_text(encoding='utf-8'))
    for group in ('source_sha256', 'evidence_sha256'):
        for name, expected in manifest[group].items():
            path = (ROOT / name).resolve()
            path.relative_to(ROOT)
            assert path.is_file() and digest(path) == expected, 'Learning acceptance changed: ' + name
    assert digest(EVIDENCE / 'budget.json') == manifest['budget_sha256']
    budget = json.loads((EVIDENCE / 'budget.json').read_text(encoding='utf-8'))
    reserved = sum((Decimal(r['reserved_usd']) for r in budget['attempts']), Decimal(0))
    assert budget['limits'] == {'usd': 10, 'requests': 300}
    assert len(budget['attempts']) <= 300 and reserved <= 10
    wheel = ROOT / 'revisions/2.1.3/closeout-artifacts/agentic_systems-2.1.3-py3-none-any.whl'
    assert digest(wheel) == manifest['sdk_wheel_sha256']
    live = json.loads((EVIDENCE / 'live-notebooks.json').read_text(encoding='utf-8'))
    assert live['planned'] == live['executed'] == live['passed'] == 12
    assert len({(r['notebook'], r['framework']) for r in live['rows']}) == 12
    for phase, count in (('features', 15), ('integrated', 16), ('studio', 16), ('studio-ui', 12)):
        result = json.loads((EVIDENCE / (phase + '.json')).read_text(encoding='utf-8'))
        assert result['all_passed'] and result['planned'] == result['executed'] == result['passed'] == count
        assert result['wheel_sha256'] == manifest['sdk_wheel_sha256']
    print(json.dumps({'source_files': len(manifest['source_sha256']),
        'evidence_files': len(manifest['evidence_sha256']), 'attempts': len(budget['attempts']),
        'reserved_usd': str(reserved), 'inference_requests_this_verification': 0}))


if __name__ == '__main__':
    main()
