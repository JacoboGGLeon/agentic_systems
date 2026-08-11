from __future__ import annotations

import ast
import inspect
import json
import re
from pathlib import Path

import agentic_systems as lab


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_TOOLKIT_METADATA = {"__all__", "__name__", "__version__"}
TOOLKIT_REFERENCE = re.compile(r"\btoolkit\.([A-Za-z_]\w*)")
PYTHON_FENCE = re.compile(r"```(?:python|py)\n(.*?)```", flags=re.DOTALL)


def _markdown_paths() -> list[Path]:
    return [
        ROOT / "README.md",
        ROOT / "INSTALL.md",
        *(ROOT / "docs").rglob("*.md"),
        *(ROOT / "tutorials").rglob("*.md"),
    ]


def _documented_api_index(api_doc: str) -> tuple[str, ...]:
    section = api_doc.split("## Complete Public API Index", 1)[1]
    section = section.split("## Provider Conformance API", 1)[0]
    names: list[str] = []
    for block in re.findall(r"```text\n(.*?)```", section, flags=re.DOTALL):
        names.extend(
            line.strip()
            for line in block.splitlines()
            if re.fullmatch(r"[A-Za-z_]\w*", line.strip())
        )
    return tuple(names)


def _narrative_sources() -> list[tuple[Path, str]]:
    sources = [(path, path.read_text(encoding="utf-8")) for path in _markdown_paths()]
    for path in sorted((ROOT / "tutorials").glob("*.ipynb")):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for cell in notebook["cells"]:
            sources.append((path, "".join(cell.get("source", []))))
    return sources


def _python_examples() -> list[tuple[Path, str, str]]:
    examples: list[tuple[Path, str, str]] = []
    for path in _markdown_paths():
        text = path.read_text(encoding="utf-8")
        for index, source in enumerate(PYTHON_FENCE.findall(text), start=1):
            examples.append((path, f"fence-{index}", source))
    for path in sorted((ROOT / "tutorials").glob("*.ipynb")):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook["cells"]):
            if cell.get("cell_type") == "code":
                examples.append((path, f"cell-{index}", "".join(cell.get("source", []))))
    return examples


def test_api_reference_is_exact_public_api_checksum() -> None:
    api_doc = (ROOT / "docs" / "API.md").read_text(encoding="utf-8")

    assert _documented_api_index(api_doc) == tuple(lab.__all__)
    assert all(hasattr(lab, name) for name in lab.__all__)


def test_documentation_and_tutorials_only_reference_public_toolkit_names() -> None:
    allowed = set(lab.__all__) | PUBLIC_TOOLKIT_METADATA
    invalid: list[str] = []

    for path, text in _narrative_sources():
        for name in TOOLKIT_REFERENCE.findall(text):
            if name not in allowed:
                invalid.append(f"{path.relative_to(ROOT)}: toolkit.{name}")

    assert invalid == []


def test_documented_toolkit_calls_match_source_signatures() -> None:
    invalid: list[str] = []

    for path, label, source in _python_examples():
        tree = ast.parse(source, filename=f"{path.relative_to(ROOT)}:{label}")
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "toolkit"
            ):
                continue
            callable_object = getattr(lab, node.func.attr)
            if not callable(callable_object):
                continue
            signature = inspect.signature(callable_object)
            accepts_kwargs = any(
                parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in signature.parameters.values()
            )
            bad_keywords = sorted(
                keyword.arg
                for keyword in node.keywords
                if keyword.arg
                and keyword.arg not in signature.parameters
                and not accepts_kwargs
            )
            if bad_keywords:
                invalid.append(
                    f"{path.relative_to(ROOT)}:{label}: toolkit.{node.func.attr} "
                    f"does not accept {bad_keywords} under {signature}"
                )

    assert invalid == []
