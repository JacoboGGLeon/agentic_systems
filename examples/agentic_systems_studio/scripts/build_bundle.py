"""Build the reproducible conversational Studio bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from agentic_systems import __version__ as AGENTIC_SYSTEMS_VERSION  # noqa: E402
from agentic_systems.registry import (  # noqa: E402
    FRAMEWORK_NAMES,
    PROVIDERS,
    provider_capability,
)


REASONING_PROVIDER_NAMES = tuple(
    definition.name
    for definition in PROVIDERS
    if provider_capability(definition.name, "model_generation").status != "unsupported"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                ".pytest_cache",
                "*.codex-backup",
            ),
        )
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _zip_tree(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return destination


def _checksums(root: Path) -> str:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name == "SHA256SUMS":
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    return "\n".join(rows) + "\n"


def build_bundle(output_dir: str | Path | None = None) -> Path:
    output = Path(output_dir) if output_dir is not None else PROJECT_ROOT / "dist"
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"agentic-systems-studio-{AGENTIC_SYSTEMS_VERSION}.zip"

    with tempfile.TemporaryDirectory(prefix="agentic-systems-studio-") as temporary:
        bundle_root = Path(temporary) / "agentic-systems-studio"
        bundle_root.mkdir()

        for relative in (
            "README.md",
            "pyproject.toml",
            ".env.example",
            "app.py",
            "src",
            "notebooks",
            "docs",
            "scripts/generate_notebooks.py",
            "scripts/validate_conversation_live.py",
        ):
            source = PROJECT_ROOT / relative
            if source.exists():
                _copy(source, bundle_root / relative)

        manifest = {
            "schema_version": "agentic-systems.studio-bundle/v2",
            "product": "Agentic Systems Studio",
            "application": "conversational-studio",
            "agentic_systems_version": AGENTIC_SYSTEMS_VERSION,
            "configuration_source": ".env",
            "entry_points": {
                "notebook": "notebooks/00_conversational_system.ipynb",
                "streamlit": "notebooks/01_launch_studio.ipynb",
            },
            # Studio exposes every canonical runtime. Language-model providers
            # run the conversational system; python-runtime is the explicit,
            # deterministic Hello World control documented by the UI.
            "providers": ["auto", "python-runtime", *REASONING_PROVIDER_NAMES],
            "frameworks": list(FRAMEWORK_NAMES),
            "normalized_result": "RunResult",
            "credentials_included": False,
        }
        (bundle_root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (bundle_root / "SHA256SUMS").write_text(
            _checksums(bundle_root), encoding="utf-8"
        )
        _zip_tree(bundle_root, destination)

    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    path = build_bundle(args.output)
    print(
        json.dumps(
            {
                "bundle": str(path.resolve()),
                "sha256": _sha256(path),
                "application": "conversational-studio",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
