"""Check current learning navigation and target-version metadata, preserving history."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    catalog = json.loads((root / 'examples/catalog.json').read_text(encoding='utf-8'))
    assert catalog['current_api_version'] == '2.1.5'
    pages = [root / p for p in ('README.md', 'INSTALL.md', 'docs/README.md',
             'docs/API.md', 'docs/API_214.md', 'docs/API_214_SURFACE.md',
             'docs/CLI.md', 'docs/ACTOR_CONTRACTS.md', 'docs/EXAMPLES_GUIDE.md',
             'docs/ONBOARDING_FIRST_RUN.md', 'examples/README.md', 'tutorials/README.md')]
    for entry in catalog['entries']:
        assert entry['target_sdk_version'] == '2.1.5', entry['id']
        path = entry.get('entrypoint')
        if path and (root / path).is_file():
            pages.append((root / path).parent / 'README.md')
    for page in pages:
        assert page.is_file(), page
        for target in re.findall(r'\]\(([^)]+)\)', page.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            assert (page.parent / target.split('#')[0]).exists(), (page, target)
    notebooks = sorted((root / 'tutorials').rglob('*.ipynb')) + sorted(
        p for p in (root / 'examples').rglob('*.ipynb') if 'history' not in p.parts)
    for path in notebooks:
        metadata = json.loads(path.read_text(encoding='utf-8'))['metadata']['agentic_systems']
        assert metadata['target_sdk_version'] == '2.1.5', path
    return {'pages_checked': len(pages), 'notebooks_checked': len(notebooks),
            'inference_executed': False}


if __name__ == '__main__':
    print(json.dumps(check()))
