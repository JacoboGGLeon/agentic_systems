"""Canonical deterministic operations and portable capability packages."""
from __future__ import annotations

import asyncio
import inspect
from functools import wraps
import math
from dataclasses import dataclass, field, replace
import importlib.util
from pathlib import Path
import sys
from types import MappingProxyType
import uuid
import weakref

from ._results import _from_engine, _json, _record_child
from ._context import Context, _active_execution


@dataclass(frozen=True)
class _Tool:
    name: str
    description: str
    _function: object = field(repr=False)
    _input_schema: object = field(default=None, repr=False)
    _output_schema: object = field(default=None, repr=False)
    metadata: object = field(default_factory=dict)
    _module_owner: object = field(default=None, repr=False, compare=False)

    def inspect(self):
        return {"name": self.name, "description": self.description, "metadata": _json(dict(self.metadata)),
                "input_schema": self._input_schema.model_json_schema() if self._input_schema else None,
                "output_schema": self._output_schema.model_json_schema() if self._output_schema else None}

    def _to_engine(self):
        from ._engine.tools.tool import Tool
        signature = inspect.signature(self._function)
        annotations = inspect.get_annotations(self._function, eval_str=True)
        contextual = "context" in signature.parameters
        business = [p for p in signature.parameters.values() if p.name != "context"]
        if self._input_schema is not None and len(business) == 1:
            declared = annotations.get(business[0].name, inspect.Signature.empty)
            from typing import Any
            if declared not in (inspect.Signature.empty, Any) and not (
                isinstance(declared, type) and issubclass(self._input_schema, declared)
            ):
                raise TypeError("A single-parameter Tool with input_schema receives that Pydantic model; annotate the parameter accordingly")
        if contextual and signature.parameters["context"].kind is not inspect.Parameter.KEYWORD_ONLY:
            raise TypeError("Injected Tool context must be keyword-only")
        if contextual and annotations.get("context") is not Context:
            raise TypeError("Injected Tool context must be annotated with Context")
        @wraps(self._function)
        def execute(*args, **kwargs):
            if contextual:
                active = _active_execution.get()
                kwargs["context"] = active.semantic if active is not None else Context({})
            raw = self._function(*args, **kwargs)
            source = raw.model_dump(mode="python") if hasattr(raw, "model_dump") else raw
            def finite(value):
                if isinstance(value, dict):
                    for item in value.values():
                        finite(item)
                elif isinstance(value, (list, tuple)):
                    for item in value:
                        finite(item)
                elif isinstance(value, float) and not math.isfinite(value):
                    raise ValueError("Tool output contains a non-finite number")
            finite(source)
            _json(raw.model_dump(mode="json") if hasattr(raw, "model_dump") else raw)
            return raw
        execute.__annotations__ = {k: v for k, v in annotations.items() if k != "context"}
        execute.__signature__ = signature.replace(parameters=[p for p in signature.parameters.values() if p.name != "context"])
        return Tool(execute, name=self.name, description=self.description,
                    input_schema=self._input_schema, output_schema=self._output_schema, metadata=dict(self.metadata))

    def run(self, input=None):
        output = _from_engine(self._to_engine().run(input))
        return _record_child(replace(output, meta={**output.meta, "name": self.name, "kind": "tool"}))

    async def arun(self, input=None):
        return await asyncio.to_thread(self.run, input)

    def __call__(self, state):
        """Use a Tool directly as a LangGraph node; bind only declared inputs."""
        state = _json(state)
        parameters = inspect.signature(self._function).parameters
        accepted = self._input_schema.model_fields if self._input_schema is not None else parameters
        payload = {key: value for key, value in state.items() if key in accepted and key != "context"}
        output = self.run(payload)
        active = _active_execution.get()
        if active is not None:
            active.last_result = output
        elif not output.ok:
            raise RuntimeError(str(output.errors))
        return output.data


def tool(function=None, /, *, name=None, description=None, input_schema=None, output_schema=None, metadata=None):
    def decorate(fn):
        if not callable(fn) or inspect.iscoroutinefunction(fn):
            raise TypeError("A Tool wraps a synchronous deterministic callable")
        selected = getattr(fn, "__name__", "") if name is None else name
        if not isinstance(selected, str) or not selected.strip():
            raise ValueError("Tool name is required")
        for schema in (input_schema, output_schema):
            if schema is not None:
                from pydantic import BaseModel
                if not isinstance(schema, type) or not issubclass(schema, BaseModel):
                    raise TypeError("Tool schemas must be Pydantic model classes")
        result = _Tool(selected, description if description is not None else fn.__doc__ or "", fn,
                       input_schema, output_schema, MappingProxyType(_json(metadata or {})))
        result._to_engine().check().raise_if_failed()
        return result
    return decorate if function is None else decorate(function)


@dataclass(frozen=True)
class _Skill:
    name: str
    tools: tuple
    instructions: str
    description: str
    version: str
    metadata: object

    def inspect(self):
        return {"name": self.name, "description": self.description, "version": self.version,
                "instructions": self.instructions, "tools": [t.inspect() for t in self.tools], "metadata": _json(dict(self.metadata))}

    def _to_engine(self):
        from ._engine.skills.skill import Skill
        return Skill(name=self.name, tools=[t._to_engine() for t in self.tools], description=self.description,
                     prompts={"instructions": self.instructions}, metadata=dict(self.metadata), version=self.version)


def skill(*, name, description="", tools=(), instructions="", version="0.1.0", metadata=None):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Skill name is required")
    items = tuple(tools)
    if any(not isinstance(t, _Tool) for t in items):
        raise TypeError("Skills contain @tool operations")
    if len({t.name for t in items}) != len(items):
        raise ValueError("Duplicate Tool identity in Skill")
    if not all(isinstance(v, str) for v in (description, instructions, version)):
        raise TypeError("Skill description, instructions and version must be strings")
    return _Skill(name, items, instructions, description, version, MappingProxyType(_json(metadata or {})))


def load_skill(path):
    if not isinstance(path, (str, Path)):
        raise TypeError("load_skill accepts a filesystem path")
    folder = Path(path).expanduser().resolve()
    if not (folder / "SKILL.md").is_file() or not (folder / "skill.py").is_file():
        raise ValueError("Skill requires SKILL.md and skill.py")
    package = "_loaded_skill_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(package, folder / "__init__.py", submodule_search_locations=[str(folder)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[package] = module
    success = False
    try:
        if (folder / "__init__.py").is_file():
            spec.loader.exec_module(module)
        source = importlib.util.spec_from_file_location(package + ".skill", folder / "skill.py")
        loaded = importlib.util.module_from_spec(source)
        sys.modules[source.name] = loaded
        source.loader.exec_module(loaded)
        build = getattr(loaded, "build_skill", None)
        if not callable(build):
            raise ValueError("skill.py must define build_skill()")
        result = build()
        if not isinstance(result, _Skill):
            raise TypeError("build_skill must return skill(...)")
        owner = _ModuleOwner()
        weakref.finalize(owner, _remove_modules, package)
        result = replace(result, tools=tuple(replace(t, _module_owner=owner) for t in result.tools))
        success = True
        return result
    finally:
        if not success:
            _remove_modules(package)


def _remove_modules(package):
    for key in tuple(sys.modules):
        if key == package or key.startswith(package + "."):
            del sys.modules[key]


class _ModuleOwner:
    """Keep lazy relative imports alive while any returned Tool is retained."""
