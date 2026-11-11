"""Fail closed on every unresolved mutant; retain reviewed equivalents in raw totals."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform


def digest(value):
    return hashlib.sha256(value).hexdigest()


def fingerprints(root, policy):
    paths = [root / p for p in policy['source_sha256']]
    paths += sorted((root / 'tests').rglob('*.py'))
    paths += sorted((root / 'mutants').rglob('*.meta'))
    paths += [root / 'scripts/check_mutation_gate.py', root / 'pyproject.toml', root / '.github/workflows/mutation.yml']
    return {str(p.relative_to(root)): digest(p.read_bytes()) for p in paths}


def evaluate(policy, records, sources, versions):
    if versions != policy['versions']:
        raise ValueError('Tool/Python versions changed; review approvals')
    if sources != policy['source_sha256']:
        raise ValueError('Source changed; review approvals')
    expected = policy['mutants_by_file']
    if set(expected) != set(sources):
        raise ValueError('Unbound mutation scope')
    counts = {path: sum(r['file'] == path for r in records) for path in expected}
    if not records or counts != expected or any(r['file'] not in expected for r in records):
        raise ValueError(f'Incomplete or changed mutation catalog: observed={counts}, expected={expected}')
    approved = policy['equivalents']
    keys = [(a['file'], a['diff_sha256']) for a in approved]
    if (len(set(keys)) != len(keys) or any(
            not a.get('reason') or digest(a.get('reviewed_diff', '').encode()) != a['diff_sha256']
            for a in approved)):
        raise ValueError('Invalid equivalence approvals')
    seen, killed, equivalent = set(), 0, 0
    for record in records:
        if record['status'] in (1, 3):
            killed += 1
        elif record['status'] == 0:
            key = (record['file'], record['diff_sha256'])
            if key not in keys or key in seen:
                raise ValueError('Unreviewed or duplicate survivor')
            seen.add(key)
            equivalent += 1
        else:
            raise ValueError('Pending, timeout, suspicious or no-tests outcome')
    if seen != set(keys):
        raise ValueError('Stale equivalence approvals')
    return {'total': len(records), 'killed': killed, 'equivalent': equivalent, 'unresolved': 0}


def collect(root, policy):
    from mutmut.mutation.diff_apply import get_diff_for_mutant
    import tomllib
    selected = tomllib.loads((root / 'pyproject.toml').read_text())['tool']['mutmut']['only_mutate']
    if set(selected) != set(policy['mutants_by_file']):
        raise ValueError('Mutation scope changed')
    records = []
    for path in policy['mutants_by_file']:
        metadata = root / 'mutants' / (path + '.meta')
        for name, status in json.loads(metadata.read_text())['exit_code_by_key'].items():
            diff = get_diff_for_mutant(name, path=path) if status == 0 else ''
            records.append({'file': path, 'name': name, 'status': status,
                            'diff_sha256': digest(diff.encode())})
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--record-success', action='store_true', help='CI only: after successful mutmut run')
    args = parser.parse_args()
    root = Path.cwd()
    policy = json.loads((root / 'mutation-equivalents.json').read_text())
    versions = {'python': platform.python_version(), 'mutmut': version('mutmut')}
    sources = {p: digest((root / p).read_bytes()) for p in policy['source_sha256']}
    report = evaluate(policy, collect(root, policy), sources, versions)
    receipt = root / 'mutants' / 'successful-run.json'
    current = {'fingerprints': fingerprints(root, policy), 'versions': versions,
               'policy_sha256': digest((root / 'mutation-equivalents.json').read_bytes())}
    if args.record_success:
        receipt.write_text(json.dumps(current, indent=2))
    elif not receipt.exists() or json.loads(receipt.read_text()) != current:
        raise ValueError('Missing or stale successful-run receipt')
    (root / 'mutation-gate.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
