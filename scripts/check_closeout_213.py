"""Check current evidence hashes and documentation links, without inference."""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'revisions/2.1.3/closeout-evidence'


def main():
    manifest = json.loads((OUTPUT / 'manifest.json').read_text(encoding='utf-8'))
    mismatches = [name for name, value in manifest['sha256'].items()
                  if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value]
    # This checker is added after the first snapshot; its own bytes are captured
    # when the sealer is run again. Other source differences must be explained.
    assert not mismatches, mismatches
    paths = [ROOT / name for name in ('README.md', 'INSTALL.md', 'docs/README.md', 'docs/API_213.md',
        'docs/API_213_SURFACE.md', 'docs/CLI_213.md', 'docs/SCAFFOLDER_213.md', 'docs/USER_EXPERIENCE_213.md',
        'docs/VALIDATION_213.md', 'docs/NOTEBOOK_INVENTORY_213.md', 'docs/RUNRESULTS_LINEAGE_213.md')]
    paths += [OUTPUT / 'REPORT.md', ROOT / 'tutorials/README.md']
    paths += [p for p in (ROOT / 'examples').rglob('README.md')
              if not {'history', 'build', 'dist', 'previous'}.intersection(p.relative_to(ROOT).parts)
              and not any(part.endswith('.egg-info') for part in p.parts)]
    broken = []
    for path in paths:
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if target.startswith(('https:', 'http:', 'mailto:', '#')):
                continue
            local = target.split('#')[0]
            if local and not (path.parent / local).exists():
                broken.append({'source': path.relative_to(ROOT).as_posix(), 'target': target})
    assert not broken, broken
    violations = []
    for folder in ('tutorials', 'examples'):
        for path in (ROOT / folder).rglob('*.py'):
            if {'history', 'build', 'dist', 'tests', 'evidence', '__pycache__'}.intersection(path.relative_to(ROOT).parts):
                continue
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == 'agentic_systems' and alias.asname != 'toolkit':
                            violations.append(path.relative_to(ROOT).as_posix())
                if isinstance(node, ast.ImportFrom) and node.module == 'agentic_systems':
                    violations.append(path.relative_to(ROOT).as_posix())
    assert not violations, violations
    payload = {'status': 'passed', 'manifest_hashes_verified': len(manifest['sha256']),
               'current_documents_checked': len(paths), 'broken_links': [], 'noncanonical_teaching_imports': [],
               'scope': 'Current source and evidence only; historical notebooks are inventoried separately and preserved.'}
    if not (OUTPUT / 'quality-review.json').exists():
        (OUTPUT / 'quality-review.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(payload))


if __name__ == '__main__':
    main()
