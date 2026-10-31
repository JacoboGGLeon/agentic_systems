"""Generate with the installed 2.1.4 CLI and record skill provenance."""

import argparse
import hashlib
import json
from pathlib import Path
import agentic_systems as toolkit
from agentic_systems.cli import main


def scaffold(destination):
    assert toolkit.__version__ == "2.1.4", "Install agentic-systems==2.1.4 first"
    path = Path(destination).resolve()
    if path.exists():
        raise FileExistsError(path)
    main(["new", str(path)])
    # The CLI already owns the example, business tests and pytest configuration.
    # Keep a single scaffold instead of appending a second pytest TOML table.
    manifest = path / "manifest.json"
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    metadata["skill_version"] = "2.1.4"
    manifest.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    files = sorted(
        p for p in path.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"
    )
    (path / "SHA256SUMS.txt").write_text(
        "".join(
            hashlib.sha256(p.read_bytes()).hexdigest()
            + "  "
            + p.relative_to(path).as_posix()
            + "\n"
            for p in files
        ),
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    print(scaffold(parser.parse_args().destination))
