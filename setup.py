"""Copy the canonical authoring skill into wheel package resources."""
from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPyWithSkill(build_py):
    def run(self):
        super().run()
        source = Path(__file__).resolve().parent / 'skills' / 'agentic-systems'
        if not (source / 'SKILL.md').is_file():
            raise FileNotFoundError('Canonical agentic-systems skill is missing')
        destination = Path(self.build_lib) / 'agentic_systems' / '_bundled_skills' / 'agentic-systems'
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))


setup(cmdclass={'build_py': BuildPyWithSkill})
