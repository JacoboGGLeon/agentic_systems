"""Build the canonical root SDK in a new staging directory, offline and unpublished."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("Choose a new candidate directory")
    source = destination / "source"
    source.mkdir(parents=True)
    shutil.copytree(ROOT / "src/agentic_systems", source / "src/agentic_systems",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        if (ROOT / name).exists():
            shutil.copyfile(ROOT / name, source / name)
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--no-index",
                    "--wheel-dir", str(destination / "dist"), str(source)], check=True)
    subprocess.run([sys.executable, "-c", "import setuptools.build_meta as backend; backend.build_sdist(" + repr(str(destination / "dist")) + ")"],
                   cwd=source, check=True, stdout=subprocess.DEVNULL)
    wheel = next((destination / "dist").glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        public = {n for n in names if n.startswith("agentic_systems/") and n.count("/") == 1}
        assert public == {"agentic_systems/" + n for n in ("__init__.py", "cli.py", "_grammar.py", "_tools.py", "_results.py", "_contracts.py", "_configuration.py", "_scaffolding.py")}, public
        assert not any("/compat/" in n for n in names)
    manifest = {"version": "2.1.3", "status": "candidate-not-published", "wheel": str(wheel),
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "inference_requests": 0,
        "source_sha256": {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(source.rglob("*")) if p.is_file() and "egg-info" not in str(p) and "build" not in p.relative_to(source).parts}}
    manifest['sdist_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (destination / 'dist').glob('*.tar.gz')}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return wheel


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    print(build(parser.parse_args().destination))
