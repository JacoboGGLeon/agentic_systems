"""Use the toolkit alias in current teaching source; preserve historical bytes."""
from pathlib import Path
import ast
import re
import nbformat

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'history', 'evidence', 'dist', 'build', '__pycache__', '.ipynb_checkpoints', 'tests'}


def normalize(source):
    source = re.sub(r'\bimport agentic_systems as ag\b', 'import agentic_systems as toolkit', source)
    return re.sub(r'(?<![\w])ag\.', 'toolkit.', source)


def qualify_imports(source):
    tree = ast.parse(source)
    imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == 'agentic_systems']
    if not imports:
        return source
    names = {alias.asname or alias.name: alias.name for node in imports for alias in node.names}
    if any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id in names for node in ast.walk(tree)):
        raise ValueError('Imported SDK name is rebound; review this source manually')
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    def position(line, column):
        # AST columns are UTF-8 bytes, not Unicode characters.
        prefix = lines[line - 1].encode('utf-8')[:column].decode('utf-8')
        return offsets[line - 1] + len(prefix)
    edits = [(position(n.lineno, n.col_offset), position(n.end_lineno, n.end_col_offset),
              'import agentic_systems as toolkit') for n in imports]
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in names:
            edits.append((position(node.lineno, node.col_offset), position(node.end_lineno, node.end_col_offset),
                          'toolkit.' + names[node.id]))
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    source = source.replace('import agentic_systems as toolkit\nimport agentic_systems as toolkit\n', 'import agentic_systems as toolkit\n')
    ast.parse(source)
    return source


def main():
    changed = []
    for directory in ('tutorials', 'examples', 'src/agentic_systems/_templates'):
        for path in sorted((ROOT / directory).rglob('*')):
            if not path.is_file() or EXCLUDED.intersection(path.relative_to(ROOT).parts):
                continue
            if path.suffix in {'.py', '.md'}:
                before = path.read_text(encoding='utf-8')
                after = normalize(before)
                if path.suffix == '.py':
                    after = qualify_imports(after)
                if after != before:
                    path.write_text(after, encoding='utf-8')
                    changed.append(path.relative_to(ROOT).as_posix())
            elif path.suffix == '.ipynb':
                notebook = nbformat.read(path, as_version=4)
                altered = False
                for cell in notebook.cells:
                    after = normalize(cell.source)
                    if after != cell.source:
                        cell.source, altered = after, True
                if altered:
                    nbformat.write(notebook, path)
                    changed.append(path.relative_to(ROOT).as_posix())
    for name in ('scripts/write_tutorials_213.py', 'scripts/migrate_examples_213.py', 'README.md', 'docs/API_213.md'):
        path = ROOT / name
        before = path.read_text(encoding='utf-8')
        after = normalize(before)
        if before != after:
            path.write_text(after, encoding='utf-8')
            changed.append(name)
    print(f'Normalized {len(changed)} current teaching files. Historical evidence untouched.')


if __name__ == '__main__':
    main()
