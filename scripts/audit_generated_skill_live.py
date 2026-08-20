"""Live-validate every generated skill scaffold without provider fallback."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

from agentic_systems_studio import get_system_spec


def _jsonable(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _package(project: Path) -> tuple[Path, str]:
    candidates = sorted(path for path in (project / "src").iterdir() if path.is_dir())
    if len(candidates) != 1:
        raise ValueError(
            f"Expected one source package in {project}; found {candidates}"
        )
    return candidates[0], candidates[0].name


def _run(project: Path, provider: str, framework: str, model: str | None) -> dict:
    manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))
    package_path, package = _package(project)
    source = package_path.parent
    spec = get_system_spec(manifest["id"])
    sys.path.insert(0, str(source))
    started = time.perf_counter()
    try:
        settings_module = importlib.import_module(f"{package}.settings")
        system_module = importlib.import_module(f"{package}.system")
        settings = settings_module.AppSettings(
            provider=provider,
            framework=framework,
            model=model,
        )
        system = system_module.build_system(settings)
        inspection = system.inspect()
        result = system.run(spec.sample_input)
        return {
            "system_id": spec.id,
            "provider": provider,
            "framework": framework,
            "model": result.model,
            "elapsed_s": round(time.perf_counter() - started, 3),
            "inspect_ok": bool(inspection.get("ok", True)),
            "run_result_type": type(result).__name__,
            "ok": bool(result.ok),
            "errors": _jsonable(result.errors),
            "text": result.text,
            "data": _jsonable(result.data),
            "children": [
                {
                    "ok": bool(child.ok),
                    "engine": child.engine,
                    "model": child.model,
                    "errors": _jsonable(child.errors),
                    "usage": _jsonable(child.usage),
                    "tool_events": [event.name for event in child.tool_events],
                }
                for child in result.children
            ],
        }
    except Exception as exc:
        return {
            "system_id": manifest["id"],
            "provider": provider,
            "framework": framework,
            "model": model,
            "elapsed_s": round(time.perf_counter() - started, 3),
            "inspect_ok": False,
            "run_result_type": None,
            "ok": False,
            "errors": [{"code": type(exc).__name__, "message": str(exc)}],
            "children": [],
        }
    finally:
        sys.path.remove(str(source))
        for key in list(sys.modules):
            if key == package or key.startswith(f"{package}."):
                del sys.modules[key]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--framework", default="agentic-systems")
    parser.add_argument("--model")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    projects = sorted(path for path in root.iterdir() if path.is_dir())
    if len(projects) != 10:
        raise SystemExit(
            f"Expected ten generated projects in {root}; found {len(projects)}"
        )

    results = []
    for index, project in enumerate(projects, start=1):
        result = _run(project, args.provider, args.framework, args.model)
        results.append(result)
        print(
            f"[{index:02d}/10] {result['system_id']}: ok={result['ok']} "
            f"model={result.get('model')} elapsed={result['elapsed_s']}s "
            f"children={len(result['children'])}",
            flush=True,
        )

    payload = {
        "schema_version": "agentic-systems.skill-live-audit/v1",
        "provider": args.provider,
        "framework": args.framework,
        "requested_model": args.model,
        "count": len(results),
        "passed": sum(result["ok"] for result in results),
        "failed": sum(not result["ok"] for result in results),
        "results": results,
    }
    output = args.output or root / f"{args.provider}-{args.framework}-live.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Evidence: {output.resolve()}", flush=True)
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
