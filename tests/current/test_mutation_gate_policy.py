"""The equivalent-aware gate rejects unknown, stale and abnormal results."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import pytest

_spec = importlib.util.spec_from_file_location('mutation_gate', Path(__file__).resolve().parents[2] / 'scripts/check_mutation_gate.py')
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def fixture():
    policy = {'versions': {'python': 'p', 'mutmut': 'm'}, 'source_sha256': {'f': 'source'},
              'mutants_by_file': {'f': 2}, 'equivalents': [{'file': 'f', 'diff_sha256': gate.digest(b'approved'), 'reason': 'proof', 'reviewed_diff': 'approved'}]}
    records = [{'file': 'f', 'status': 1, 'diff_sha256': 'killed'}, {'file': 'f', 'status': 0, 'diff_sha256': gate.digest(b'approved')}]
    return policy, records


def test_equivalents_are_not_reported_as_killed():
    policy, records = fixture()
    assert gate.evaluate(policy, records, {'f': 'source'}, policy['versions']) == {
        'total': 2, 'killed': 1, 'equivalent': 1, 'unresolved': 0}


@pytest.mark.parametrize('status', [None, 2, 33, 34, 35, 36, 37])
def test_abnormal_outcomes_block(status):
    policy, records = fixture()
    records[0]['status'] = status
    with pytest.raises(ValueError):
        gate.evaluate(policy, records, {'f': 'source'}, policy['versions'])


@pytest.mark.parametrize('change', ['unknown', 'missing', 'stale', 'duplicate', 'source', 'version', 'proof'])
def test_unknown_or_stale_approvals_block(change):
    policy, records = fixture()
    sources, versions = {'f': 'source'}, deepcopy(policy['versions'])
    if change == 'unknown':
        records[1]['diff_sha256'] = 'new'
    if change == 'missing':
        records.pop()
    if change == 'stale':
        records[1]['status'] = 1
    if change == 'duplicate':
        policy['equivalents'] *= 2
    if change == 'source':
        sources['f'] = 'changed'
    if change == 'version':
        versions['python'] = 'changed'
    if change == 'proof':
        policy['equivalents'][0]['reason'] = ''
    with pytest.raises(ValueError):
        gate.evaluate(policy, records, sources, versions)


def test_cli_rejects_missing_and_stale_success_receipts(tmp_path, monkeypatch):
    import json
    import sys
    policy, records = fixture()
    (tmp_path / 'f').write_text('source')
    policy['source_sha256']['f'] = gate.digest(b'source')
    (tmp_path / 'mutation-equivalents.json').write_text(json.dumps(policy))
    (tmp_path / 'mutants').mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gate, 'version', lambda name: 'm')
    monkeypatch.setattr(gate.platform, 'python_version', lambda: 'p')
    monkeypatch.setattr(gate, 'collect', lambda root, policy: records)
    monkeypatch.setattr(gate, 'fingerprints', lambda root, policy: {'test': 'original'})
    monkeypatch.setattr(sys, 'argv', ['gate'])
    with pytest.raises(ValueError, match='Missing or stale'):
        gate.main()
    monkeypatch.setattr(sys, 'argv', ['gate', '--record-success'])
    gate.main()
    monkeypatch.setattr(sys, 'argv', ['gate'])
    gate.main()
    monkeypatch.setattr(gate, 'fingerprints', lambda root, policy: {'test': 'changed'})
    with pytest.raises(ValueError, match='Missing or stale'):
        gate.main()
