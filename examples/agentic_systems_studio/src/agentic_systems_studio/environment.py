"""Canonical ``.env`` discovery and loading for Agentic Systems Studio."""

from __future__ import annotations

import os
from pathlib import Path
import re


ENV_FILE_VARIABLE = "AGENTIC_SYSTEMS_ENV_FILE"
_ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ancestors(start: Path) -> tuple[Path, ...]:
    current = start.expanduser().resolve()
    if current.is_file():
        current = current.parent
    return (current, *current.parents)


def find_studio_environment(path: str | Path | None = None) -> Path:
    """Locate the one Studio ``.env`` contract without relying only on cwd."""

    if path is not None:
        explicit = Path(path).expanduser().resolve()
        if not explicit.is_file():
            raise FileNotFoundError(
                f"Studio environment file does not exist: {explicit}"
            )
        return explicit

    configured = os.getenv(ENV_FILE_VARIABLE)
    if configured:
        explicit = Path(configured).expanduser().resolve()
        if not explicit.is_file():
            raise FileNotFoundError(
                f"{ENV_FILE_VARIABLE} points to a missing file: {explicit}"
            )
        return explicit

    roots = (*_ancestors(Path.cwd()), *_ancestors(Path(__file__)))
    checked: list[Path] = []
    for root in roots:
        candidate = root / ".env"
        if candidate in checked:
            continue
        checked.append(candidate)
        if candidate.is_file():
            return candidate

    rendered = os.linesep.join(f"- {candidate}" for candidate in checked)
    raise FileNotFoundError(
        "Could not locate the canonical Studio .env. "
        f"Set {ENV_FILE_VARIABLE} to an explicit file or create .env at the "
        "bundle/application root. Checked:" + os.linesep + rendered
    )


def load_studio_environment(
    path: str | Path | None = None,
    *,
    override: bool = True,
) -> Path:
    """Load the canonical Studio contract and return its resolved path.

    Values declared in ``.env`` win by default. Variables absent from the file
    remain untouched, so managed AWS credential-chain variables continue to be
    inherited from SageMaker/ADA.
    """

    environment = find_studio_environment(path)
    for line_number, raw_line in enumerate(
        environment.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(
                f"Invalid .env entry at {environment}:{line_number}: expected KEY=VALUE"
            )
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not _ENV_KEY.fullmatch(key):
            raise ValueError(
                f"Invalid .env key at {environment}:{line_number}: {key!r}"
            )
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value
    os.environ[ENV_FILE_VARIABLE] = str(environment)
    return environment


__all__ = [
    "ENV_FILE_VARIABLE",
    "find_studio_environment",
    "load_studio_environment",
]
