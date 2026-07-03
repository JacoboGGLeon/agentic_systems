from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LEGACY_ROOT = Path(__file__).resolve().parent / "_legacy_modules"


def _load_module(legacy_name: str) -> types.ModuleType:
    legacy_path = LEGACY_ROOT / f"legacy_{legacy_name}.py"
    if not legacy_path.exists():
        raise FileNotFoundError(f"Legacy test module not found: {legacy_path}")

    module_name = f"tests.api._legacy_modules.legacy_{legacy_name}"
    if module_name in sys.modules:
        return sys.modules[module_name]

    module = types.ModuleType(module_name)
    module.__file__ = str(ROOT / "tests" / f"test_{legacy_name}.py")
    module.__package__ = "tests.api._legacy_modules"
    module.__dict__["__builtins__"] = __builtins__
    sys.modules[module_name] = module
    source = legacy_path.read_text(encoding="utf-8-sig")
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def export_legacy_tests(target_globals: dict[str, Any], *legacy_names: str) -> None:
    for legacy_name in legacy_names:
        module = _load_module(legacy_name)
        prefix = legacy_name.replace("-", "_").replace(".", "_")
        for name, value in vars(module).items():
            if name.startswith("test_") or name.startswith("Test"):
                target_globals[f"test__{prefix}__{name}"] = value
