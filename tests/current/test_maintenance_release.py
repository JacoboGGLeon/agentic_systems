"""Maintenance sealing rejects changed bytes, identities and incomplete evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

import pytest


def module():
    scripts = Path(__file__).resolve().parents[2] / 'scripts'
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location('maintenance_seal', scripts / 'seal_release.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize('change', ['none', 'bytes', 'logic', 'version', 'commit', 'scope', 'mode', 'live'])
def test_maintenance_delivery_rejects_unapproved_payload(tmp_path, change):
    seal = module()
    init = b'__version__ = "2.1.5"\n'
    logic = b'def work(): return 1\n'
    wheel = tmp_path / 'agentic_systems-2.1.5-py3-none-any.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr('agentic_systems/__init__.py', init)
        archive.writestr('agentic_systems/work.py', logic if change != 'logic' else b'def work(): return 2\n')
    sdist = tmp_path / 'agentic_systems-2.1.5.tar.gz'
    sdist.write_bytes(b'sdist-fixture')
    build = {'version': '2.1.5', 'commit': 'a' * 40,
             'artifacts': {p.name: seal.sha256(p) for p in (wheel, sdist)}}
    policy = {'release': '2.1.5', 'mode': 'offline-verified-maintenance-release',
              'new_live_inference': False,
              'reference_python_sha256': {'agentic_systems/__init__.py': 'historical',
                                          'agentic_systems/work.py': hashlib.sha256(logic).hexdigest()},
              'stable_init_sha256': hashlib.sha256(init).hexdigest()}
    if change == 'bytes':
        sdist.write_bytes(b'changed-after-quality')
    elif change in ('version', 'commit'):
        build[change] = 'wrong'
    elif change == 'scope':
        build['artifacts'].pop(sdist.name)
    elif change == 'mode':
        policy['mode'] = 'unreviewed'
    elif change == 'live':
        policy['new_live_inference'] = True
    if change == 'none':
        assert seal.verify_delivery(tmp_path, build, policy, '2.1.5', 'a' * 40) == 2
    else:
        with pytest.raises(ValueError):
            seal.verify_delivery(tmp_path, build, policy, '2.1.5', 'a' * 40)


@pytest.mark.parametrize('change', ['none', 'approvals', 'unresolved', 'incomplete', 'raw'])
def test_maintenance_requires_exact_mutation_evidence(tmp_path, change):
    seal = module()
    policy = json.dumps({'mutants_by_file': {'file.py': 3}, 'equivalents': [{}]}).encode()
    (tmp_path / 'mutation-equivalents.json').write_bytes(policy if change != 'approvals' else b'{}')
    report = {'total': 3, 'killed': 2, 'equivalent': 1, 'unresolved': 0}
    if change == 'unresolved':
        report['unresolved'] = 1
    elif change == 'incomplete':
        report['total'] = 2
    (tmp_path / 'mutation-gate.json').write_text(json.dumps(report))
    for name in ('mutation-results.txt', 'mutation-run.log'):
        (tmp_path / name).write_text('raw evidence' if change != 'raw' else '')
    if change == 'none':
        assert seal.verify_mutation(tmp_path, policy) == report
    else:
        with pytest.raises(ValueError):
            seal.verify_mutation(tmp_path, policy)


@pytest.mark.parametrize('change', ['none', 'source', 'application'])
def test_seal_retains_bound_evidence_without_rebuilding(tmp_path, monkeypatch, change):
    seal = module()
    root = tmp_path / 'source'
    quality = tmp_path / 'quality'
    dist = quality / 'dist'
    mutation = tmp_path / 'mutation'
    dist.mkdir(parents=True)
    mutation.mkdir()
    files = {'pyproject.toml': 'version = "2.1.5"', 'README.md': 'Read me',
             'CHANGELOG.md': 'Changes', 'src/agentic_systems/__init__.py': '__version__ = "2.1.5"\n',
             'src/agentic_systems/work.py': 'def work(): return 1\n',
             'skills/agentic-systems/SKILL.md': 'Skill', 'docs/RELEASE_NOTES_215.md': 'Notes',
             'tutorials/lesson.md': 'Lesson', 'examples/agentic_systems_studio/README.md': 'Studio',
             'integrations/ada/README.md': 'ADA'}
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    policy_bytes = json.dumps({'mutants_by_file': {'file.py': 3}, 'equivalents': [{}]}).encode()
    (root / 'mutation-equivalents.json').write_bytes(policy_bytes)
    (mutation / 'mutation-equivalents.json').write_bytes(policy_bytes)
    report = {'total': 3, 'killed': 2, 'equivalent': 1, 'unresolved': 0}
    (mutation / 'mutation-gate.json').write_text(json.dumps(report))
    for name in ('mutation-results.txt', 'mutation-run.log'):
        (mutation / name).write_text('original raw evidence')
    wheel = dist / 'agentic_systems-2.1.5-py3-none-any.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        for name in ('__init__.py', 'work.py'):
            archive.write(root / 'src/agentic_systems' / name, 'agentic_systems/' + name)
    sdist = dist / 'agentic_systems-2.1.5.tar.gz'
    sdist.write_bytes(b'original quality sdist')
    for package in ('agentic_systems_studio', 'agentic_systems_ada'):
        (dist / f'{package}-2.1.5-py3-none-any.whl').write_bytes(b'quality application')
    bound = ['pyproject.toml', 'README.md', 'CHANGELOG.md',
             'src/agentic_systems/__init__.py', 'src/agentic_systems/work.py']
    build = {'version': '2.1.5', 'commit': 'a' * 40,
             'artifacts': {p.name: seal.sha256(p) for p in (wheel, sdist)},
             'source_sha256': {name: seal.sha256(root / name) for name in bound}}
    (quality / 'manifest.json').write_text(json.dumps(build))
    policy = {'release': '2.1.5', 'mode': 'offline-verified-maintenance-release', 'new_live_inference': False,
              'reference_python_sha256': {name.removeprefix('src/'): seal.sha256(root / name)
                                          for name in bound if name.startswith('src/')},
              'stable_init_sha256': seal.sha256(root / 'src/agentic_systems/__init__.py'),
              'reference_commit_sha': 'b' * 40, 'known_limitations': ['No new live acceptance']}
    policy_path = tmp_path / 'policy.json'
    policy_path.write_text(json.dumps(policy))
    monkeypatch.setattr(seal, 'ROOT', root)
    monkeypatch.setattr(seal.subprocess, 'check_output', lambda *args, **kwargs: 'a' * 40)
    if change == 'source':
        (root / 'README.md').write_text('changed after quality')
    elif change == 'application':
        (dist / 'agentic_systems_ada-2.1.5-py3-none-any.whl').unlink()
    output = tmp_path / 'sealed'
    if change != 'none':
        with pytest.raises(ValueError):
            seal.seal(quality, mutation, policy_path, output)
        assert not (output / 'release-manifest.json').exists()
        return
    seal.seal(quality, mutation, policy_path, output)
    manifest = seal.ReleaseManifest.model_validate_json((output / 'release-manifest.json').read_bytes())
    seal.verify_artifacts(manifest, output)
    assert (output / wheel.name).read_bytes() == wheel.read_bytes()
    assert (output / sdist.name).read_bytes() == sdist.read_bytes()
    acceptance = json.loads((output / 'acceptance.json').read_text())
    assert acceptance['live_passed_on_this_artifact'] is False
    assert acceptance['new_inference'] is False and acceptance['mutation'] == report


def test_feature_policy_pins_exact_reviewed_payload(tmp_path):
    seal = module()
    wheel = tmp_path / 'agentic_systems-2.1.7-py3-none-any.whl'
    init, cli = b'__version__ = "2.1.7"\n', b'def main(): return 0\n'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr('agentic_systems/__init__.py', init)
        archive.writestr('agentic_systems/cli.py', cli)
    sdist = tmp_path / 'agentic_systems-2.1.7.tar.gz'
    sdist.write_bytes(b'source')
    policy = {'release': '2.1.7', 'mode': 'offline-verified-feature-release', 'new_live_inference': False,
              'reference_python_sha256': {'agentic_systems/__init__.py': hashlib.sha256(init).hexdigest(),
                                          'agentic_systems/cli.py': hashlib.sha256(cli).hexdigest()},
              'stable_init_sha256': hashlib.sha256(init).hexdigest()}
    build = {'version': '2.1.7', 'commit': 'a' * 40,
             'artifacts': {p.name: seal.sha256(p) for p in (wheel, sdist)}}
    assert seal.verify_delivery(tmp_path, build, policy, '2.1.7', 'a' * 40) == 2
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr('agentic_systems/__init__.py', init)
        archive.writestr('agentic_systems/cli.py', b'def main(): return 99\n')
    # Even after transport hashes are updated, unreviewed executable bytes fail.
    build['artifacts'][wheel.name] = seal.sha256(wheel)
    with pytest.raises(ValueError, match='Unapproved executable difference'):
        seal.verify_delivery(tmp_path, build, policy, '2.1.7', 'a' * 40)
