"""Inspect/install/export the authoring skill; this example does not generate apps."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import zipfile
import agentic_systems as toolkit
from agentic_systems.cli import main


def run():
    with tempfile.TemporaryDirectory(prefix='agentic-skill-example-') as directory:
        destination = Path(directory) / 'authoring-skill'
        archive = Path(directory) / 'skill.zip'
        captured = StringIO()
        with redirect_stdout(captured):
            main(['skill', 'info'])
        info = json.loads(captured.getvalue())
        with redirect_stdout(StringIO()):
            main(['skill', 'install', str(destination)])
            main(['skill', 'export', str(archive)])
        assert (destination / 'SKILL.md').is_file()
        assert info['sdk_version'] == toolkit.__version__
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.testzip() is None
            assert len(bundle.namelist()) == len(info['files'])
        return {'input': 'bundled authoring skill', 'process': ['info', 'install', 'export'],
                'output': {'sdk_version': toolkit.__version__, 'files': len(info['files']),
                           'installed': True, 'exported': True}}
