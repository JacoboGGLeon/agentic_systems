"""Publication tests use local files and index fixtures; no uploads or inference."""
import json
import shutil

import pytest

from prepare_release_213 import (
    ARTIFACTS, EVIDENCE_ZIP, GUIDE, PHASES, PROFILE, ROOT, SDK_SHA, SDIST,
    SDIST_SHA, STUDIO_ZIP, VERSION, WHEEL, build_manifest, prepare, verify_reviewed,
)
from release_publication import (
    PublicationDecision, ReleaseArtifactIdentity, ReleaseManifest,
    check_index, load_manifest, reconcile, sha256, verify_artifacts,
)


def minimal_delivery(directory):
    directory.mkdir()
    for name in (WHEEL, SDIST, STUDIO_ZIP, GUIDE, EVIDENCE_ZIP, 'RELEASE_NOTES_213.md'):
        if name in (WHEEL, SDIST):
            shutil.copyfile(ROOT / ARTIFACTS / name, directory / name)
        else:
            (directory / name).write_text(name)
    summary = {'schema_version': 'agentic_systems.release-readiness-213.v1',
               'acceptance_profile': PROFILE, 'package_version': VERSION,
               'sdk_wheel_sha256': SDK_SHA, 'sdk_sdist_sha256': SDIST_SHA,
               'online_scenarios_passed': 75, 'notebooks_passed': 13,
               'assembly_commit_sha': 'a' * 40}
    (directory / 'final-certification-summary.json').write_text(json.dumps(summary))
    return directory


def test_reviewed_sdk_source_and_live_evidence_are_still_identical():
    report = verify_reviewed()
    assert report['sdk_wheel_sha256'] == SDK_SHA
    assert report['online_scenarios_passed'] == sum(PHASES.values()) == 75
    assert report['budget'] == {'attempts': 238, 'reserved_usd': '9.673028'}


def test_build_is_repeatable_and_detects_changed_bytes(tmp_path):
    directory = minimal_delivery(tmp_path / 'delivery')
    manifest = build_manifest(directory)
    original = manifest.read_bytes()
    assert build_manifest(directory).read_bytes() == original
    parsed = load_manifest(manifest, sha256(manifest))
    assert {a.filename for a in parsed.artifacts if a.kind != 'asset'} == {WHEEL, SDIST}
    verify_artifacts(parsed, directory)
    (directory / WHEEL).write_bytes(b'changed')
    with pytest.raises(ValueError, match='SHA256'):
        verify_artifacts(parsed, directory)
    with pytest.raises(ValueError, match='SDK bytes differ'):
        build_manifest(directory)


def test_no_overwrite_or_invalid_commit(tmp_path):
    target = tmp_path / 'delivery'
    target.mkdir()
    marker = target / 'keep.txt'
    marker.write_text('preserve')
    with pytest.raises(ValueError, match='never overwrite'):
        prepare(target, 'a' * 40)
    assert marker.read_text() == 'preserve'
    with pytest.raises(ValueError, match='full SHA'):
        prepare(tmp_path / 'other', 'main')


def test_altered_packaging_inputs_are_rejected(tmp_path):
    # A tiny mirror is enough: the review rejects the changed notebook hash
    # before reading any package or starting a subprocess.
    from prepare_release_213 import EVIDENCE
    (tmp_path / EVIDENCE).mkdir(parents=True)
    (tmp_path / EVIDENCE / 'manifest.json').write_text(json.dumps({'sha256': {'tutorials/00_api.ipynb': '0' * 64}}))
    with pytest.raises(ValueError, match='Reviewed source/evidence changed'):
        verify_reviewed(tmp_path)


def index_fixture(manifest):
    return {'info': {'name': 'agentic-systems', 'version': VERSION}, 'urls': [
        {'filename': a.filename, 'packagetype': a.kind, 'digests': {'sha256': a.sha256}, 'yanked': False}
        for a in manifest.artifacts if a.kind != 'asset']}


@pytest.fixture
def release_manifest():
    return ReleaseManifest(project='agentic-systems', version=VERSION, commit_sha='a' * 40, artifacts=(
        ReleaseArtifactIdentity(filename=WHEEL, kind='bdist_wheel', sha256=SDK_SHA),
        ReleaseArtifactIdentity(filename=SDIST, kind='sdist', sha256=SDIST_SHA)))


def test_complete_index_is_idempotent_and_absent_is_distinct(release_manifest):
    assert reconcile(release_manifest, None).decision == PublicationDecision.ABSENT
    assert reconcile(release_manifest, index_fixture(release_manifest)).decision == PublicationDecision.MATCHING


@pytest.mark.parametrize('change', ['partial', 'hash', 'yanked', 'duplicate', 'foreign'])
def test_index_conflicts_block_publication(release_manifest, change):
    payload = index_fixture(release_manifest)
    if change == 'partial':
        payload['urls'].pop()
    elif change == 'hash':
        payload['urls'][0]['digests']['sha256'] = '0' * 64
    elif change == 'yanked':
        payload['urls'][0]['yanked'] = True
    elif change == 'duplicate':
        payload['urls'].append(payload['urls'][0])
    else:
        payload['info']['name'] = 'another-project'
    assert reconcile(release_manifest, payload).decision == PublicationDecision.CONFLICT
    with pytest.raises(ValueError):
        check_index(release_manifest, attempts=1, fetch=lambda *a, **kw: payload)


def test_absence_never_satisfies_production_prerequisite(release_manifest):
    with pytest.raises(TimeoutError, match='did not become visible'):
        check_index(release_manifest, index='testpypi', require_present=True, attempts=1, fetch=lambda *a, **kw: None)


def test_release_workflow_no_longer_uses_retired_api():
    workflow = (ROOT / '.github/workflows/release.yml').read_text()
    assert 'a.api_contract()' not in workflow
    assert 'confirm_publish' in workflow and '--require-present' in workflow
    assert '--index testpypi' in workflow
    assert sha256(ROOT / ARTIFACTS / WHEEL) == SDK_SHA


def test_manifest_rejects_path_traversal():
    with pytest.raises(ValueError, match='plain filename'):
        ReleaseArtifactIdentity(filename='../escape.whl', kind='bdist_wheel', sha256='0' * 64)
