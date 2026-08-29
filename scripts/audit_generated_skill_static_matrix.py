"""Build and inspect every generated app across the static runtime matrix."""

from __future__ import annotations

import importlib
import itertools
import json
import sys
from pathlib import Path

from agentic_systems.registry import FRAMEWORK_NAMES, PROVIDER_NAMES


PROVIDERS = tuple(name for name in PROVIDER_NAMES if name != "python-runtime")
FRAMEWORKS = tuple(
    "agentic-systems" if name == "native" else name for name in FRAMEWORK_NAMES
)


def main(root_value: str) -> int:
    root = Path(root_value).resolve()
    projects = sorted(path for path in root.iterdir() if path.is_dir())
    results = []
    for project in projects:
        manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))
        packages = [path for path in (project / "src").iterdir() if path.is_dir()]
        if len(packages) != 1:
            raise SystemExit(f"Expected one package in {project}")
        package = packages[0].name
        source = packages[0].parent
        sys.path.insert(0, str(source))
        try:
            settings_module = importlib.import_module(f"{package}.settings")
            system_module = importlib.import_module(f"{package}.system")
            for provider, framework in itertools.product(PROVIDERS, FRAMEWORKS):
                try:
                    compiled = system_module.build_system(
                        settings_module.AppSettings(
                            provider=provider,
                            framework=framework,
                        )
                    )
                    inspection = compiled.inspect()
                    results.append(
                        {
                            "system_id": manifest["id"],
                            "provider": provider,
                            "framework": framework,
                            "ok": inspection["unit_count"] == len(manifest["stages"]),
                        }
                    )
                except Exception as exc:
                    results.append(
                        {
                            "system_id": manifest["id"],
                            "provider": provider,
                            "framework": framework,
                            "ok": False,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
        finally:
            sys.path.remove(str(source))
            for key in list(sys.modules):
                if key == package or key.startswith(f"{package}."):
                    del sys.modules[key]

    payload = {
        "schema_version": "agentic-systems.skill-static-matrix/v1",
        "systems": len(projects),
        "requested": len(results),
        "passed": sum(result["ok"] for result in results),
        "failed": sum(not result["ok"] for result in results),
        "providers": list(PROVIDERS),
        "frameworks": list(FRAMEWORKS),
        "results": results,
    }
    output = root / "static-provider-framework-matrix.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {key: payload[key] for key in ("systems", "requested", "passed", "failed")},
            indent=2,
        )
    )
    print(f"Evidence: {output}")
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: audit_generated_skill_static_matrix.py ROOT")
    raise SystemExit(main(sys.argv[1]))
