"""Lossless Bedrock wire projection; local Tool contracts remain authoritative."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


# Model-specific capability, verified against AWS's runtime model card. Do not
# assume that another model/profile supports strict decoding because Converse
# itself accepts the parameter.
_STRICT_TOOL_MODELS = frozenset({"qwen.qwen3-32b-v1:0"})
_KEYWORDS = frozenset({
    "$defs", "definitions", "$ref", "type", "properties", "required",
    "additionalProperties", "items", "anyOf", "allOf", "enum", "const",
    "title", "description", "default",
})


def _strict_schema_counts(schema: Any) -> tuple[int, int] | None:
    """Recognize a conservative AWS subset without rewriting the user's schema.

    Open objects, unconstrained values, recursive references and unsupported
    constraints keep their original schema and local validation. They are not
    silently closed, stripped of constraints or advertised as server-enforced.
    """
    if not isinstance(schema, dict):
        return None
    optional = unions = 0

    def visit(node: Any, refs: frozenset[str] = frozenset()) -> bool:
        nonlocal optional, unions
        if not isinstance(node, dict) or not node or set(node) - _KEYWORDS:
            return False
        if "$ref" in node:
            ref = node["$ref"]
            if not isinstance(ref, str) or not ref.startswith("#/") or ref in refs:
                return False
            target = schema
            for part in ref[2:].split("/"):
                if not isinstance(target, dict):
                    return False
                target = target.get(part.replace("~1", "/").replace("~0", "~"))
            if not visit(target, refs | {ref}):
                return False
        elif not any(key in node for key in ("type", "anyOf", "allOf", "enum", "const")):
            return False
        kind = node.get("type")
        if isinstance(kind, list):
            unions += 1
        if kind == "object" or isinstance(kind, list) and "object" in kind:
            properties = node.get("properties", {})
            if node.get("additionalProperties") is not False or not isinstance(properties, dict):
                return False
            optional += len(set(properties) - set(node.get("required", [])))
            if not all(visit(value, refs) for value in properties.values()):
                return False
        if "items" in node and not visit(node["items"], refs):
            return False
        for key in ("anyOf", "allOf"):
            if key in node:
                if key == "anyOf":
                    unions += 1
                if not all(visit(value, refs) for value in node[key]):
                    return False
        return True

    if not visit(schema) or optional > 12 or unions > 16:
        return None
    return optional, unions


def bedrock_strict_tools(tools: list[dict[str, Any]], model_id: str) -> list[dict[str, Any]]:
    """Enable supported strict decoding without changing a single schema value.

    An explicit SDK strict choice is retained. No request is retried with a
    weaker schema if Bedrock rejects strict mode. No response values are filled.
    Tool.strict controls local output semantics; it is not a wire-schema flag.
    """
    result = deepcopy(tools)
    if model_id not in _STRICT_TOOL_MODELS:
        return result
    optional = unions = 0
    for entry in result:
        spec = entry.get("toolSpec")
        if not isinstance(spec, dict):  # Cache points are not Tools.
            continue
        counts = _strict_schema_counts(spec.get("inputSchema", {}).get("json"))
        if counts is None:
            continue
        next_optional, next_unions = counts
        optional += next_optional
        unions += next_unions
        if optional <= 12 and unions <= 16:
            spec.setdefault("strict", True)
    return result
