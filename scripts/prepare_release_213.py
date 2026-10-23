"""Prepare and verify the reviewed 2.1.3 delivery, without publishing or inference."""
from __future__ import annotations

import argparse
import hashlib
from decimal import Decimal
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import zipfile

from release_publication import ReleaseArtifactIdentity, ReleaseManifest, sha256, verify_artifacts

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path('revisions/2.1.3/closeout-artifacts')
EVIDENCE = Path('revisions/2.1.3/closeout-evidence')
VERSION = '2.1.3'
WHEEL = 'agentic_systems-2.1.3-py3-none-any.whl'
SDIST = 'agentic_systems-2.1.3.tar.gz'
STUDIO = 'agentic_systems_studio-2.1.3-py3-none-any.whl'
STUDIO_ZIP = 'agentic-systems-studio-2.1.3-final-local.zip'
GUIDE = '01_api_user_guide.ipynb'
EVIDENCE_ZIP = 'agentic-systems-2.1.3-validation.zip'
SDK_SHA = 'b09785bc75faa97d15b4cf4c1fc25b18741319ce1b8024641c9597930115b283'
SDIST_SHA = '88169951ced5c823bda436e15e227529f0133bd7efa422bf400f54e49e65b03f'
STUDIO_SHA = '4aed36644d555e5a05f80da034645ed2dd9a6f100dccd224cddeef93a07adab4'
PROFILE = 'single-api-213-reviewed-v1'
LEARNING_ARCHIVE = 'revisions/2.1.3/published-learning-source.zip'
LEARNING_SHA = '15061c2fbd0438dcc06afcc6016162188d3d879aa9b1c1767581c0639ddc7ae7'
NOTES_SHA = '48defff5e81c8bb1ebff5f74a433c86316b940f8611e49c101e00739663a1903'
PHASES = {'matrix': 16, 'features': 15, 'integrated': 16, 'studio': 16, 'studio-ui': 12}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def package_bytes(wheel, package):
    with zipfile.ZipFile(wheel) as archive:
        return {name: archive.read(name) for name in archive.namelist()
                if name.startswith(package + '/') and not name.endswith('/')}


