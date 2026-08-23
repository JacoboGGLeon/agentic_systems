"""Enforce adapter boundaries and prevent concrete runtime selection leakage."""

from __future__ import annotations

import ast
from pathlib import Path

from agentic_systems.registry import FRAMEWORK_NAMES, PROVIDER_NAMES


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "agentic_systems"
SELECTION_BOUNDARIES = (
    "registry.py",
    "compatibility.py",
    "cli.py",
    "factories.py",
    "system.py",
    "core/runtime.py",
    "engines/",
    "providers/",
    "integrations/langgraph.py",
    "integrations/adapters/",
)


def _relative(path: Path) -> str:
    return path.relative_to(SOURCE).as_posix()


def _selection_allowed(path: Path) -> bool:
    relative = _relative(path)
    return any(
        relative == boundary or relative.startswith(boundary)
        for boundary in SELECTION_BOUNDARIES
    )


def _names(node: ast.AST) -> set[str]:
    return {
        child.id.lower() for child in ast.walk(node) if isinstance(child, ast.Name)
    } | {
        child.attr.lower()
        for child in ast.walk(node)
        if isinstance(child, ast.Attribute)
    }


def _literals(node: ast.AST) -> set[str]:
    return {
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    }


def _selection_violations(path: Path, tree: ast.AST) -> list[str]:
    if _selection_allowed(path):
        return []
    identities = set(PROVIDER_NAMES) | set(FRAMEWORK_NAMES)
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.IfExp, ast.Match)):
            continue
        names = _names(
            node.test if isinstance(node, (ast.If, ast.IfExp)) else node.subject
        )
        if not names.intersection(
            {"provider", "framework", "engine", "runtime_engine"}
        ):
            continue
        if _literals(node).intersection(identities):
            violations.append(
                f"{_relative(path)}:{node.lineno}: concrete selection outside boundary"
            )
    return violations


def _cross_adapter_imports(path: Path, tree: ast.AST) -> list[str]:
    relative = _relative(path)
    if not relative.startswith("integrations/adapters/") or relative.endswith(
        "/__init__.py"
    ):
        return []
    own = path.stem
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            module = node.module.rsplit(".", 1)[-1]
            if "adapters" in node.module and module not in {own, "base", "tools"}:
                violations.append(
                    f"{relative}:{node.lineno}: imports sibling adapter {module}"
                )
    return violations


def main() -> int:
    violations: list[str] = []
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        violations.extend(_selection_violations(path, tree))
        violations.extend(_cross_adapter_imports(path, tree))
    if violations:
        print("Architecture gate failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("Architecture branch gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
