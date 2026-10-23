"""Learning navigation and archived-publication boundaries; no inference."""
import hashlib
import json
import zipfile

import nbformat
import pytest
from prepare_release_213 import ARTIFACTS, LEARNING_ARCHIVE, LEARNING_SHA, NOTES_SHA, ROOT, verify_reviewed


def test_course_is_organized_and_core_is_self_contained():
    paths = list((ROOT / 'tutorials').rglob('*.ipynb'))
    assert len(paths) == 19
    assert {p.parent.name for p in paths} == {'core', 'providers', 'frameworks', 'api'}
    assert not list((ROOT / 'tutorials').glob('*.ipynb'))
    for path in paths:
        notebook = nbformat.read(path, 4)
        code = '\n'.join(c.source for c in notebook.cells if c.cell_type == 'code')
        assert 'import agentic_systems as toolkit' in code
        assert 'lesson_examples' not in code and 'sys.path' not in code
    for name in ('01_openai', '02_ollama', '03_bedrock'):
        notebook = nbformat.read(ROOT / 'tutorials/providers' / (name + '.ipynb'), 4)
        live = [c for c in notebook.cells if 'live' in c.metadata.get('tags', [])]
        assert len(live) == 2 and any('actor.run' in c.source for c in live)


def test_original_learning_snapshot_is_independently_pinned():
    archive = ROOT / LEARNING_ARCHIVE
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == LEARNING_SHA
    manifest = json.loads((ROOT / 'revisions/2.1.3/closeout-evidence/manifest.json').read_text())
    with zipfile.ZipFile(archive) as saved:
        for name in saved.namelist():
            assert hashlib.sha256(saved.read(name)).hexdigest() == manifest['sha256'][name]
        assert b'no se ha publicado' in saved.read('README.md')
    assert '2.1.3 está publicada' in (ROOT / 'README.md').read_text(encoding='utf-8-sig')
    assert hashlib.sha256((ROOT / ARTIFACTS / 'RELEASE_NOTES_213.md').read_bytes()).hexdigest() == NOTES_SHA


def test_bad_snapshot_is_rejected_before_package_verification(tmp_path):
    archive = tmp_path / LEARNING_ARCHIVE
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b'not the reviewed snapshot')
    evidence = tmp_path / 'revisions/2.1.3/closeout-evidence'
    evidence.mkdir(parents=True)
    (evidence / 'manifest.json').write_text('{"sha256": {}}')
    with pytest.raises(ValueError, match='Published learning archive changed'):
        verify_reviewed(tmp_path)


def test_snapshot_cannot_excuse_a_changed_sdk(tmp_path):
    # Only documentation names are in the pinned archive. A changed SDK source
    # must still fail the original manifest before any publication is possible.
    archive = tmp_path / LEARNING_ARCHIVE
    archive.parent.mkdir(parents=True)
    archive.write_bytes((ROOT / LEARNING_ARCHIVE).read_bytes())
    original = json.loads((ROOT / 'revisions/2.1.3/closeout-evidence/manifest.json').read_text())
    with zipfile.ZipFile(archive) as saved:
        original['sha256'] = {name: original['sha256'][name] for name in saved.namelist()}
    original['sha256']['src/agentic_systems/_grammar.py'] = '0' * 64
    evidence = tmp_path / 'revisions/2.1.3/closeout-evidence'
    evidence.mkdir(parents=True)
    (evidence / 'manifest.json').write_text(json.dumps(original))
    # Archived learning files can move; the unarchived SDK source cannot.
    with pytest.raises(ValueError, match='Reviewed source/evidence changed: src/agentic_systems'):
        verify_reviewed(tmp_path)
