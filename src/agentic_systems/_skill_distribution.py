"""Offline installation/export of the SDK's authoring skill, not runtime Skills."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
from importlib import resources
from pathlib import Path
import shutil
import tempfile
import zipfile


@contextmanager
def skill_source():
    bundled = resources.files('agentic_systems').joinpath('_bundled_skills', 'agentic-systems')
    if bundled.joinpath('SKILL.md').is_file():
        yield bundled
        return
    # Editable installations retain the canonical source outside the package.
    checkout = Path(__file__).resolve().parents[2]
    source = checkout / 'skills' / 'agentic-systems'
    if (checkout / 'pyproject.toml').is_file() and (source / 'SKILL.md').is_file():
        yield source
        return
    raise FileNotFoundError('This installation has no bundled authoring skill; install a release that includes it')


def _files(root, prefix=''):
    for item in sorted(root.iterdir(), key=lambda entry: entry.name):
        if item.name == '__pycache__' or item.name.endswith(('.pyc', '.pyo')):
            continue
        if isinstance(item, Path) and item.is_symlink():
            raise ValueError('Skill resources must not contain symbolic links')
        relative = prefix + item.name
        if item.is_dir():
            yield from _files(item, relative + '/')
        elif item.is_file():
            yield relative, item.read_bytes()


def skill_info():
    from . import __version__
    with skill_source() as source:
        files = {name: hashlib.sha256(data).hexdigest() for name, data in _files(source)}
    return {'name': 'agentic-systems', 'sdk_version': __version__, 'files': files,
            'scope': 'authoring-skill', 'network_required': False}


def _destination(value):
    # Do not resolve the final component: broken symlinks count as existing paths.
    path = Path(value).expanduser().absolute()
    if path.exists() or path.is_symlink():
        raise FileExistsError(f'Refusing to overwrite existing destination: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def install_skill(destination='.agents/skills/agentic-systems'):
    path = _destination(destination)
    # Build the complete tree before exposing it as an installed skill.
    with tempfile.TemporaryDirectory(prefix='.agentic-skill-', dir=path.parent) as temporary:
        staged = Path(temporary) / 'agentic-systems'
        staged.mkdir()
        with skill_source() as source:
            for relative, data in _files(source):
                output = staged / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(data)
        # mkdir reserves the final destination exclusively, including against races.
        path.mkdir()
        try:
            for item in staged.iterdir():
                shutil.move(str(item), str(path / item.name))
        except BaseException:
            shutil.rmtree(path)
            raise
    return path


def export_skill(destination):
    path = _destination(destination)
    if path.suffix.lower() != '.zip':
        raise ValueError('Skill export destination must end in .zip')
    # Exclusive creation preserves existing files, including concurrent writers.
    with skill_source() as source:
        entries = list(_files(source))
    with path.open('xb') as stream:
        try:
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
                for relative, data in entries:
                    entry = zipfile.ZipInfo('agentic-systems/' + relative, (2026, 1, 1, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    entry.external_attr = 0o644 << 16
                    archive.writestr(entry, data)
        except BaseException:
            # Close before unlinking for Windows compatibility.
            stream.close()
            path.unlink()
            raise
    return path
