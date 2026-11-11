"""Authoring-skill installation preserves user files and works without services."""
import json
from pathlib import Path
import zipfile

import pytest

import agentic_systems as toolkit
from agentic_systems import _skill_distribution as distribution
from agentic_systems.cli import main


def test_install_contains_complete_executable_skill_and_matches_identity(tmp_path):
    destination = tmp_path / 'project with spaces' / 'agentic-systems'
    assert distribution.install_skill(destination) == destination
    info = distribution.skill_info()
    assert info['sdk_version'] == toolkit.__version__
    assert info['network_required'] is False
    assert {'SKILL.md', 'assets/first_tool.py', 'agents/openai.yaml'} <= info['files'].keys()
    import hashlib
    actual = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in destination.rglob('*') if p.is_file()}
    assert actual == info['files']
    assert '2.1.5' not in (destination / 'assets/first_tool.py').read_text()


def test_cli_default_install_and_info(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(['skill', 'install']) == 0
    destination = tmp_path / '.agents/skills/agentic-systems'
    assert Path(capsys.readouterr().out.strip()) == destination
    assert (destination / 'SKILL.md').is_file()
    assert main(['skill', 'info']) == 0
    assert json.loads(capsys.readouterr().out)['scope'] == 'authoring-skill'


@pytest.mark.parametrize('kind', ['directory', 'file', 'broken_symlink'])
def test_existing_paths_are_never_overwritten(tmp_path, kind, capsys):
    path = tmp_path / 'user work'
    if kind == 'directory':
        path.mkdir()
        (path / 'keep').write_text('original')
    elif kind == 'file':
        path.write_text('original')
    else:
        path.symlink_to(tmp_path / 'absent')
    for operation in ('install', 'export'):
        with pytest.raises(SystemExit) as caught:
            main(['skill', operation, str(path)])
        assert caught.value.code == 2
        assert 'Refusing to overwrite' in capsys.readouterr().err
    if kind == 'directory':
        assert (path / 'keep').read_text() == 'original'
    elif kind == 'file':
        assert path.read_text() == 'original'
    else:
        assert path.is_symlink()


def test_export_is_reproducible_complete_and_importable(tmp_path, capsys):
    first, second = tmp_path / 'first.zip', tmp_path / 'second.ZIP'
    assert main(['skill', 'export', str(first)]) == 0
    assert str(first) in capsys.readouterr().out
    assert distribution.export_skill(second) == second
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert archive.testzip() is None
        assert 'agentic-systems/SKILL.md' in archive.namelist()
        assert all(n.startswith('agentic-systems/') and '..' not in n.split('/') for n in archive.namelist())
        assert len(archive.namelist()) == len(distribution.skill_info()['files'])


def test_invalid_export_extension_is_actionable(tmp_path, capsys):
    target = tmp_path / 'skill.txt'
    with pytest.raises(SystemExit) as caught:
        main(['skill', 'export', str(target)])
    assert caught.value.code == 2 and '.zip' in capsys.readouterr().err
    assert not target.exists()


def test_install_failure_rolls_back_only_new_destination(tmp_path, monkeypatch):
    parent = tmp_path / 'existing'
    parent.mkdir()
    sentinel = parent / 'keep.txt'
    sentinel.write_text('original')
    def fail_move(*args):
        raise OSError('disk full')
    monkeypatch.setattr(distribution.shutil, 'move', fail_move)
    with pytest.raises(OSError, match='disk full'):
        distribution.install_skill(parent / 'new-skill')
    assert not (parent / 'new-skill').exists()
    assert sentinel.read_text() == 'original'
    assert sorted(p.name for p in parent.iterdir()) == ['keep.txt']


def test_export_failure_removes_incomplete_archive(tmp_path, monkeypatch):
    def fail_write(*args):
        raise OSError('disk full')
    monkeypatch.setattr(distribution.zipfile.ZipFile, 'writestr', fail_write)
    destination = tmp_path / 'new.zip'
    with pytest.raises(OSError, match='disk full'):
        distribution.export_skill(destination)
    assert not destination.exists()


def test_symlinked_resources_are_rejected(tmp_path):
    (tmp_path / 'link').symlink_to(tmp_path / 'absent')
    with pytest.raises(ValueError, match='symbolic links'):
        list(distribution._files(tmp_path))


def test_bytecode_is_not_distributed(tmp_path):
    (tmp_path / '__pycache__').mkdir()
    (tmp_path / '__pycache__/bad.pyc').write_bytes(b'bad')
    (tmp_path / 'bad.pyc').write_bytes(b'bad')
    (tmp_path / 'SKILL.md').write_text('skill')
    assert list(distribution._files(tmp_path)) == [('SKILL.md', b'skill')]


def test_missing_bundle_has_actionable_cli_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(distribution.resources, 'files', lambda name: tmp_path)
    # Disable the source-checkout fallback in this deliberately incomplete install.
    monkeypatch.setattr(distribution, '__file__', str(tmp_path / 'src/pkg/module.py'))
    with pytest.raises(SystemExit) as caught:
        main(['skill', 'info'])
    assert caught.value.code == 2
    assert 'no bundled authoring skill' in capsys.readouterr().err


def test_bundled_skill_takes_precedence_over_checkout(monkeypatch, tmp_path):
    source = tmp_path / '_bundled_skills/agentic-systems'
    source.mkdir(parents=True)
    (source / 'SKILL.md').write_text('packaged copy')
    monkeypatch.setattr(distribution.resources, 'files', lambda name: tmp_path)
    with distribution.skill_source() as selected:
        assert selected == source
    assert set(distribution.skill_info()['files']) == {'SKILL.md'}


def test_skill_target_and_guards_match_installed_sdk():
    # Prevent a future release from silently shipping the stale exact-version guards
    # that blocked the original 2.1.5 skill when used with SDK 2.1.6.
    with distribution.skill_source() as source:
        for name in ('SKILL.md', 'assets/first_tool.py',
                     'agents/openai.yaml', 'references/project-contract.md'):
            assert toolkit.__version__ in source.joinpath(*name.split('/')).read_text(encoding='utf-8'), name


def test_editable_checkout_fallback_works_without_bundled_resources(monkeypatch, tmp_path):
    source = tmp_path / 'skills/agentic-systems'
    source.mkdir(parents=True)
    (tmp_path / 'pyproject.toml').write_text('[project]')
    (source / 'SKILL.md').write_text('editable skill')
    monkeypatch.setattr(distribution.resources, 'files', lambda name: tmp_path / 'absent')
    monkeypatch.setattr(distribution, '__file__', str(tmp_path / 'src/agentic_systems/module.py'))
    with distribution.skill_source() as selected:
        assert selected == source
    assert set(distribution.skill_info()['files']) == {'SKILL.md'}
