"""Published descriptions and notebook views remain usable outside GitHub previews."""
import json
from pathlib import Path
import re
import nbformat

ROOT = Path(__file__).resolve().parents[2]


def test_package_readme_uses_absolute_links():
    readme = (ROOT / 'README.md').read_text()
    for target in re.findall(r'\]\(([^)]+)\)', readme):
        assert target.startswith(('https://', 'http://', '#', 'mailto:')), target


def test_current_notebooks_have_english_reading_views():
    paths = [*(ROOT / 'tutorials').rglob('*.ipynb'), *(p for p in (ROOT / 'examples').rglob('*.ipynb') if 'history' not in p.parts)]
    for path in paths:
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        assert path.with_suffix('.md').is_file(), path
        prose = '\n'.join(c.source for c in notebook.cells)
        prose += '\n' + '\n'.join(o.get('text', '') for c in notebook.cells for o in c.get('outputs', []) if o.get('output_type') == 'stream')
        assert not re.search(r'\b(ejecución|resultados|comisión|contratos|recompensa|aprendizaje|proveedores|capacidad|episodios|linaje)\b', prose, re.I), path
        assert json.loads(path.read_text())['nbformat'] == 4
