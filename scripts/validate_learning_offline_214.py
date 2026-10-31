"""Execute each current example against an explicitly selected installed wheel."""

import argparse
import hashlib
import importlib
import json
import os
import platform
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--only", default="")
args = parser.parse_args()
SITE = Path(os.environ["AGENTIC_VALIDATION_SITE"]).resolve()
sys.path[:0] = [
    str(SITE),
    str(ROOT),
    str(ROOT / "tutorials"),
    str(ROOT / "examples/agentic_systems_studio/src"),
]
from _offline import enforce_offline, blocked_attempts  # noqa: E402
import agentic_systems as toolkit  # noqa: E402

# Botocore's user-agent asks platform for OS metadata. On Windows its first
# lookup may spawn cmd.exe; populate that stdlib cache before the app guard.
# This does not permit application subprocesses or credential discovery.
platform.platform()
enforce_offline()
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
os.environ["OTEL_SDK_DISABLED"] = "true"
assert toolkit.__version__ == os.environ["AGENTIC_TEST_VERSION"]
assert Path(toolkit.__file__).resolve().is_relative_to(SITE)
E = Path(os.environ["AGENTIC_VALIDATION_EVIDENCE"]).resolve()
(E / "examples").mkdir(parents=True, exist_ok=True)


def serialize(value):
    if isinstance(value, toolkit.RunResult):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(k): serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    return value


def results(value):
    if isinstance(value, dict):
        if {"execution_id", "status", "children", "usage", "data"} <= value.keys():
            return [toolkit.RunResult(**value)]
        return [x for v in value.values() for x in results(v)]
    if isinstance(value, list):
        return [x for v in value for x in results(v)]
    return []


rows = []
paths = sorted(
    p
    for p in (ROOT / "examples").rglob("example.py")
    if not any(k in p.parts for k in ("history", "__pycache__", "evidence"))
)
paths += [
    ROOT / "examples/common_graph/application.py",
    ROOT / "examples/api_214/application.py",
    ROOT / "examples/context_memory_lineage/application.py",
]
for path in paths:
    relative = path.relative_to(ROOT).as_posix()
    if args.only and args.only not in relative:
        continue
    if "strands_protocol_graph" in relative:
        rows.append(
            {
                "path": relative,
                "status": "separate-local-protocol-profile",
                "passed": None,
            }
        )
        continue
    started = time.monotonic()
    row = {
        "path": relative,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "passed": False,
    }
    try:
        module = importlib.import_module(
            ".".join(path.relative_to(ROOT).with_suffix("").parts)
        )
        entry = getattr(module, "run", None) or getattr(module, "demonstrate")
        output = serialize(entry())
        captured = results(output)
        assert all(r.check_invariants().ok for r in captured)
        row.update(
            {
                "passed": True,
                "status": "offline-passed",
                "output": output,
                "run_results": [r.to_dict() for r in captured],
                "lineage": [
                    {
                        "human": r.lineage(name=relative).render(),
                        "agent": r.lineage().to_prompt_context(),
                    }
                    for r in captured
                ],
            }
        )
    except Exception as exc:
        row["error"] = {
            "type": type(exc).__name__,
            "message": str(exc)[-2000:],
            "traceback": traceback.format_exc()[-5000:],
        }
    row["elapsed_s"] = round(time.monotonic() - started, 3)
    rows.append(row)
    filename = relative.replace("/", "--") + ".json"
    (E / "examples" / filename).write_text(
        json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: row.get(k) for k in ("path", "passed", "error")}), flush=True)
report = {
    "version": toolkit.__version__,
    "rows": rows,
    "inference_requests": 0,
    "offline_guard_blocked_attempts": blocked_attempts(),
}
(E / ("examples-selected.json" if args.only else "examples-offline.json")).write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
assert blocked_attempts() == 0, (
    "An example attempted application networking/process execution"
)
raise SystemExit(0 if all(row["passed"] is not False for row in rows) else 1)
