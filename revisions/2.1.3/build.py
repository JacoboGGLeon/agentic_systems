"""Build the real 2.1.3 SDK wheel with one public API, without changing 2.1.2 artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HOME = Path(__file__).resolve().parent
ROOT = HOME.parents[1]


def build(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("Build into a new directory")
    destination.mkdir(parents=True)
    project = destination / "source"
    project.mkdir()
    shutil.copytree(ROOT / "src/agentic_systems", project / "src/agentic_systems",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "compat"))
    for source in (HOME / "package").glob("*.py"):
        shutil.copyfile(source, project / "src/agentic_systems" / source.name)
    (project / "src/agentic_systems/core/__init__.py").write_text(
        '"""Private runtime implementation; the public API is agentic_systems."""\n__all__ = []\n', encoding="utf-8"
    )
    package = project / "src/agentic_systems"
    for before, after in {"agents.py": "_actors.py", "system.py": "_workspace.py", "factories.py": "_factories.py"}.items():
        (package / before).rename(package / after)
    # Retired public forwarding modules are not distributed in 2.1.3.
    (package / "core/agents.py").unlink()
    (package / "api_contract.py").unlink()
    for path in package.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for old, new in {"agents": "_actors", "system": "_workspace", "factories": "_factories"}.items():
            text = text.replace(f"from .{old} import", f"from .{new} import")
            text = text.replace(f"from agentic_systems.{old} import", f"from agentic_systems.{new} import")
        path.write_text(text, encoding="utf-8")
    templates = package / "templates"
    shutil.copytree(ROOT / "examples/order_fulfillment", templates / "order_fulfillment",
                    ignore=shutil.ignore_patterns("__pycache__", "evidence", "*.pyc"))
    shutil.copytree(HOME / "project_template", templates / "project")
    config = (ROOT / "pyproject.toml").read_text(encoding="utf-8").replace('version = "2.1.2"', 'version = "2.1.3"', 1)
    config += '\n[tool.setuptools.package-data]\nagentic_systems = ["templates/**/*", "templates/project/.env.example", "templates/project/.gitignore"]\n'
    (project / "pyproject.toml").write_text(config, encoding="utf-8")
    shutil.copyfile(HOME / "README.md", project / "README.md")
    artifacts = destination / "dist"
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
                    "--no-index", "--wheel-dir", str(artifacts), str(project)], check=True)
    wheel = next(artifacts.glob("agentic_systems-2.1.3-*.whl"))
    (destination / "manifest.json").write_text(json.dumps({
        "version": "2.1.3", "status": "single-api-candidate-not-published",
        "wheel": str(wheel), "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "inference_requests": 0,
        "source_sha256": {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted((project / "src").rglob("*.py"))},
    }, indent=2) + "\n", encoding="utf-8")
    return wheel


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    print(build(parser.parse_args().destination))
