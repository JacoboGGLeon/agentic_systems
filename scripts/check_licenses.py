"""Fail release gates on missing or strong-copyleft direct dependency licenses."""

from __future__ import annotations

import importlib.metadata as metadata
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 release lane.
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_MARKERS = (
    "MIT",
    "Apache-2.0",
    "Apache Software License",
    "BSD",
    "PSF-2.0",
    "ISC",
    "MPL-2.0",
)
DENIED_MARKERS = ("AGPL", "GNU AFFERO", "GNU GENERAL PUBLIC LICENSE")


def _requirements() -> set[str]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    declared = list(project.get("dependencies", ()))
    for dependencies in project.get("optional-dependencies", {}).values():
        declared.extend(dependencies)
    return {Requirement(item).name for item in declared}


def _license_evidence(package: Any) -> str:
    """Return canonical license metadata without scanning bundled notice bodies."""
    expression = package.get("License-Expression")
    classifiers = [
        value
        for value in package.get_all("Classifier") or ()
        if value.startswith("License ::")
    ]
    legacy_lines = [
        line.strip()
        for line in (package.get("License") or "").splitlines()
        if line.strip()
    ]
    legacy_summary = legacy_lines[0] if legacy_lines else None
    return " | ".join(
        value for value in (expression, " ".join(classifiers), legacy_summary) if value
    )


def main() -> int:
    failures: list[str] = []
    checked = 0
    for name in sorted(_requirements(), key=str.lower):
        try:
            package = metadata.metadata(name)
        except metadata.PackageNotFoundError:
            continue
        checked += 1
        license_text = _license_evidence(package)
        upper = license_text.upper()
        denied = any(marker in upper for marker in DENIED_MARKERS)
        allowed = any(marker.upper() in upper for marker in ALLOWED_MARKERS)
        if denied or not allowed:
            failures.append(
                f"{name}: {license_text[:160] or 'missing license metadata'}"
            )
    if failures:
        print("License gate failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"License gate passed for {checked} installed direct dependencies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
