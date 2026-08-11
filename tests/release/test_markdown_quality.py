from __future__ import annotations

import ast
import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_ROOTS = (
    ROOT / "README.md",
    ROOT / "INSTALL.md",
    ROOT / "CHANGELOG.md",
    ROOT / "ROADMAP.md",
    ROOT / "tests" / "README.md",
)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^\s*```([^`]*)$", re.MULTILINE)


def _markdown_files() -> list[Path]:
    files = [path for path in MARKDOWN_ROOTS if path.exists()]
    files.extend((ROOT / "docs").rglob("*.md"))
    files.extend((ROOT / "tutorials").rglob("*.md"))
    return sorted(set(files))


def _local_link_target(source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
    if not target or target.startswith(("#", "http://", "https://", "mailto:")):
        return None
    relative = unquote(target.split("#", 1)[0])
    return (source.parent / relative).resolve()


def test_repository_markdown_is_release_quality() -> None:
    errors: list[str] = []

    for path in _markdown_files():
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)

        if len(FENCE_RE.findall(text)) % 2:
            errors.append(f"{relative}: unbalanced fenced code block")

        in_python = False
        python_start = 0
        python_lines: list[str] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.strip().startswith("```"):
                if not in_python and line.strip().lower() in {"```python", "```py"}:
                    in_python = True
                    python_start = line_number + 1
                    python_lines = []
                elif in_python:
                    try:
                        ast.parse("\n".join(python_lines), filename=str(relative))
                    except SyntaxError as exc:
                        errors.append(
                            f"{relative}:{python_start + (exc.lineno or 1) - 1}: "
                            f"invalid Python example: {exc.msg}"
                        )
                    in_python = False
                continue
            if in_python:
                python_lines.append(line)

        for match in LINK_RE.finditer(text):
            target = _local_link_target(path, match.group(1))
            if target is not None and not target.exists():
                errors.append(f"{relative}: broken local link {match.group(1)!r}")

    assert not (ROOT / "COMMIT_MESSAGE.md").exists()
    assert not (ROOT / "AGENTIC_SYSTEMS_PROGRESS.md").exists()
    assert "alias `vll`" not in (ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    assert errors == [], "\n".join(errors)
