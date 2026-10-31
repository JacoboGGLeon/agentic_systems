"""Validate current catalog declarations, paths and truthful acceptance scope."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check():
    catalog = json.loads((ROOT / "examples/catalog.json").read_text(encoding="utf-8"))
    entries = catalog["entries"]
    ids = [entry["id"] for entry in entries]
    assert len(ids) == len(set(ids)), "Duplicate catalog ID"
    for entry in entries:
        assert entry["purpose"] and entry["sources"], entry["id"]
        for source in entry["sources"]:
            target = source["target"]
            if not target.startswith(("https://", "http://")):
                assert (ROOT / target.split("#")[0]).exists(), (entry["id"], target)
        validation = entry.get("validation", {})
        if validation.get("entrypoint"):
            assert (ROOT / validation["entrypoint"]).is_file(), entry["id"]
        # Historical acceptance has its own version/hash. This check never
        # promotes it to a new wheel or claims an external service is usable.
    return {"entries": len(entries), "inference_executed": False}


if __name__ == "__main__":
    print(json.dumps(check()))
