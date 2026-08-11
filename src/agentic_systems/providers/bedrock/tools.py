from __future__ import annotations

import ast
import dataclasses
import inspect
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Type

from pydantic import BaseModel, ConfigDict, create_model

from .models import RuntimeToolSpec, ToolEnvelope


class _ToolsMixin:
    @property
    def tools(self) -> List[RuntimeToolSpec]:
        """Registered neutral tool specs."""

        return list(self._tools.values())

    def tool(
        self,
        func: Optional[Callable[..., Any]] = None,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """
        Register a Python function as an ADA tool.

        This decorator does not depend on OpenAI Agents SDK or LangGraph.
        It stores a neutral tool spec and returns the original function.
        """

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or fn.__name__
            tool_description = description or inspect.getdoc(fn) or f"Tool {tool_name}"
            signature = inspect.signature(fn)
            input_model = self._build_input_model(tool_name, signature)
            input_schema = input_model.model_json_schema()

            # Bedrock expects object schemas for tool input.
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
    def _build_input_model(
        tool_name: str, signature: inspect.Signature
    ) -> Type[BaseModel]:
        """Create a Pydantic v2 model from a Python function signature."""

        fields: Dict[str, tuple[Any, Any]] = {}

        for param_name, param in signature.parameters.items():
            if param.kind in {
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            }:
                raise TypeError(
                    f"Tool '{tool_name}' cannot use *args or **kwargs. "
                    "Use explicit typed parameters so a JSON schema can be generated."
                )

            annotation = (
                Any if param.annotation is inspect.Signature.empty else param.annotation
            )
            default = ... if param.default is inspect.Signature.empty else param.default
            fields[param_name] = (annotation, default)

        model_name = (
            "".join(part.capitalize() for part in tool_name.split("_")) + "Input"
        )

        return create_model(
            model_name,
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            **fields,
        )

    def _select_tools(
        self, tool_names: Optional[Sequence[str]] = None
    ) -> List[RuntimeToolSpec]:
        if tool_names is None:
            return list(self._tools.values())

        missing = [name for name in tool_names if name not in self._tools]
        if missing:
            raise KeyError(f"Unknown tools requested: {missing}")

        return [self._tools[name] for name in tool_names]

    def export_tool_specs(
        self, tool_names: Optional[Sequence[str]] = None
    ) -> List[Dict[str, Any]]:
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

    def validate_tool_registry(
        self, tool_names: Optional[Sequence[str]] = None
    ) -> Dict[str, Any]:
        """Run static checks over registered tools before invoking a model."""

        issues: List[Dict[str, Any]] = []
        selected = self._select_tools(tool_names)

        for spec in selected:
            if not spec.name or not isinstance(spec.name, str):
                issues.append(
                    {"tool": spec.name, "issue": "tool_name_must_be_non_empty_string"}
                )

            if not spec.description or not spec.description.strip():
                issues.append({"tool": spec.name, "issue": "tool_description_is_empty"})

            schema = spec.input_schema or {}
            if schema.get("type") != "object":
                issues.append(
                    {"tool": spec.name, "issue": "input_schema_type_must_be_object"}
                )

            if "properties" not in schema:
                issues.append(
                    {"tool": spec.name, "issue": "input_schema_missing_properties"}
                )

            if schema.get("additionalProperties") is not False:
                issues.append(
                    {"tool": spec.name, "issue": "additionalProperties_should_be_false"}
                )

            for param_name, param in spec.signature.parameters.items():
                if param.annotation is inspect.Signature.empty:
                    issues.append(
                        {
                            "tool": spec.name,
                            "parameter": param_name,
                            "issue": "parameter_missing_type_annotation",
                        }
                    )

        return {
            "ok": not issues,
            "tool_count": len(selected),
            "tools": [spec.name for spec in selected],
            "issues": issues,
        }

    # ---------------------------------------------------------------------
    # JSON-first serialization
    # ---------------------------------------------------------------------

    @classmethod
    def to_envelope(
        cls,
        value: Any,
        *,
        tool_name: str,
        ok: bool = True,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> ToolEnvelope:
        """Normalize any supported tool return value into ToolEnvelope."""

        kind, data, meta_extra = cls._payload_parts(value)

        meta = {
            "tool_name": tool_name,
            "serializer": "BedrockRuntime.ToolEnvelope.v1",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        meta.update(meta_extra)

        if extra_meta:
            meta.update(extra_meta)

        return ToolEnvelope(
            kind=kind,
            tool_name=tool_name,
            ok=ok,
            data=data,
            meta=meta,
        )

    @classmethod
    def dumps_tool_output(
        cls,
        value: Any,
        *,
        tool_name: str,
        ok: bool = True,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Serialize a ToolEnvelope as JSON text."""

        return cls.to_envelope(
            value,
            tool_name=tool_name,
            ok=ok,
            extra_meta=extra_meta,
        ).model_dump_json()

    @staticmethod
    def _make_jsonable(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")

        if dataclasses.is_dataclass(value):
            return dataclasses.asdict(value)

        try:
            json.dumps(value, ensure_ascii=False)
            return value
        except TypeError:
            return json.loads(json.dumps(value, ensure_ascii=False, default=str))

    @staticmethod
    def _summarize_model_metadata(metadata: Any) -> Dict[str, Any]:
        """
        Return a compact Bedrock model metadata summary.

        This is useful when notebook output will be copied into docs/tickets.
        `model_availability(full_metadata=True)` remains the default for dev.
        """

        safe = _ToolsMixin._make_jsonable(metadata)
        details = safe.get("modelDetails") if isinstance(safe, dict) else None
        if not isinstance(details, dict):
            details = safe if isinstance(safe, dict) else {}

        lifecycle = details.get("modelLifecycle")
        if not isinstance(lifecycle, dict):
            lifecycle = {}

        return {
            "modelDetails": {
                "modelId": details.get("modelId") or details.get("foundationModelId"),
                "modelName": details.get("modelName"),
                "providerName": details.get("providerName"),
                "inputModalities": details.get("inputModalities"),
                "outputModalities": details.get("outputModalities"),
                "responseStreamingSupported": details.get("responseStreamingSupported"),
                "inferenceTypesSupported": details.get("inferenceTypesSupported"),
                "modelLifecycle": {
                    key: value
                    for key, value in lifecycle.items()
                    if key in {"status", "startOfLifeTime", "endOfLifeTime"}
                },
            }
        }

    @classmethod
    def _payload_parts(cls, value: Any) -> tuple[str, Dict[str, Any], Dict[str, Any]]:
        """
        Normalize arbitrary Python/Pydantic values into a dict payload.

        Contract: ToolEnvelope.data is always ``Dict[str, Any]``.
        - dict / Pydantic / dataclass mappings keep their field names.
        - list is wrapped as {"items": [...]}.
        - text is wrapped as {"text": "..."}.
        - number/bool are wrapped as {"value": ...}.
        - None becomes an empty dict with wrapper metadata.
        - unsupported values are represented as {"repr": "..."}.
        """

        if isinstance(value, BaseModel):
            data = cls._make_jsonable(value.model_dump(mode="json"))
            if not isinstance(data, dict):
                data = {"value": data}
            return (
                "pydantic",
                data,
                {"pydantic_model": value.__class__.__name__},
            )

        if dataclasses.is_dataclass(value):
            data = cls._make_jsonable(dataclasses.asdict(value))
            if not isinstance(data, dict):
                data = {"value": data}
            return (
                "dataclass",
                data,
                {"python_type": value.__class__.__name__},
            )

        if isinstance(value, dict):
            data = cls._make_jsonable(value)
            if not isinstance(data, dict):
                data = {"value": data}
            return "object", data, {}

        if isinstance(value, list):
            return (
                "list",
                {"items": cls._make_jsonable(value)},
                {"length": len(value), "wrapper_key": "items"},
            )

        if isinstance(value, str):
            return (
                "text",
                {"text": value},
                {"length": len(value), "wrapper_key": "text"},
            )

        if isinstance(value, bool):
            return "boolean", {"value": value}, {"wrapper_key": "value"}

        if value is None:
            return "null", {}, {"wrapper_key": None}

        if isinstance(value, (int, float)):
            return "number", {"value": value}, {"wrapper_key": "value"}

        return (
            "repr",
            {"repr": repr(value)},
            {"python_type": type(value).__name__, "wrapper_key": "repr"},
        )

    @classmethod
    def parse_tool_output(cls, raw: Any) -> Dict[str, Any]:
        """
        Parse tool output returned by a framework bridge.

        OpenAI Agents SDK tool outputs are text, so this method accepts JSON text,
        Python literal text, dictionaries, or arbitrary values.
        """

        if isinstance(raw, ToolEnvelope):
            return raw.model_dump(mode="json")

        if isinstance(raw, dict):
            # If a bridge gives us a full ToolEnvelope-like dict, preserve it but
            # repair internal/non-canonical payloads where data was not a dict.
            required = {"kind", "tool_name", "ok", "data"}
            if required.issubset(raw):
                parsed = dict(raw)
                if not isinstance(parsed.get("data"), dict):
                    repaired = cls.to_envelope(
                        parsed.get("data"),
                        tool_name=str(parsed.get("tool_name") or "unknown"),
                        ok=bool(parsed.get("ok", True)),
                        extra_meta={"repaired_internal_non_dict_data": True},
                    ).model_dump(mode="json")
                    parsed["data"] = repaired["data"]
                    parsed["meta"] = {
                        **repaired.get("meta", {}),
                        **(parsed.get("meta") or {}),
                    }
                return parsed

            # A plain dict is a normal successful payload, not an envelope.
            return cls.to_envelope(raw, tool_name="unknown").model_dump(mode="json")

        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
                return cls.to_envelope(
                    parsed,
                    tool_name="unknown",
                    extra_meta={"parsed_via": "json_non_object"},
                ).model_dump(mode="json")
            except Exception:
                pass

            try:
                parsed = ast.literal_eval(raw)
                return cls.to_envelope(
                    parsed,
                    tool_name="unknown",
                    extra_meta={"parsed_via": "literal_eval"},
                ).model_dump(mode="json")
            except Exception:
                return cls.to_envelope(
                    raw,
                    tool_name="unknown",
                    extra_meta={"parsed_via": "raw_text"},
                ).model_dump(mode="json")

        return cls.to_envelope(
            raw,
            tool_name="unknown",
            extra_meta={"parsed_via": "fallback"},
        ).model_dump(mode="json")

    @classmethod
    def parse_framework_tool_output(
        cls,
        raw: Any,
        *,
        expected_tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Strictly parse a tool output produced by an external framework bridge.

        This method is intentionally stricter than parse_tool_output(). A bridge
        that claims to execute ADA tools must return a valid ToolEnvelope. Raw
        text, arbitrary dictionaries, malformed JSON, or a mismatched tool name
        are converted into ok=False contract errors.
        """

        tool_name = expected_tool_name or "unknown"

        if isinstance(raw, ToolEnvelope):
            envelope = raw

        else:
            parsed: Any = None

            if isinstance(raw, dict):
                parsed = raw

            elif isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                except Exception:
                    return cls.to_envelope(
                        {
                            "error_type": "NonEnvelopeToolOutput",
                            "message": (
                                "Framework returned raw text where "
                                "BedrockRuntime expected a ToolEnvelope JSON string."
                            ),
                            "raw_output_preview": raw[:500],
                        },
                        tool_name=tool_name,
                        ok=False,
                        extra_meta={
                            "bridge_contract": "ToolEnvelopeRequired",
                            "raw_type": "str",
                        },
                    ).model_dump(mode="json")

            else:
                return cls.to_envelope(
                    {
                        "error_type": "NonEnvelopeToolOutput",
                        "message": "Framework returned a non-envelope tool output.",
                        "raw_type": type(raw).__name__,
                    },
                    tool_name=tool_name,
                    ok=False,
                    extra_meta={"bridge_contract": "ToolEnvelopeRequired"},
                ).model_dump(mode="json")

            try:
                envelope = ToolEnvelope.model_validate(parsed)
            except Exception as exc:
                return cls.to_envelope(
                    {
                        "error_type": "MalformedToolEnvelope",
                        "message": str(exc),
                        "raw_output": cls._make_jsonable(parsed),
                    },
                    tool_name=tool_name,
                    ok=False,
                    extra_meta={"bridge_contract": "ToolEnvelopeRequired"},
                ).model_dump(mode="json")

        if expected_tool_name and envelope.tool_name not in {
            expected_tool_name,
            "unknown",
        }:
            return cls.to_envelope(
                {
                    "error_type": "ToolNameMismatch",
                    "message": "Tool output envelope belongs to a different tool.",
                    "expected_tool_name": expected_tool_name,
                    "actual_tool_name": envelope.tool_name,
                    "raw_envelope": envelope.model_dump(mode="json"),
                },
                tool_name=expected_tool_name,
                ok=False,
                extra_meta={"bridge_contract": "ToolEnvelopeRequired"},
            ).model_dump(mode="json")

        return envelope.model_dump(mode="json")

    # ---------------------------------------------------------------------
    # Tool execution
    # ---------------------------------------------------------------------

    def execute_tool(
        self, tool_name: str, tool_input: Optional[Dict[str, Any]] = None
    ) -> ToolEnvelope:
        """
        Execute one registered tool locally and return a ToolEnvelope.

        This is used by Bedrock runtime, OpenAI Agents SDK wrappers,
        and any custom framework that wants deterministic local tool execution.
        """

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
                    f"Tool '{tool_name}' is async. "
                    "This light runtime supports sync tool execution in run_direct()."
                )

            value = spec.func(**clean_input)

            return self.to_envelope(
                value,
                tool_name=tool_name,
                ok=True,
                extra_meta={"validated_input": clean_input},
            )

        except Exception as exc:
            return self.to_envelope(
                {
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                },
                tool_name=tool_name,
                ok=False,
                extra_meta={"failed_input": tool_input},
            )

    # ---------------------------------------------------------------------
    # Bedrock Converse
    # ---------------------------------------------------------------------
