"""Run a local demonstration with socket/subprocess activity forbidden."""

import argparse
import hashlib
import importlib.metadata
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unified_grammar.offline import blocked_attempts, enforce_offline  # noqa: E402

enforce_offline()

from unified_grammar.demo import (  # noqa: E402
    EXPECTED,
    build,
    episode,
    evaluation,
    nested_application,
)
import agentic_systems as toolkit  # noqa: E402

WHEEL_SHA256 = "2c14a8e6f871fcc455acbf899db851130c49a129ba988821d6656e90ebc3d47b"


def verify_wheel(path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != WHEEL_SHA256:
        raise ValueError("Wheel differs from the published 2.1.2 artifact")
    package = Path(toolkit.__file__).resolve().parent
    if "site-packages" not in package.parts:
        raise ValueError("Wheel verification requires a non-editable installation")
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.startswith("agentic_systems/") and not name.endswith("/"):
                if (package.parent / name).read_bytes() != archive.read(name):
                    raise ValueError("Installed package differs from the exact wheel")
    return {"status": "exact-wheel-bytes-verified", "wheel_sha256": WHEEL_SHA256}


def run():
    rows = []
    alternatives = []
    for owner in ("Agent", "System"):
        for kind in EXPECTED:
            for backend in ("native", "langgraph"):
                unit = build(owner, kind, backend)
                compiled = unit.compile()
                direct = unit.run({"value": 3})
                explicit = compiled.run({"value": 3})
                ok = (
                    direct.ok
                    and explicit.ok
                    and direct.data == explicit.data == {"value": EXPECTED[kind]}
                )
                rows.append(
                    dict(
                        owner=owner,
                        flow=kind,
                        backend=backend,
                        passed=ok,
                        input={"value": 3},
                        process=[
                            {"step": n.meta["name"], "output": n.data}
                            for n in direct.walk()
                            if n.meta.get("prototype_kind") == "action"
                        ],
                        output=direct.data,
                        direct=direct.to_dict(),
                        compiled=explicit.to_dict(),
                        topology=compiled.inspect(),
                    )
                )
                if kind == "graph":
                    alternate = compiled.run({"value": -3})
                    alternatives.append(dict(
                        owner=owner, backend=backend, input={"value": -3},
                        passed=alternate.ok and alternate.data == {"value": -2},
                        output=alternate.data, result=alternate.to_dict(),
                    ))
    nested = nested_application().run({"value": 3})
    env = episode().run()
    report = evaluation().compile().run()
    return dict(
        schema_version="unified-grammar.offline-prototype.v1",
        python_version=sys.version.split()[0],
        package_version=importlib.metadata.version("agentic-systems"),
        package_file=str(Path(toolkit.__file__).resolve()),
        langgraph_version=importlib.metadata.version("langgraph"),
        source_sha256={
            str(path.relative_to(Path(__file__).parent)).replace(
                "\\", "/"
            ): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path(__file__).parent.rglob("*.py"))
        },
        inference_requests=0,
        blocked_network_or_subprocess_attempts=blocked_attempts(),
        matrix=rows,
        decision_alternatives=alternatives,
        nested=nested.to_dict(),
        environment=env.to_dict(),
        evaluation=report.to_dict(),
        passed=all(row["passed"] for row in rows)
        and all(row["passed"] for row in alternatives)
        and nested.ok
        and env.ok
        and report.ok,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path(__file__).parent / "evidence" / "offline-run.json",
    )
    parser.add_argument("--wheel", type=Path)
    args = parser.parse_args()
    artifact = (
        verify_wheel(args.wheel)
        if args.wheel
        else {"status": "installed-metadata-only"}
    )
    output = run()
    output["artifact"] = artifact
    destination = args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            dict(
                passed=output["passed"],
                matrix_passed=sum(row["passed"] for row in output["matrix"]),
                decision_alternatives_passed=sum(
                    row["passed"] for row in output["decision_alternatives"]
                ),
                inference_requests=0,
                report=str(destination),
                report_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
            )
        )
    )
    raise SystemExit(0 if output["passed"] else 1)
