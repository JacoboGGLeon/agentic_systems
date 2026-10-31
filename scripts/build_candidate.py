"""Build current source bytes in a fresh directory, without publishing."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def build(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("Choose a new candidate directory")
    stage = destination / "source"
    stage.mkdir(parents=True)
    shutil.copytree(ROOT / "src", stage / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
    for name in ("pyproject.toml", "README.md", "CHANGELOG.md", "LICENSE", "MANIFEST.in"):
        shutil.copyfile(ROOT / name, stage / name)
    version = tomllib.loads((stage / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    dist = destination / "dist"
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--no-index",
                    "--wheel-dir", str(dist), str(stage)], check=True)
    subprocess.run([sys.executable, "-c", "import setuptools.build_meta as b; b.build_sdist(" + repr(str(dist)) + ")"],
                   cwd=stage, check=True, stdout=subprocess.DEVNULL)
    wheel = dist / f"agentic_systems-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert not any("__pycache__" in name or name.endswith((".pyc", "/.env")) for name in names)
        for name in names:
            if name.startswith("agentic_systems/") and not name.endswith("/"):
                assert archive.read(name) == (stage / "src" / name).read_bytes(), name
    manifest = {
        "version": version, "status": "offline-candidate-not-published", "inference_requests": 0,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "artifacts": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(dist.iterdir())},
        "source_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in [ROOT / "pyproject.toml", ROOT / "README.md", ROOT / "CHANGELOG.md", *sorted((ROOT / "src").rglob("*.py"))]},
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return wheel


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    print(build(parser.parse_args().destination))
