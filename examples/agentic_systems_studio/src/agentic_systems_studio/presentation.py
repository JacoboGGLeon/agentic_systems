"""Public-evidence projections used by the Studio presentation adapter."""

from __future__ import annotations

import ast
from collections.abc import Mapping
import inspect
import re
from typing import Any

import agentic_systems as toolkit


_DYNAMIC_EXECUTION_PRIMITIVES = frozenset({"__import__", "compile", "eval", "exec"})


def _generated_python_blocks(text: str) -> list[str]:
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, flags=re.DOTALL)
    if blocks:
        return blocks
    clean = text.strip()
    if clean.startswith(("import agentic_systems", "from agentic_systems")):
        ast.parse(clean)
        return [clean]
    return []


def _usage_fields(value: Any, *, prefix: str = "") -> list[tuple[str, Any]]:
    if not isinstance(value, Mapping):
        return []
    fields: list[tuple[str, Any]] = []
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(item, Mapping):
            fields.extend(_usage_fields(item, prefix=path))
        elif item is not None:
            fields.append((path, item))
    return fields


def processing_mark(result: Any) -> str:
    """Summarize observed execution without exposing private reasoning."""

    payload = result.normalized() if hasattr(result, "normalized") else {}
    runtime = dict(payload.get("runtime") or {})
    provider = (
        runtime.get("provider")
        or runtime.get("runtime_engine")
        or runtime.get("engine")
        or getattr(result, "engine", None)
        or "unknown"
    )
    framework = runtime.get("framework") or "native"
    observed_tools = []
    for tool in payload.get("tools") or []:
        name = tool.get("name") if isinstance(tool, dict) else None
        if name and name not in observed_tools:
            observed_tools.append(str(name))

    status = "✓ Procesado" if bool(getattr(result, "ok", False)) else "✗ Falló"
    fields = [status, f"provider={provider}", f"framework={framework}"]
    if observed_tools:
        fields.append("tools=" + ", ".join(observed_tools))
    else:
        fields.append("tools=ninguna")
    return " · ".join(fields)


def usage_mark(result: Any) -> str:
    """Render every available usage fact without synthesizing missing values."""

    payload = result.normalized() if hasattr(result, "normalized") else {}
    usage = _usage_fields(payload.get("usage") or {})
    if not usage:
        return "Usage: no reportado por el runtime"
    return "Usage: " + " | ".join(f"{key}={value}" for key, value in usage)


def validate_generated_tool_contracts(text: str) -> None:
    """Reject generated Python Tools whose declared output violates the public API."""

    blocks = _generated_python_blocks(text)
    for block in blocks:
        if "@toolkit.tool" not in block:
            continue
        tree = ast.parse(block)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorators = {ast.unparse(item) for item in node.decorator_list}
            if "toolkit.tool" not in decorators:
                continue
            annotation = ast.unparse(node.returns) if node.returns is not None else ""
            if annotation != "dict" and not annotation.startswith("dict["):
                raise ValueError(
                    "Generated @toolkit.tool functions must declare a dictionary "
                    f"return type; {node.name!r} declared {annotation or 'nothing'!r}."
                )


def validate_generated_python_safety(
    text: str,
    *,
    allow_code: bool = True,
) -> None:
    """Reject unsolicited code and unsafe dynamic execution in public answers."""

    blocks = _generated_python_blocks(text)
    if blocks and not allow_code:
        raise ValueError(
            "The current request did not ask for Python code; return only the "
            "natural-language result supported by Tool evidence."
        )
    for block in blocks:
        tree = ast.parse(block)
        unsafe_calls = {
            node.func.id if isinstance(node.func, ast.Name) else node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                isinstance(node.func, ast.Name)
                and node.func.id in _DYNAMIC_EXECUTION_PRIMITIVES
                or isinstance(node.func, ast.Attribute)
                and node.func.attr in _DYNAMIC_EXECUTION_PRIMITIVES
            )
        }
        if unsafe_calls:
            raise ValueError(
                "Generated Python code may not call dynamic execution primitives: "
                f"{sorted(unsafe_calls)}."
            )


def validate_generated_agentic_systems_code(
    text: str,
    *,
    required_calls: tuple[str, ...] = (),
    allow_code: bool = True,
) -> None:
    """Validate generated examples against the canonical public grammar."""

    validate_generated_python_safety(text, allow_code=allow_code)
    validate_generated_tool_contracts(text)
    blocks = _generated_python_blocks(text)
    relevant = [
        block for block in blocks if "agentic_systems" in block or "toolkit." in block
    ]
    if not relevant:
        return

    observed_calls: set[str] = set()
    for block in relevant:
        tree = ast.parse(block)
        factory_results: dict[str, str] = {}
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            if not isinstance(value, ast.Call):
                continue
            factory = ast.unparse(value.func)
            if not factory.startswith("toolkit."):
                continue
            symbol = factory.rsplit(".", 1)[-1]
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    factory_results[target.id] = symbol
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                function = ast.unparse(node.func)
                if isinstance(node.func, ast.Name):
                    factory = factory_results.get(node.func.id)
                    if factory == "skill":
                        raise ValueError(
                            f"{node.func.id} is a Skill object, not a callable; "
                            "attach it to an Agent through skills=[...]."
                        )
                if isinstance(node.func, ast.Call):
                    nested_factory = ast.unparse(node.func.func)
                    if nested_factory == "toolkit.skill":
                        raise ValueError(
                            "toolkit.skill(...) returns a Skill object and cannot be "
                            "called directly; attach it through skills=[...]."
                        )
                if function.startswith("toolkit."):
                    symbol = function.rsplit(".", 1)[-1]
                    observed_calls.add(symbol)
                    public_factory = getattr(toolkit, symbol, None)
                    if callable(public_factory):
                        signature = inspect.signature(public_factory)
                        if not any(
                            parameter.kind == inspect.Parameter.VAR_KEYWORD
                            for parameter in signature.parameters.values()
                        ):
                            allowed = set(signature.parameters)
                            unknown = sorted(
                                keyword.arg
                                for keyword in node.keywords
                                if keyword.arg is not None
                                and keyword.arg not in allowed
                            )
                            if unknown:
                                raise ValueError(
                                    f"toolkit.{symbol}(...) received unsupported "
                                    f"keyword arguments: {unknown}."
                                )
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                decorators = {ast.unparse(item) for item in node.decorator_list}
                if "toolkit.tool" in decorators:
                    observed_calls.add("tool")
                if "toolkit.skill" in decorators:
                    raise ValueError(
                        "toolkit.skill is a factory, not a decorator; use "
                        "toolkit.skill(name=..., tools=[...])."
                    )
            if isinstance(node, ast.ClassDef):
                bases = {ast.unparse(item) for item in node.bases}
                if "toolkit.Skill" in bases:
                    raise ValueError(
                        "Studio examples must use the canonical toolkit.skill(...) "
                        "factory instead of subclassing toolkit.Skill."
                    )

    missing = sorted(set(required_calls).difference(observed_calls))
    if missing:
        raise ValueError(
            "Generated Agentic Systems code omitted canonical calls required by "
            f"the current request: {missing}."
        )


__all__ = [
    "processing_mark",
    "usage_mark",
    "validate_generated_agentic_systems_code",
    "validate_generated_python_safety",
    "validate_generated_tool_contracts",
]
