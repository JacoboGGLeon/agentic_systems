"""Build Studio from clean staging, checking source/wheel payload equality."""
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
    source = ROOT / "examples/agentic_systems_studio"
    stage = destination / "source"
    shutil.copytree(source, stage, ignore=shutil.ignore_patterns(
        "build", "dist", "*.egg-info", "__pycache__", ".pytest_cache", "evidence", "tests"))
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
                    "--no-index", "--wheel-dir", str(destination / "dist"), str(stage)], check=True)
    wheels = list((destination / "dist").glob("*.whl"))
    assert len(wheels) == 1
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        names = [name for name in archive.namelist() if name.startswith("agentic_systems_studio/") and not name.endswith("/")]
        for name in names:
            assert archive.read(name) == (source / "src" / name).read_bytes(), name
    manifest = {"wheel": wheel.name, "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                "source_payload_files_checked": len(names), "published": False}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return wheel


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    print(build(parser.parse_args().destination))
