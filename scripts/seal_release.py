"""Seal exact quality-built approved artifacts, retaining mutation evidence."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

from release_publication import ReleaseArtifactIdentity, ReleaseManifest, sha256, verify_artifacts
from seal_release_214 import bundle, verify_logic

ROOT = Path(__file__).resolve().parents[1]


def verify_delivery(distributions, build, policy, version, commit):
    if (policy['release'] != version or policy['mode'] not in {'offline-verified-maintenance-release', 'offline-verified-feature-release'}
            or policy['new_live_inference'] is not False):
        raise ValueError('Release policy does not authorize this version/mode')
    if build['version'] != version or build['commit'] != commit:
        raise ValueError('Quality build belongs to another version/commit')
    expected = {f'agentic_systems-{version}-py3-none-any.whl', f'agentic_systems-{version}.tar.gz'}
    if set(build['artifacts']) != expected:
        raise ValueError('Quality build must identify exactly the SDK wheel and sdist')
    for name in expected:
        path = distributions / name
        if path.is_symlink() or not path.is_file() or sha256(path) != build['artifacts'][name]:
            raise ValueError('Quality artifact changed: ' + name)
    return verify_logic(distributions / f'agentic_systems-{version}-py3-none-any.whl', policy)


def verify_mutation(directory, policy_bytes):
    if (directory / 'mutation-equivalents.json').read_bytes() != policy_bytes:
        raise ValueError('Mutation approvals differ from current source')
    policy = json.loads(policy_bytes)
    report = json.loads((directory / 'mutation-gate.json').read_text())
    total = sum(policy['mutants_by_file'].values())
    equivalents = len(policy['equivalents'])
    if report != {'total': total, 'killed': total - equivalents,
                  'equivalent': equivalents, 'unresolved': 0}:
        raise ValueError('Mutation gate is incomplete or unresolved')
    for name in ('mutation-results.txt', 'mutation-run.log'):
        if not (directory / name).is_file() or not (directory / name).stat().st_size:
            raise ValueError('Missing raw mutation evidence: ' + name)
    return report


def seal(quality, mutation, policy_path, output):
    policy = json.loads(policy_path.read_text())
    version = policy['release']
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Invalid release version')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    build = json.loads((quality / 'manifest.json').read_text())
    distributions = quality / 'dist'
    checked = verify_delivery(distributions, build, policy, version, commit)
    required = {'pyproject.toml', 'README.md', 'CHANGELOG.md',
                *(p.relative_to(ROOT).as_posix() for p in (ROOT / 'src').rglob('*.py'))}
    if (ROOT / 'setup.py').is_file():
        required.add('setup.py')
        required.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'skills/agentic-systems').rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.pyo'})
    if set(build['source_sha256']) != required:
        raise ValueError('Quality source fingerprint scope changed')
    for name, expected in build['source_sha256'].items():
        if sha256(ROOT / name) != expected:
            raise ValueError('Quality source changed: ' + name)
    report = verify_mutation(mutation, (ROOT / 'mutation-equivalents.json').read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    for name in build['artifacts']:
        shutil.copyfile(distributions / name, output / name)
    bundle(output / f'agentic-systems-skill-{version}.zip',
           [(ROOT / 'skills/agentic-systems', Path('agentic-systems'))])
    for application, root, package in (
            ('studio', ROOT / 'examples/agentic_systems_studio', 'agentic_systems_studio'),
            ('ada', ROOT / 'integrations/ada', 'agentic_systems_ada')):
        wheel = distributions / f'{package}-{version}-py3-none-any.whl'
        if not wheel.is_file():
            raise ValueError('Missing quality-tested optional application: ' + wheel.name)
        bundle(output / f'agentic-systems-{application}-{version}.zip',
               [(root, Path(application)), (wheel, Path(application) / 'wheels')])
    bundle(output / f'agentic-systems-learning-{version}.zip',
           [(ROOT / name, Path(name)) for name in ('tutorials', 'examples', 'docs')])
    bundle(output / f'mutation-evidence-{version}.zip', [(mutation, Path('mutation'))])
    shutil.copyfile(ROOT / 'docs' / f'RELEASE_NOTES_{version.replace(".", "")}.md',
                    output / 'release-notes.md')
    shutil.copyfile(policy_path, output / 'acceptance-policy.json')
    acceptance = {'version': version, 'commit_sha': commit,
                  'wheel_sha256': sha256(distributions / f'agentic_systems-{version}-py3-none-any.whl'),
                  'offline_passed': True, 'python_versions': ['3.10', '3.11', '3.12', '3.13', '3.14'],
                  'live_passed_on_this_artifact': False, 'new_inference': False,
                  'acceptance_mode': policy['mode'], 'reference_commit_sha': policy['reference_commit_sha'],
                  'executable_files_compared': checked, 'mutation': report,
                  'known_limitations': policy['known_limitations']}
    (output / 'acceptance.json').write_text(json.dumps(acceptance, indent=2) + '\n')
    manifest = ReleaseManifest(project='agentic-systems', version=version, commit_sha=commit,
        artifacts=tuple(ReleaseArtifactIdentity(filename=p.name, sha256=sha256(p),
                        kind='bdist_wheel' if p.suffix == '.whl' else 'sdist' if p.name.endswith('.tar.gz') else 'asset')
                        for p in sorted(output.iterdir())))
    path = output / 'release-manifest.json'
    path.write_text(manifest.model_dump_json(indent=2) + '\n')
    verify_artifacts(manifest, output)
    print('Manifest SHA256:', sha256(path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quality', type=Path, required=True)
    parser.add_argument('--mutation', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    seal(args.quality, args.mutation, args.policy, args.output)
