"""Provider-neutral runtime registry primitives.

This module is intentionally free of cloud/framework dependencies.  It gives the
Agentic Systems core a place to store tool metadata even when optional providers
such as Bedrock Runtime are not installed or not selected.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Sequence, Type

from pydantic import BaseModel, ConfigDict, Field, create_model

from agentic_systems.defaults import DEFAULT_AWS_REGION


class ToolEnvelope(BaseModel):
    """Canonical JSON-first output returned by provider-neutral tools."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    tool_name: str
    ok: bool = True
    data: Dict[str, Any]
    meta: Dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeToolSpec:
    """Neutral tool metadata shared by providers and integrations."""

    name: str
    description: str
    func: Callable[..., Any]
    signature: inspect.Signature
    input_model: Type[BaseModel]
    input_schema: Dict[str, Any]
    is_async: bool = False


class ToolRegistryRuntime:
    """Small local registry used by the core before a provider is selected.

    It mirrors the registry surface required by ``AgenticSystem`` without
    importing boto3, LangGraph, OpenAI Agents SDK, or any other optional runtime.
    Provider-specific runtimes can be hydrated from ``self._tools`` later.
    """

    def __init__(
        self,
        *,
        model_id: str,
        region_name: str | None = None,
        max_tokens_default: int = 800,
        temperature_default: float = 0.0,
    ) -> None:
        self.model_id = model_id
        self.region_name = region_name or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or DEFAULT_AWS_REGION
        self.max_tokens_default = int(max_tokens_default)
        self.temperature_default = float(temperature_default)
        self._tools: dict[str, RuntimeToolSpec] = {}

    @property
    def tools(self) -> list[RuntimeToolSpec]:
        """Registered neutral tool specs."""

        return list(self._tools.values())

    def tool(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
    ):
        """Register a Python function as a provider-neutral tool."""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or fn.__name__
            tool_description = description or inspect.getdoc(fn) or f"Tool {tool_name}"
            signature = inspect.signature(fn)
            input_model = self._build_input_model(tool_name, signature)
            input_schema = input_model.model_json_schema()
            input_schema.setdefault("type", "object")
            input_schema.setdefault("properties", {})
            input_schema.setdefault("additionalProperties", False)
            self._tools[tool_name] = RuntimeToolSpec(
                name=tool_name,
                description=tool_description,
                func=fn,
                signature=signature,
                input_model=input_model,
                input_schema=input_schema,
                is_async=inspect.iscoroutinefunction(fn),
            )
            return fn

        if func is None:
            return decorator
        return decorator(func)

    @staticmethod
    def _build_input_model(tool_name: str, signature: inspect.Signature) -> Type[BaseModel]:
        fields: dict[str, tuple[Any, Any]] = {}
        for param_name, param in signature.parameters.items():
            if param.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
                raise TypeError(
                    f"Tool '{tool_name}' cannot use *args or **kwargs. "
                    "Use explicit typed parameters so a JSON schema can be generated."
                )
            annotation = Any if param.annotation is inspect.Signature.empty else param.annotation
            default = ... if param.default is inspect.Signature.empty else param.default
            fields[param_name] = (annotation, default)
        model_name = "".join(part.capitalize() for part in tool_name.split("_")) + "Input"
        return create_model(
            model_name,
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            **fields,
        )

    def _select_tools(self, tool_names: Sequence[str] | None = None) -> list[RuntimeToolSpec]:
        if tool_names is None:
            return list(self._tools.values())
        missing = [name for name in tool_names if name not in self._tools]
        if missing:
            raise KeyError(f"Unknown tools requested: {missing}")
        return [self._tools[name] for name in tool_names]

    def export_tool_specs(self, tool_names: Sequence[str] | None = None) -> list[dict[str, Any]]:
        """Return neutral, serializable tool metadata."""

        return [
            {
                "name": spec.name,
                "description": spec.description,
                "input_schema": spec.input_schema,
                "is_async": spec.is_async,
            }
            for spec in self._select_tools(tool_names)
        ]

    def print_tool_specs(self) -> None:
        print(json.dumps(self.export_tool_specs(), indent=2, ensure_ascii=False))

    def validate_tool_registry(self, tool_names: Sequence[str] | None = None) -> dict[str, Any]:
        """Run static checks over registered tools before invoking any provider."""

        issues: list[dict[str, Any]] = []
        selected = self._select_tools(tool_names)
        for spec in selected:
            if not spec.name or not isinstance(spec.name, str):
                issues.append({"tool": spec.name, "issue": "tool_name_must_be_non_empty_string"})
            if not spec.description or not spec.description.strip():
                issues.append({"tool": spec.name, "issue": "tool_description_is_empty"})
            schema = spec.input_schema or {}
            if schema.get("type") != "object":
                issues.append({"tool": spec.name, "issue": "input_schema_type_must_be_object"})
            if "properties" not in schema:
                issues.append({"tool": spec.name, "issue": "input_schema_missing_properties"})
            if schema.get("additionalProperties") is not False:
                issues.append({"tool": spec.name, "issue": "additionalProperties_should_be_false"})
            for param_name, param in spec.signature.parameters.items():
                if param.annotation is inspect.Signature.empty:
                    issues.append({
                        "tool": spec.name,
                        "parameter": param_name,
                        "issue": "parameter_missing_type_annotation",
                    })
        return {
            "ok": not issues,
            "tool_count": len(selected),
            "tools": [spec.name for spec in selected],
            "issues": issues,
        }

    @classmethod
    def to_envelope(
        cls,
        value: Any,
        *,
        tool_name: str,
        ok: bool = True,
        extra_meta: dict[str, Any] | None = None,
    ) -> ToolEnvelope:
        kind, data, meta_extra = cls._payload_parts(value)
        meta = {
            "tool_name": tool_name,
            "serializer": "AgenticSystems.ToolEnvelope.v1",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        meta.update(meta_extra)
        if extra_meta:
            meta.update(extra_meta)
        return ToolEnvelope(kind=kind, tool_name=tool_name, ok=ok, data=data, meta=meta)

    @staticmethod
    def _payload_parts(value: Any) -> tuple[str, dict[str, Any], dict[str, Any]]:
        if isinstance(value, BaseModel):
            return "pydantic", value.model_dump(mode="json"), {"model": value.__class__.__name__}
        if dataclasses.is_dataclass(value):
            return "dataclass", dataclasses.asdict(value), {"model": value.__class__.__name__}
        if isinstance(value, dict):
            return "object", _jsonable(value), {}
        if isinstance(value, list):
            return "list", {"items": _jsonable(value)}, {}
        if isinstance(value, str):
            return "text", {"text": value}, {}
        if isinstance(value, bool):
            return "boolean", {"value": value}, {}
        if isinstance(value, (int, float)) or value is None:
            return "number" if value is not None else "null", {"value": value}, {}
        return "repr", {"repr": repr(value)}, {"python_type": type(value).__name__}

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any] | None = None) -> ToolEnvelope:
        """Execute one registered tool locally and return a ToolEnvelope."""

        tool_input = tool_input or {}
        try:
            spec = self._tools[tool_name]
        except KeyError:
            return self.to_envelope(
                {
                    "error_type": "UnknownToolError",
                    "message": f"Tool '{tool_name}' is not registered.",
                    "available_tools": sorted(self._tools),
                },
                tool_name=tool_name,
                ok=False,
            )
        try:
            validated = spec.input_model.model_validate(tool_input)
            clean_input = validated.model_dump()
            if spec.is_async:
                raise RuntimeError(
                    f"Tool '{tool_name}' is async. Use an async-capable provider/runtime for this tool."
                )
            value = spec.func(**clean_input)
            return self.to_envelope(value, tool_name=tool_name, ok=True, extra_meta={"validated_input": clean_input})
        except Exception as exc:  # noqa: BLE001 - structured local failure.
            return self.to_envelope(
                {"error_type": type(exc).__name__, "message": str(exc)},
                tool_name=tool_name,
                ok=False,
                extra_meta={"failed_input": tool_input},
            )


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    return value


__all__ = ["RuntimeToolSpec", "ToolEnvelope", "ToolRegistryRuntime"]
