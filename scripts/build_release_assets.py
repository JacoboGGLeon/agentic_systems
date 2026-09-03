"""Build and audit the downloadable assets for an Agentic Systems release."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tarfile
from email.parser import BytesParser

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 only.
    import tomli as tomllib

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = str(
    tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
)
DIST = ROOT / "dist"
CERTIFICATION_SUMMARY = DIST / "release-evidence" / "final-certification-summary.json"
CERTIFICATION_ASSET = DIST / "final-certification-summary.json"
SKILL_SOURCE = (
    ROOT / "examples" / "agentic_systems_studio" / "skills" / "agentic-systems"
)
STUDIO_SOURCE = (
    ROOT
    / "examples"
    / "agentic_systems_studio"
    / "dist"
    / f"agentic-systems-studio-{VERSION}.zip"
)
CHALLENGE_SOURCE = DIST / f"agentic-systems-{VERSION}-strands-protocol-challenge.zip"
FORBIDDEN_PATH_PARTS = ("accountability_otc", "accountability-otc")
SECRET_PREFIXES = (
    re.compile(rb"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"(?<![A-Z0-9])AKIA[0-9A-Z]{16}"),
    re.compile(rb"(?<![A-Z0-9])ASIA[0-9A-Z]{16}"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_skill(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(item for item in SKILL_SOURCE.rglob("*") if item.is_file()):
            relative = path.relative_to(SKILL_SOURCE).as_posix()
            info = zipfile.ZipInfo(
                f"agentic-systems/{relative}", date_time=(2026, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return destination


def _secret_values() -> list[bytes]:
    env_path = ROOT / ".env"
    values: list[bytes] = []
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not any(
            marker in key.upper() for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD")
        ):
            continue
        value = value.strip().strip('"').strip("'")
        if len(value) >= 12:
            values.append(value.encode())
    return values


def _members(path: Path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    yield info.filename, archive.read(info)
        return
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            for info in archive.getmembers():
                if info.isfile():
                    stream = archive.extractfile(info)
                    if stream is not None:
                        yield info.name, stream.read()
        return
    yield path.name, path.read_bytes()


def audit_archive(path: Path, secrets: list[bytes]) -> dict[str, object]:
    forbidden_paths: list[str] = []
    env_files: list[str] = []
    secret_paths: list[str] = []
    members = 0
    for name, payload in _members(path):
        members += 1
        lowered = name.lower()
        if any(part in lowered for part in FORBIDDEN_PATH_PARTS):
            forbidden_paths.append(name)
        if Path(name).name == ".env":
            env_files.append(name)
        if any(pattern.search(payload) for pattern in SECRET_PREFIXES) or any(
            value in payload for value in secrets
        ):
            secret_paths.append(name)
    return {
        "path": path.name,
        "members": members,
        "forbidden_paths": forbidden_paths,
        "embedded_env_files": env_files,
        "secret_paths": secret_paths,
        "sha256": sha256(path),
        "ok": not forbidden_paths and not env_files and not secret_paths,
    }


def validate_certification_identity(
    summary_path: Path,
    *,
    wheel: Path,
    sdist: Path,
) -> dict[str, object]:
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    totals = payload.get("totals", {})
    expected = {
        "schema_version": "agentic_systems.release-certification.v1",
        "package_version": VERSION,
        "wheel_sha256": sha256(wheel),
        "sdist_sha256": sha256(sdist),
        "no_fallback": True,
        "secrets_redacted": True,
        "certified_live_failed": 0,
        "total_semantic_episodes_failed": 0,
    }
    observed = {
        "schema_version": payload.get("schema_version"),
        "package_version": payload.get("package_version"),
        "wheel_sha256": payload.get("wheel_sha256"),
        "sdist_sha256": payload.get("sdist_sha256"),
        "no_fallback": payload.get("no_fallback"),
        "secrets_redacted": payload.get("secrets_redacted"),
        "certified_live_failed": totals.get("certified_live_failed"),
        "total_semantic_episodes_failed": totals.get("total_semantic_episodes_failed"),
    }
    if observed != expected:
        raise ValueError(
            "Certification does not describe the release artifacts: "
            f"observed={observed!r}, expected={expected!r}"
        )
    return payload


def validate_distribution_narrative(
    *,
    wheel: Path,
    sdist: Path,
    readme: Path | None = None,
) -> None:
    canonical = (readme or (ROOT / "README.md")).read_text(encoding="utf-8")
    with zipfile.ZipFile(wheel) as archive:
        metadata_names = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_names) != 1:
            raise ValueError(f"Wheel metadata is ambiguous: {metadata_names!r}")
        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
        wheel_readme = metadata.get_payload()
    with tarfile.open(sdist, "r:gz") as archive:
        readme_members = [
            member
            for member in archive.getmembers()
            if member.isfile() and Path(member.name).name == "README.md"
        ]
        if len(readme_members) != 1:
            raise ValueError(f"Sdist README is ambiguous: {readme_members!r}")
        stream = archive.extractfile(readme_members[0])
        if stream is None:  # pragma: no cover - guarded by member.isfile().
            raise ValueError("Sdist README could not be read")
        sdist_readme = stream.read().decode("utf-8")

    def normalize(value: str) -> str:
        return value.replace("\r\n", "\n").rstrip()

    if normalize(wheel_readme) != normalize(canonical):
        raise ValueError("Wheel long description does not match the canonical README")
    if normalize(sdist_readme) != normalize(canonical):
        raise ValueError("Sdist README does not match the canonical README")


def build_release_assets(*, require_certification: bool = False) -> dict[str, object]:
    DIST.mkdir(parents=True, exist_ok=True)
    if require_certification and not CERTIFICATION_SUMMARY.exists():
        raise FileNotFoundError(
            f"Final release assembly requires {CERTIFICATION_SUMMARY}"
        )
    if not STUDIO_SOURCE.exists():
        raise FileNotFoundError(
            "Build the Studio bundle first with "
            "examples/agentic_systems_studio/scripts/build_bundle.py"
        )

    skill = _zip_skill(DIST / f"agentic-systems-skill-{VERSION}.zip")
    studio = DIST / f"agentic-systems-studio-{VERSION}.zip"
    shutil.copy2(STUDIO_SOURCE, studio)

    artifacts = [
        DIST / f"agentic_systems-{VERSION}-py3-none-any.whl",
        DIST / f"agentic_systems-{VERSION}.tar.gz",
        studio,
        skill,
        CHALLENGE_SOURCE,
    ]
    wheel = DIST / f"agentic_systems-{VERSION}-py3-none-any.whl"
    sdist = DIST / f"agentic_systems-{VERSION}.tar.gz"
    validate_distribution_narrative(wheel=wheel, sdist=sdist)
    if CERTIFICATION_SUMMARY.exists():
        validate_certification_identity(
            CERTIFICATION_SUMMARY,
            wheel=wheel,
            sdist=sdist,
        )
        shutil.copy2(CERTIFICATION_SUMMARY, CERTIFICATION_ASSET)
        artifacts.append(CERTIFICATION_ASSET)
    ada_bundle = DIST / f"agentic-systems-{VERSION}-ada-offline.zip"
    if ada_bundle.exists():
        artifacts.append(ada_bundle)
    missing = [str(path) for path in artifacts if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing release artifacts: {missing}")

    secrets = _secret_values()
    audits = [audit_archive(path, secrets) for path in artifacts]
    if not all(report["ok"] for report in audits):
        raise RuntimeError(f"Release audit failed: {audits}")

    checksum_path = DIST / f"SHA256SUMS-{VERSION}.txt"
    checksum_path.write_text(
        "".join(f"{report['sha256']}  {report['path']}\n" for report in audits),
        encoding="utf-8",
    )
    return {
        "version": VERSION,
        "artifacts": audits,
        "checksums": str(checksum_path.resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-certification",
        action="store_true",
        help="Fail unless the final live-certification summary is present.",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            build_release_assets(
                require_certification=args.require_certification,
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
