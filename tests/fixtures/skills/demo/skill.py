from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_tool_module():
    tools_path = Path(__file__).with_name("tools.py")
    spec = importlib.util.spec_from_file_location("agentic_systems_demo_skill_tools", tools_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def register(system):
    """Register the demo skill tools and return a loader summary."""
    module = _load_tool_module()
    tool_functions = [
        module.sumar,
        module.restar,
        module.multiplicar,
        module.dividir,
        module.number_to_text,
        module.read_md,
    ]
    for fn in tool_functions:
        system.tool(fn)

    manifest_path = Path(__file__).with_name("skill.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "manifest": manifest,
        "tool_names": [fn.__name__ for fn in tool_functions],
        "prompt_files": sorted(str(path.relative_to(Path(__file__).parent)) for path in (Path(__file__).parent / "prompts").glob("*.md")),
        "data_files": sorted(str(path.relative_to(Path(__file__).parent)) for path in (Path(__file__).parent / "data").glob("*.md")),
    }
