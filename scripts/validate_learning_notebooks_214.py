"""Fresh-kernel notebook validation; offline and explicitly budgeted live profiles."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--profile", choices=("offline", "live", "local"), default="offline"
)
parser.add_argument("--path", default="")
parser.add_argument(
    "--framework", choices=("native", "openai-agents", "strands"), default="native"
)
args = parser.parse_args()
SITE = Path(os.environ["AGENTIC_VALIDATION_SITE"]).resolve()
E = Path(os.environ["AGENTIC_VALIDATION_EVIDENCE"]).resolve()
VERSION = os.environ["AGENTIC_TEST_VERSION"]
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
destination = E / "notebook-runs" / (stamp + "-" + args.profile)
destination.mkdir(parents=True)
paths = sorted((ROOT / "tutorials").rglob("*.ipynb")) + sorted(
    p for p in (ROOT / "examples").rglob("*.ipynb") if "history" not in p.parts
)
rows = []
for path in paths:
    relative = path.relative_to(ROOT).as_posix()
    if args.path and args.path not in relative:
        continue
    nb = nbformat.read(path, 4)
    code_source = "\n".join(c.source for c in nb.cells if c.cell_type == "code")
    source_hash = hashlib.sha256(code_source.encode()).hexdigest()
    skipped = []
    for index, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        tags = cell.metadata.get("tags", [])
        if args.profile == "live" and "parameters" in tags:
            cell.source = "actor_framework=" + repr(args.framework)
        skip = args.profile == "offline" and any(
            t in tags for t in ("live", "local-service")
        )
        skip |= args.profile == "live" and "local-service" in tags
        skip |= args.profile == "local" and "live" in tags
        if skip:
            cell.metadata["tags"] = [*tags, "skip-execution"]
            skipped.append(index)
    capture = destination / (relative.replace("/", "--") + ".json")
    bootstrap = "import sys\nfrom pathlib import Path\n"
    bootstrap += "sys.path.insert(0, " + repr(str(ROOT / "scripts")) + ")\n"
    if args.profile == "offline":
        bootstrap += "from _offline import enforce_offline, blocked_attempts\nenforce_offline()\n"
    elif args.profile == "live":
        bootstrap += (
            "from agentic_systems_studio.budget import ensure_budget\n__budget=ensure_budget()\n__budget.phase="
            + repr(relative + "/" + args.framework)
            + "\n"
        )
    bootstrap += "import agentic_systems as __toolkit\nassert __toolkit.__version__ == " + repr(VERSION) + "\n"
    bootstrap += (
        "assert Path(__toolkit.__file__).resolve().is_relative_to(Path("
        + repr(str(SITE))
        + "))\n"
    )
    bootstrap += (
        "from grammar_coverage_214 import Coverage\n__coverage=Coverage()\n__coverage.current="
        + repr(relative)
        + "\n__coverage.rows[__coverage.current]=set()\nsys.setprofile(__coverage.profile)\n"
    )
    footer = "sys.setprofile(None)\nimport json\n"
    footer += '''__results, __result_sources, __seen, __memories = {}, {}, set(), {}
def __collect(value, path):
    if isinstance(value, __toolkit.RunResult):
        __results[value.execution_id] = value.to_dict()
        __result_sources.setdefault(value.execution_id, []).append(path)
        return
    if isinstance(value, dict) and {'execution_id','status','children','data','usage','ok','tool_events'} <= value.keys():
        restored = __toolkit.RunResult(**value)
        __results[restored.execution_id] = restored.to_dict()
        __result_sources.setdefault(restored.execution_id, []).append(path)
        return
    if not isinstance(value, (dict,list,tuple)) or id(value) in __seen:
        return
    __seen.add(id(value))
    items = value.items() if isinstance(value, dict) else enumerate(value)
    for key, child in items:
        __collect(child, path + '.' + str(key))
for __name, __value in tuple(globals().items()):
    if __name.startswith('_'):
        continue
    __collect(__value, __name)
    __memory = __value if isinstance(__value, __toolkit.Memory) else getattr(__value, 'memory', None) if isinstance(__value, (__toolkit.Agent,__toolkit.System,__toolkit.Environment)) else None
    if isinstance(__memory, __toolkit.Memory):
        __memories[__name] = __memory.read()
'''
    if args.profile == "offline":
        footer += "assert blocked_attempts()==0\n"
    footer += (
        "Path("
        + repr(str(capture))
        + ").write_text(json.dumps({'grammar':__coverage.report(),'run_results':__results,'result_sources':__result_sources,'memories':__memories},ensure_ascii=False,indent=2),encoding='utf-8')\n"
    )
    nb.cells = [
        nbformat.v4.new_code_cell(bootstrap),
        *nb.cells,
        nbformat.v4.new_code_cell(footer),
    ]
    km = KernelManager(kernel_name="python3")
    km.kernel_spec.argv = [
        sys.executable,
        "-m",
        "ipykernel_launcher",
        "-f",
        "{connection_file}",
    ]
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            (
                str(SITE),
                str(ROOT),
                str(ROOT / "tutorials"),
                str(ROOT / "examples/agentic_systems_studio/src"),
            )
        ),
        "OPENAI_AGENTS_DISABLE_TRACING": "1",
        "OTEL_SDK_DISABLED": "true",
    }
    client = NotebookClient(
        nb, km=km, timeout=240, resources={"metadata": {"path": str(ROOT)}}
    )
    error = None
    try:
        client.execute(env=env)
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)[-4000:]}
    finally:
        if client.kc is not None:
            client.kc.stop_channels()
        if km.has_kernel:
            km.shutdown_kernel(now=False)
    nb.cells = nb.cells[1:-1]
    executed = sum(
        c.cell_type == "code" and c.execution_count is not None for c in nb.cells
    )
    snapshot = destination / relative.replace("/", "--")
    nbformat.write(nb, snapshot)
    # Only the default, unparameterized lesson replaces its visible output.
    if args.profile == "offline" or args.framework == "native":
        original = nbformat.read(path, 4)
        for source, target in zip(nb.cells, original.cells):
            if source.cell_type == "code":
                target.outputs = source.outputs
                target.execution_count = source.execution_count
        nbformat.write(original, path)
    row = {
        "path": relative,
        "profile": args.profile,
        "framework": args.framework,
        "passed": error is None,
        "error": error,
        "executed_code_cells": executed,
        "skipped_cells": skipped,
        "code_sha256_before_parameterization": source_hash,
        "coverage_source_sha256": hashlib.sha256((ROOT / "scripts/grammar_coverage_214.py").read_bytes()).hexdigest(),
        "capture_schema": "recursive-results-memory.v2",
        "snapshot": str(snapshot.relative_to(E)),
        "capture": str(capture.relative_to(E)),
    }
    rows.append(row)
    (destination / "results.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: row[k]
                for k in (
                    "path",
                    "passed",
                    "executed_code_cells",
                    "skipped_cells",
                    "error",
                )
            }
        ),
        flush=True,
    )
raise SystemExit(0 if all(r["passed"] for r in rows) else 1)
