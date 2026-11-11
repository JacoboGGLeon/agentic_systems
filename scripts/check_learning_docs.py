"""Check current learning navigation and target-version metadata, preserving history."""
import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def project_version(root):
    module = ast.parse((root / "src/agentic_systems/__init__.py").read_text())
    return next(ast.literal_eval(node.value) for node in module.body
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets))


def check(root=ROOT):
    version = project_version(root)
    catalog = json.loads((root / 'examples/catalog.json').read_text(encoding='utf-8'))
    assert catalog['current_api_version'] == version
    pages = [root / p for p in ('README.md', 'INSTALL.md', 'docs/README.md',
             'docs/API.md', 'docs/API_214.md', 'docs/API_214_SURFACE.md',
             'docs/CLI.md', 'docs/ACTOR_CONTRACTS.md', 'docs/EXAMPLES_GUIDE.md',
             'docs/ONBOARDING_FIRST_RUN.md', 'examples/README.md', 'tutorials/README.md',
             'docs/CONCEPTS.md', 'docs/GRAPHS.md', 'docs/EXECUTION.md',
             'docs/RESULTS.md', 'docs/EVALUATION.md', 'docs/CONTEXT_MEMORY.md',
             'docs/INTEGRATIONS.md', 'docs/MIGRATION_217_TO_218.md',
             'docs/STATUS_214.md', 'docs/RUNRESULT_CONTRACT.md')]
    for entry in catalog['entries']:
        assert entry['target_sdk_version'] == version, entry['id']
        path = entry.get('entrypoint')
        if path and (root / path).is_file():
            pages.append((root / path).parent / 'README.md')
    for page in pages:
        assert page.is_file(), page
        text = page.read_text(encoding='utf-8')
        heading = next((line for line in text.splitlines() if line.startswith('# ')), '')
        if page.name != 'MIGRATION_217_TO_218.md':
            versions = re.findall(r'2\.1\.\d+(?:\.dev\d+)?', heading)
            assert all(item == version for item in versions), (page, heading, version)
        assert not re.search(r'The current SDK(?: release)? is 2\.1\.(?!' + re.escape(version.split('.')[-1]) + r'\b)\d+', text), page
        assert 'Generate a complete offline project' not in text, page
        for target in re.findall(r'\]\(([^)]+)\)', page.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            assert (page.parent / target.split('#')[0]).exists(), (page, target)
    notebooks = sorted((root / 'tutorials').rglob('*.ipynb')) + sorted(
        p for p in (root / 'examples').rglob('*.ipynb') if 'history' not in p.parts)
    for path in notebooks:
        metadata = json.loads(path.read_text(encoding='utf-8'))['metadata']['agentic_systems']
        assert metadata['target_sdk_version'] == version, path
        notebook = json.loads(path.read_text(encoding='utf-8'))
        for cell in notebook['cells']:
            if cell['cell_type'] != 'code':
                continue
            source = ''.join(cell['source'])
            pins = re.findall(r"__version__\s*==\s*['\"]([^'\"]+)['\"]", source)
            assert all(pin == version for pin in pins), (path, pins, version)
    return {'pages_checked': len(pages), 'notebooks_checked': len(notebooks),
            'inference_executed': False}


if __name__ == '__main__':
    print(json.dumps(check()))
