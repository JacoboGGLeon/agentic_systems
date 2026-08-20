"""Build a reproducible Studio bundle containing ten nested system bundles."""

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
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from agentic_systems_studio.catalog import SYSTEM_SPECS  # noqa: E402
from agentic_systems_studio.scaffolder import scaffold_application  # noqa: E402
from agentic_systems_studio.store import StudioStore  # noqa: E402


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
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
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
    destination = output / "agentic-systems-studio-2.0.zip"

    with tempfile.TemporaryDirectory(prefix="agentic-systems-studio-") as temporary:
        temporary_root = Path(temporary)
        bundle_root = temporary_root / "agentic-systems-studio"
        bundle_root.mkdir()

        for relative in (
            "README.md",
            "pyproject.toml",
            ".env.example",
            "app.py",
            "src",
            "skills",
            "notebooks",
            "docs",
            "scripts",
            "evidence",
        ):
            source = PROJECT_ROOT / relative
            if source.exists():
                _copy(source, bundle_root / relative)

        database = StudioStore(bundle_root / "data" / "studio.db")
        database.initialize()

        nested_dir = bundle_root / "system-bundles"
        nested_dir.mkdir()
        nested_manifest = []
        for spec in SYSTEM_SPECS:
            application = temporary_root / "nested" / spec.id
            scaffold_application(
                application,
                name=spec.id,
                system_id=spec.id,
            )
            nested_zip = _zip_tree(application, nested_dir / f"{spec.id}.zip")
            nested_manifest.append(
                {
                    "id": spec.id,
                    "name": spec.name,
                    "size": spec.size,
                    "agents": len(spec.stages),
                    "path": f"system-bundles/{nested_zip.name}",
                    "sha256": _sha256(nested_zip),
                }
            )

        manifest = {
            "schema_version": "agentic-systems.studio-bundle/v1",
            "product": "Agentic Systems Studio",
            "agentic_systems_version": "2.0.0",
            "systems": nested_manifest,
            "composition_plans": ["sequential", "parallel"],
            "normalized_result": "RunResult",
            "credentials_included": False,
        }
        (bundle_root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
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
                "systems": len(SYSTEM_SPECS),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