def verify_reviewed(root=ROOT):
    """Verify published bytes; current learning material has separate acceptance."""
    manifest = read(root / EVIDENCE / 'manifest.json')
    archived = {}
    if (root / LEARNING_ARCHIVE).exists():
        require(sha256(root / LEARNING_ARCHIVE) == LEARNING_SHA, 'Published learning archive changed')
        with zipfile.ZipFile(root / LEARNING_ARCHIVE) as archive:
            archived = {name: archive.read(name) for name in archive.namelist()}
        require(all(name in manifest['sha256'] and hashlib.sha256(data).hexdigest() == manifest['sha256'][name]
                    for name, data in archived.items()), 'Archive differs from original acceptance')

    def reviewed_bytes(name):
        return archived[name] if name in archived else (root / name).read_bytes()
    # Operational fixes can evolve after live acceptance. Package and application
    # declarations, source notebooks and all original evidence must stay exact.
    operational = ('.github/workflows/', 'scripts/', 'tests/')
    harnesses = {'examples/run_offline_213.py', 'examples/catalog_tools.py'}
    changes = []
    for name, expected in manifest['sha256'].items():
        path = root / name
        if not path.is_file() or sha256(path) != expected:
            require(name.startswith(operational) or name in harnesses or name in archived, f'Reviewed source/evidence changed: {name}')
            changes.append(name)
    for name, expected in ((WHEEL, SDK_SHA), (SDIST, SDIST_SHA), (STUDIO, STUDIO_SHA)):
        require(sha256(root / ARTIFACTS / name) == expected, f'Reviewed artifact changed: {name}')
    require(sha256(root / ARTIFACTS / 'RELEASE_NOTES_213.md') == NOTES_SHA, 'Published release notes changed')
    for name, package, source in ((WHEEL, 'agentic_systems', root / 'src'),
                                   (STUDIO, 'agentic_systems_studio', root / 'examples/agentic_systems_studio/src')):
        expected = package_bytes(root / ARTIFACTS / name, package)
        actual = {p.relative_to(source).as_posix(): p.read_bytes() for p in (source / package).rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
        require(actual == expected, f'Current {package} source differs from the reviewed wheel')
    with tarfile.open(root / ARTIFACTS / SDIST) as archive:
        files = {member.name.split('/', 1)[1]: archive.extractfile(member).read()
                 for member in archive.getmembers() if member.isfile() and '/' in member.name}
    for name in ('README.md', 'pyproject.toml', 'LICENSE'):
        if (root / name).exists():
            require(files[name] == reviewed_bytes(name), f'Frozen packaging input changed: {name}')
    for name, data in package_bytes(root / ARTIFACTS / WHEEL, 'agentic_systems').items():
        require(files['src/' + name] == data, 'sdist and wheel source differ')
    for phase, count in PHASES.items():
        result = read(root / EVIDENCE / (phase + '.json'))
        require(result['all_passed'] and result['wheel_sha256'] == SDK_SHA, f'{phase}: acceptance identity differs')
        require(result['passed'] == result['planned'] == result['executed'] == count, f'{phase}: incomplete acceptance')
        require(len({row['name'] for row in result['rows']}) == len(result['rows']) == count, f'{phase}: duplicate cases')
        for row in result['rows']:
            require(row['passed'] is True, f'{phase}: failed acceptance row')
            case = read(root / result['attempt_directory'] / (row['name'] + '.json'))
            require(case['passed'] is True and case['name'] == row['name'], f'{phase}: case evidence differs')
    budget = read(root / EVIDENCE / 'budget.json')
    reserved = sum((Decimal(row['reserved_usd']) for row in budget['attempts']), Decimal(0))
    require(budget['limits'] == {'usd': 10, 'requests': 300}, 'Unexpected final campaign allocation')
    require(len(budget['attempts']) <= 300 and reserved <= Decimal(10), 'Campaign limit exceeded')
    books = read(root / EVIDENCE / 'notebooks.json')
    require(books['passed'] == books['total'] == 13, 'Incomplete notebook acceptance')
    for row in books['notebooks']:
        require(row['passed'] and hashlib.sha256(reviewed_bytes(row['notebook'])).hexdigest() == row['source_sha256'], 'Notebook changed after acceptance')
    with zipfile.ZipFile(root / ARTIFACTS / STUDIO_ZIP) as archive:
        require(archive.read('wheels/' + WHEEL) == (root / ARTIFACTS / WHEEL).read_bytes(), 'Studio bundle contains another SDK')
        require(archive.read('wheels/' + STUDIO) == (root / ARTIFACTS / STUDIO).read_bytes(), 'Studio bundle contains another Studio')
        require(not any(Path(n).name == '.env' for n in archive.namelist()), 'Studio bundle contains dotenv credentials')
    require((root / ARTIFACTS / GUIDE).read_bytes() == reviewed_bytes('examples/api_walkthrough/' + GUIDE), 'Downloadable guide differs')
    return {'profile': PROFILE, 'sdk_wheel_sha256': SDK_SHA, 'sdk_sdist_sha256': SDIST_SHA,
            'studio_wheel_sha256': STUDIO_SHA, 'online_scenarios_passed': sum(PHASES.values()),
            'notebooks_passed': 13, 'budget': {'attempts': len(budget['attempts']), 'reserved_usd': str(reserved)},
            'operational_changes_since_live_snapshot': changes, 'inference_requests_this_verification': 0}


def build_manifest(directory):
    summary = read(directory / 'final-certification-summary.json')
    require(summary['acceptance_profile'] == PROFILE and summary['package_version'] == VERSION, 'Unexpected delivery profile')
    require(summary['sdk_wheel_sha256'] == SDK_SHA and summary['sdk_sdist_sha256'] == SDIST_SHA, 'Unreviewed SDK')
    require(sha256(directory / WHEEL) == SDK_SHA and sha256(directory / SDIST) == SDIST_SHA, 'SDK bytes differ from live acceptance')
    require(summary['online_scenarios_passed'] == 75 and summary['notebooks_passed'] == 13, 'Acceptance incomplete')
    filenames = (WHEEL, SDIST, STUDIO_ZIP, GUIDE, EVIDENCE_ZIP, 'final-certification-summary.json', 'RELEASE_NOTES_213.md')
    artifacts = [ReleaseArtifactIdentity(filename=name, sha256=sha256(directory / name),
                 kind='bdist_wheel' if name == WHEEL else 'sdist' if name == SDIST else 'asset') for name in filenames]
    sums = directory / 'SHA256SUMS-2.1.3.txt'
    content = ''.join(f'{a.sha256}  {a.filename}\n' for a in artifacts)
    if sums.exists():
        require(sums.read_text() == content, 'Existing checksums differ')
    else:
        sums.write_text(content, encoding='utf-8', newline='\n')
    artifacts.append(ReleaseArtifactIdentity(filename=sums.name, sha256=sha256(sums), kind='asset'))
    manifest = ReleaseManifest(project='agentic-systems', version=VERSION,
                               commit_sha=summary['assembly_commit_sha'], artifacts=artifacts)
    verify_artifacts(manifest, directory)
    target = directory / 'release-manifest.json'
    content = manifest.model_dump_json(indent=2) + '\n'
    if target.exists():
        require(target.read_text() == content, 'Never replace an existing release manifest')
    else:
        target.write_text(content, encoding='utf-8', newline='\n')
    return target


def prepare(directory, commit, root=ROOT):
    require(bool(re.fullmatch(r'[a-f0-9]{40}', commit)), 'Commit must be a full SHA')
    report = verify_reviewed(root)
    require(not directory.exists(), 'Choose a new output directory; never overwrite a candidate')
    directory.mkdir(parents=True)
    for name in (WHEEL, SDIST, STUDIO_ZIP, GUIDE):
        shutil.copyfile(root / ARTIFACTS / name, directory / name)
    # The preview uses the downloaded, hash-verified published notes. Current
    # learning material has its own campaign and cannot recertify this version.
    shutil.copyfile(root / ARTIFACTS / 'RELEASE_NOTES_213.md', directory / 'RELEASE_NOTES_213.md')
    with zipfile.ZipFile(directory / EVIDENCE_ZIP, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((root / EVIDENCE).rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(root).as_posix())
        for name in ('docs/RUNRESULTS_LINEAGE_213.md', 'docs/NOTEBOOK_INVENTORY_213.md',
                     'docs/notebook_inventory_213.json', 'docs/notebook_parameters_213.csv'):
            with zipfile.ZipFile(root / LEARNING_ARCHIVE) as frozen:
                archive.writestr(name, frozen.read(name))
    summary = {**report, 'schema_version': 'agentic_systems.release-readiness-213.v1',
               'acceptance_profile': PROFILE, 'package_version': VERSION, 'assembly_commit_sha': commit,
               'state': 'reviewed-artifacts-not-published',
               'pending_environment_validation': ['vLLM/Colab GPU', 'AWS IAM', 'ADA IAM'],
               'note': 'Local live acceptance is preserved. The workflow independently requires all five Python CI jobs for this commit.'}
    (directory / 'final-certification-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    return build_manifest(directory)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--commit')
    args = parser.parse_args()
    if args.output:
        commit = args.commit or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        target = prepare(args.output.resolve(), commit)
        print(json.dumps({'manifest': str(target), 'sha256': sha256(target), 'published': False}))
    else:
        print(json.dumps(verify_reviewed()))
