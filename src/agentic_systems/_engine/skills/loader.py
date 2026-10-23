"""Skill asset loader loading primitives."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..errors import SkillLoadError
from .skill import Skill


class SkillManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    version: str = "0.1.0"
    description: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    tools: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class LoadedSkill(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    path: str
    manifest: SkillManifest
    registry: dict[str, Any] = Field(default_factory=dict)
    runtime_skill: Skill | None = Field(default=None, exclude=True)

def load_skill_definition(path: str | Path) -> Skill:
    """Load a portable Skill without constructing or mutating a system."""

    skill_path = Path(path).resolve()
    if not skill_path.exists() or not skill_path.is_dir():
        raise SkillLoadError(
            f"Skill path does not exist or is not a directory: {skill_path}"
        )
    skill_md = skill_path / "SKILL.md"
    skill_py = skill_path / "skill.py"
    if not skill_md.exists():
        raise SkillLoadError(f"Skill '{skill_path.name}' is missing SKILL.md")
    if not skill_py.exists():
        raise SkillLoadError(f"Skill '{skill_path.name}' is missing skill.py")

    module_name = f"agentic_skill_{skill_path.name}_{abs(hash(str(skill_path)))}"
    module = _load_skill_module(skill_path, module_name)
    for builder_name in ("build_skill", "build"):
        builder = getattr(module, builder_name, None)
        if not callable(builder):
            continue
        built = builder()
        if not isinstance(built, Skill):
            raise SkillLoadError(
                f"{builder_name}() must return a Skill, got {type(built).__name__}."
            )
        built.metadata.setdefault("source", "filesystem_loader")
        built.metadata.setdefault("path", str(skill_path))
        return built

    raise SkillLoadError(
        f"Skill '{skill_path.name}' must expose build_skill() -> Skill for pure "
        "loading. Legacy register(system) skills can be loaded explicitly with "
        "system.load_skill(path)."
    )


def load_skill(system: Any, path: str | Path) -> LoadedSkill:
    skill_path = Path(path).resolve()
    if not skill_path.exists() or not skill_path.is_dir():
        raise SkillLoadError(f"Skill path does not exist or is not a directory: {skill_path}")
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        raise SkillLoadError(f"Skill '{skill_path.name}' is missing SKILL.md")
    skill_py = skill_path / "skill.py"
    if not skill_py.exists():
        raise SkillLoadError(f"Skill '{skill_path.name}' is missing skill.py")

    module_name = f"agentic_skill_{skill_path.name}_{abs(hash(str(skill_path)))}"
    module = _load_skill_module(skill_path, module_name)

    register = getattr(module, "register", None)
    if not callable(register):
        raise SkillLoadError(f"Skill '{skill_path.name}' must expose register(system)")

    registry = register(system)
    if registry is None:
        registry = {}
    if not isinstance(registry, dict):
        raise SkillLoadError("register(system) must return a dict summary.")

    manifest_data = dict(registry.get("manifest") or {})
    runtime_skill_from_registry = registry.get("runtime_skill")
    if runtime_skill_from_registry is not None and not isinstance(runtime_skill_from_registry, Skill):
        raise SkillLoadError("registry['runtime_skill'] must be a Skill instance when provided.")
    manifest_data.setdefault("name", getattr(runtime_skill_from_registry, "name", skill_path.name))
    manifest_data.setdefault("version", getattr(runtime_skill_from_registry, "version", "0.1.0"))
    manifest_data.setdefault("description", getattr(runtime_skill_from_registry, "description", "") or _first_non_empty_line(skill_md.read_text(encoding="utf-8")))
    manifest_data.setdefault("tools", list(getattr(runtime_skill_from_registry, "tool_names", ())) or [spec.name for spec in system.tools])
    manifest_data.setdefault("agents", [agent.name for agent in system.agents])
    manifest = SkillManifest.model_validate(manifest_data)
    if runtime_skill_from_registry is not None:
        runtime_skill = runtime_skill_from_registry
    else:
        runtime_tools = [system.public_tools[name] for name in manifest.tools if name in system.public_tools]
        runtime_skill = Skill(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            tools=runtime_tools,
            metadata={"source": "filesystem_loader", "path": str(skill_path)},
        )
    loaded = LoadedSkill(path=str(skill_path), manifest=manifest, registry=registry, runtime_skill=runtime_skill)
    system._skills.append(loaded)
    return loaded


def _load_skill_module(skill_path: Path, module_name: str) -> ModuleType:
    """Load a filesystem skill as an isolated package, without mutating sys.path.

    Skills are directories with ``skill.py`` and optional sibling modules. Loading
    the directory as a temporary package lets ``skill.py`` use normal relative
    imports such as ``from .runtime import ...`` without exposing the skill
    folder globally.
    """

    package_init = skill_path / "__init__.py"
    if package_init.exists():
        package_spec = importlib.util.spec_from_file_location(
            module_name,
            package_init,
            submodule_search_locations=[str(skill_path)],
        )
    else:
        package_spec = importlib.util.spec_from_loader(module_name, loader=None, is_package=True)
        if package_spec is not None:
            package_spec.submodule_search_locations = [str(skill_path)]
    if package_spec is None:
        raise SkillLoadError(f"Cannot create package spec for skill at {skill_path}")

    package = importlib.util.module_from_spec(package_spec)
    package.__path__ = [str(skill_path)]  # type: ignore[attr-defined]
    sys.modules[module_name] = package
    if package_spec.loader is not None:
        package_spec.loader.exec_module(package)

    skill_module_name = f"{module_name}.skill"
    skill_spec = importlib.util.spec_from_file_location(skill_module_name, skill_path / "skill.py")
    if skill_spec is None or skill_spec.loader is None:
        raise SkillLoadError(f"Cannot import skill.py from {skill_path}")
    module = importlib.util.module_from_spec(skill_spec)
    module.__package__ = module_name
    sys.modules[skill_module_name] = module
    skill_spec.loader.exec_module(module)
    return module


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip("# ").strip()
        if line:
            return line
    return ""
