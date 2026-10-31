"""Verify installed/source SDK bytes, RECORD hashes and wheel hygiene."""

import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

import agentic_systems as toolkit


def verify(wheel):
    root = Path(__file__).resolve().parents[1]
    installed = Path(toolkit.__file__).parent.parent
    if "site-packages" not in installed.parts:
        raise ValueError("Verification requires a non-editable installed wheel")
    checked = 0
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        for name in names:
            if name.endswith("/"):
                continue
            if "__pycache__" in name or name.endswith((".pyc", "/.env")):
                raise ValueError("Invalid wheel member")
            if name.startswith("agentic_systems/"):
                assert archive.read(name) == (installed / name).read_bytes(), name
                assert archive.read(name) == (root / "src" / name).read_bytes(), name
        record = next(name for name in names if name.endswith(".dist-info/RECORD"))
        for name, digest, size in csv.reader(io.StringIO(archive.read(record).decode())):
            if digest:
                algorithm, expected = digest.split("=", 1)
                actual = base64.urlsafe_b64encode(hashlib.new(algorithm, archive.read(name)).digest()).rstrip(b"=").decode()
                assert actual == expected and len(archive.read(name)) == int(size), name
                checked += 1
    return {"version": toolkit.__version__, "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "record_hashes_verified": checked, "source_matches": True, "installed_matches": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    print(json.dumps(verify(parser.parse_args().wheel)))
