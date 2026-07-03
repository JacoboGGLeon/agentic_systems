"""Final-answer helpers for Agentic Systems.

The runtime envelope must stay stable, but the user-facing answer may change
shape depending on what the user asked for.  This module keeps that split
explicit:

- ``normalize_output(...)`` converts arbitrary Python/model/tool outputs into a
  JSON-like dictionary.
- ``OutputSchema`` projects that dictionary into the requested final fields.
- ``final_answer(...)`` returns the final answer dictionary shown first by
  notebook/human renderers.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

FINAL_ANSWER_SCHEMA_VERSION = "agentic_systems.final_answer.v1"


class OutputSchema(BaseModel):
    """Declarative projection for user-facing final answers.

    Parameters
    ----------
    fields:
        Field names the final answer should contain.  Missing fields are filled
        with ``None`` unless ``required=True``.
    many:
        When true, project a sequence of rows.  The output root defaults to
        ``rows``.
    root_key:
        Optional root key for ``many=True`` outputs.  Useful for domain labels
        such as ``accounts`` or ``items``.
    required:
        If true, missing requested fields raise ``KeyError``.
    aliases:
        Optional mapping from output field name to source field name.
    """

    model_config = ConfigDict(extra="forbid")

    fields: tuple[str, ...] = Field(default_factory=tuple)
    many: bool = False
    root_key: str | None = None
    required: bool = False
    aliases: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def coerce(cls, value: "OutputSchema | Mapping[str, Any] | None") -> "OutputSchema | None":
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls.model_validate(dict(value))
        raise TypeError("output_schema must be an OutputSchema or mapping.")

    def project(self, value: Any) -> dict[str, Any]:
        payload = normalize_output(value)
        if self.many:
            rows = _extract_rows(payload)
            root = self.root_key or "rows"
            return {root: [self._project_one(row) for row in rows]}
        return self._project_one(payload)

    def _project_one(self, value: Any) -> dict[str, Any]:
        source = normalize_output(value)
        if not self.fields:
            return source
        projected: dict[str, Any] = {}
        for field in self.fields:
            source_field = self.aliases.get(field, field)
            found, item = _lookup_field(source, source_field)
            if not found and self.required:
                raise KeyError(f"Missing required final-answer field {field!r}.")
            projected[field] = item if found else None
        return projected


def output_schema(
    fields: Sequence[str] | None = None,
    *,
    many: bool = False,
    root_key: str | None = None,
    required: bool = False,
    aliases: Mapping[str, str] | None = None,
) -> OutputSchema:
    """Create a final-answer projection schema.

    Examples
    --------
    >>> schema = output_schema(["cuenta", "mes_actual", "diferencia"], many=True)
    >>> schema.project({"rows": [{"cuenta": "123", "mes_actual": 10, "diferencia": 2}]})
    {'rows': [{'cuenta': '123', 'mes_actual': 10, 'diferencia': 2}]}
    """

    return OutputSchema(
        fields=tuple(str(field) for field in (fields or ())),
        many=many,
        root_key=root_key,
        required=required,
        aliases={str(key): str(value) for key, value in dict(aliases or {}).items()},
    )


def normalize_output(value: Any) -> dict[str, Any]:
    """Normalize arbitrary output into a JSON-like dictionary.

    This function is intentionally permissive because it is used at the boundary
    between tools, agents, systems and notebook renderers.  Strict validation
    belongs in tools/contracts; this helper only gives every value a predictable
    shape.
    """

    value = _jsonable(value)
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            return {"rows": value}
        return {"items": value}
    if isinstance(value, str):
        return {"value": value}
    if value is None:
        return {}
    return {"value": value}


def final_answer(value: Any = None, *, schema: OutputSchema | Mapping[str, Any] | None = None, text: str | None = None) -> dict[str, Any]:
    """Return the user-facing final answer dictionary.

    ``value`` should usually be the business payload (``RunResult.data`` or a
    tool output).  Runtime metadata, tool events, usage, validation and lineage
    stay in the ``RunResult`` envelope.
    """

    schema_obj = OutputSchema.coerce(schema)
    payload = normalize_output(value)
    if schema_obj is not None:
        return schema_obj.project(payload)
    if payload:
        return payload
    clean_text = str(text or "").strip()
    return {"text": clean_text} if clean_text else {}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    return value


def _extract_rows(payload: dict[str, Any]) -> list[Any]:
    for key in ("rows", "items", "records", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    if payload:
        return [payload]
    return []


def _lookup_field(source: dict[str, Any], field: str) -> tuple[bool, Any]:
    if field in source:
        return True, source[field]
    # Common nested shapes used by existing tools and graph adapters.
    for parent in ("fields", "data", "last", "summary"):
        child = source.get(parent)
        if isinstance(child, Mapping) and field in child:
            return True, child[field]
    return False, None


__all__ = [
    "FINAL_ANSWER_SCHEMA_VERSION",
    "OutputSchema",
    "final_answer",
    "normalize_output",
    "output_schema",
]
