"""Check installed CLI/skill outside checkout without inference."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
import agentic_systems as toolkit


def main():
    if 'site-packages' not in Path(toolkit.__file__).parts:
        raise ValueError('Install the candidate wheel first')
    evidence = Path(os.environ['AGENTIC_VALIDATION_EVIDENCE']).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory(prefix='agentic-skill-') as directory:
        root = Path(directory)
        env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
        def run(arguments, expected=0):
            result = subprocess.run([sys.executable, *arguments], cwd=root, env=env,
                                    capture_output=True, text=True, timeout=90)
            rows.append({'arguments': arguments, 'returncode': result.returncode,
                         'stdout': result.stdout, 'stderr': result.stderr})
            (evidence / 'skill-distribution.json').write_text(json.dumps(rows, indent=2))
            assert result.returncode == expected, rows[-1]
            return result.stdout
        prefix = ['-m', 'agentic_systems.cli']
        assert run(prefix + ['version']).strip() == toolkit.__version__
        info = json.loads(run(prefix + ['skill', 'info']))
        assert info['sdk_version'] == toolkit.__version__
        assert 'scripts/scaffold.py' not in info['files']
        run(prefix + ['skill', 'install'])
        run(prefix + ['skill', 'install'], 2)
        run(prefix + ['skill', 'export', 'skill.zip'])
        run(prefix + ['skill', 'export', 'skill.zip'], 2)
        run(prefix + ['new', 'must-not-exist'], 2)
        assert not (root / 'must-not-exist').exists()
        with zipfile.ZipFile(root / 'skill.zip') as archive:
            assert archive.testzip() is None
            assert len(archive.namelist()) == len(info['files'])
        skill = root / '.agents/skills/agentic-systems'
        run([str(skill / 'assets/first_tool.py')])
        run([str(skill / 'assets/minimal.py')])
    print(json.dumps({'version': toolkit.__version__, 'commands_checked': len(rows),
                      'inference_requests': 0, 'status': 'PASS'}))


if __name__ == '__main__':
    main()
