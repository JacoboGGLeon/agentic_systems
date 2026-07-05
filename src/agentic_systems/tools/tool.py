"""Public Tool API.

A :class:`Tool` is the smallest executable unit in Agentic Systems. It wraps a
Python callable, validates optional Pydantic input/output contracts, and always
returns a normalized :class:`~agentic_systems.results.RunResult` from ``run``.
"""

from __future__ import annotations

import dataclasses
import inspect
import uuid
from collections.abc import Callable
from typing import Any, get_type_hints

from pydantic import BaseModel

from ..contracts import ValidationResult
from ..engines.names import PYTHON_RUNTIME_ENGINE
from ..errors import ToolContractError
from .compat import ToolEvent, assert_dict_tool_output


class Tool:
    """Validated unit of computation.

    Parameters
    ----------
    name:
        Public tool name. It must be non-empty.
    description:
        Human-readable description. When omitted, the wrapped function's
        docstring is used.
    function:
        Callable executed by :meth:`run`.
    input_schema:
        Optional Pydantic v2 model used to validate tool input.
    output_schema:
        Optional Pydantic v2 model used to validate tool output.
    metadata:
        JSON-like user metadata.
    strict:
        When ``True``, outputs must be dictionaries unless an ``output_schema``
        is provided. When ``False``, common scalar/list/model outputs are
        normalized into dictionaries.
    """

    def __init__(
        self,
        function: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        input_schema: type[BaseModel] | None = None,
        output_schema: type[BaseModel] | None = None,
        input_model: type[BaseModel] | None = None,
        output_model: type[BaseModel] | None = None,
        input: type[BaseModel] | None = None,  # noqa: A002 - public ergonomic alias.
        output: type[BaseModel] | None = None,
        metadata: dict[str, Any] | None = None,
        strict: bool = True,
    ) -> None:
        if function is not None and not callable(function):
            raise TypeError("Tool function must be callable.")
        inferred_name = getattr(function, "__name__", None) if function is not None else None
        self.name = (name or inferred_name or "").strip() if isinstance(name or inferred_name, str) else ""
        if not self.name:
            raise ValueError("Tool name must be non-empty. Pass name=... when no function is provided.")
        self.function = function
        self.description, self.description_source = _resolve_description(description, function)
        self.input_schema = _resolve_schema_alias(
            "input",
            input_schema=input_schema,
            input_model=input_model,
            input=input,
        )
        self.output_schema = _resolve_schema_alias(
            "output",
            output_schema=output_schema,
            output_model=output_model,
            output=output,
        )
        self.metadata = dict(metadata or {})
        self.strict = bool(strict)

    def info(self) -> dict[str, Any]:
        """Return a JSON-like description of this tool."""

        return {
            "name": self.name,
            "description": self.description,
            "description_source": self.description_source,
            "strict": self.strict,
            "function": getattr(self.function, "__name__", None),
            "input_schema": _schema_info(self.input_schema),
            "output_schema": _schema_info(self.output_schema),
            "metadata": self.metadata,
        }

    def describe(self) -> str:
        """Return a short human-readable description."""

        suffix = f": {self.description}" if self.description else ""
        return f"Tool `{self.name}`{suffix}"

    def check(self) -> ValidationResult:
        """Validate local configuration and strict type-hint expectations."""

        result = ValidationResult(ok=True)
        if self.function is None:
            result.add("missing_function", f"Tool '{self.name}' has no callable function.", path="function")
            return result

        if self.strict:
            signature = inspect.signature(self.function)
            # When an explicit Pydantic input_schema exists, it is the source of
            # truth for input validation. Do not force duplicate function
            # parameter annotations; this keeps schema-backed tools ergonomic
            # while preserving strict return validation.
            if self.input_schema is None:
                for param_name, param in signature.parameters.items():
                    if param.annotation is inspect.Signature.empty:
                        result.add(
                            "missing_parameter_annotation",
                            f"Tool '{self.name}' parameter '{param_name}' is missing a type annotation.",
                            path=f"function.parameters.{param_name}",
                        )
            if not self.output_schema and not _return_annotation_is_dict(self.function):
                result.add(
                    "return_annotation_must_be_dict",
                    f"Tool '{self.name}' must be annotated as returning dict when no output_schema is configured.",
                    path="function.return_annotation",
                )
        return result

    def run(self, input_payload: Any = None, context: Any = None):
        """Execute the tool and return a normalized ``RunResult``.

        ``context`` is accepted for future runtime integration and is stored in
        the result metadata when provided.
        """

        from ..results import RunResult

        event_id = f"tool-{uuid.uuid4().hex}"
        try:
            self.check().raise_if_failed()
            payload = self._validate_input(input_payload)
            raw_output = self._call(payload)
            output = self._validate_output(raw_output)
            event = ToolEvent(id=event_id, name=self.name, input=_payload_to_dict(payload), output={"data": output}, ok=True)
            return RunResult(
                text="",
                data=output,
                ok=True,
                tool_events=[event],
                usage={"requests": 1},
                engine=PYTHON_RUNTIME_ENGINE,
                mode="tool",
                meta=_result_meta(context, input_payload),
            )
        except Exception as exc:  # noqa: BLE001 - tool runs return structured failures.
            error = {"error_type": type(exc).__name__, "message": str(exc)}
            event = ToolEvent(id=event_id, name=self.name, input=_payload_to_dict(input_payload), output={"data": error}, ok=False, error=error)
            return RunResult(
                text=str(exc),
                data=error,
                ok=False,
                tool_events=[event],
                usage={"requests": 1},
                engine=PYTHON_RUNTIME_ENGINE,
                mode="tool",
                meta=_result_meta(context, input_payload),
            )

    def _validate_input(self, input_payload: Any) -> Any:
        payload = {} if input_payload is None else input_payload
        if self.input_schema is None:
            return payload
        if isinstance(payload, self.input_schema):
            return payload
        return self.input_schema.model_validate(payload)

    def _validate_output(self, value: Any) -> dict[str, Any]:
        if self.output_schema is not None:
            if isinstance(value, self.output_schema):
                model = value
            else:
                model = self.output_schema.model_validate(value)
            return model.model_dump(mode="json")
        if self.strict:
            try:
                return assert_dict_tool_output(self.name, value)
            except TypeError as exc:
                raise ToolContractError(str(exc)) from exc
        return _normalize_to_dict(value)

    def _call(self, payload: Any) -> Any:
        if self.function is None:
            raise ToolContractError(f"Tool '{self.name}' has no callable function.")  # pragma: no cover
        signature = inspect.signature(self.function)
        parameters = list(signature.parameters.values())
        if not parameters:
            return self.function()
        if isinstance(payload, BaseModel):
            if len(parameters) == 1:
                signature.bind(payload)
                return self.function(payload)
            payload = payload.model_dump(mode="json")
        if isinstance(payload, dict):
            if len(parameters) == 1 and parameters[0].name not in payload:
                signature.bind(payload)
                return self.function(payload)
            signature.bind(**payload)
            return self.function(**payload)
        if len(parameters) == 1:
            signature.bind(payload)
            return self.function(payload)
        raise TypeError(f"Tool '{self.name}' expected dict input for parameters {[param.name for param in parameters]}.")


CheckResult = ValidationResult


def _function_doc(function: Callable[..., Any] | None) -> str | None:
    return inspect.getdoc(function) if function is not None else None


def _resolve_description(description: str | None, function: Callable[..., Any] | None) -> tuple[str, str]:
    """Resolve description and expose where it came from for tool catalogs."""

    if description is not None and description.strip():
        return description.strip(), "decorator"
    doc = _function_doc(function)
    if doc and doc.strip():
        return doc.strip(), "docstring"
    return "", "none"


def _resolve_schema_alias(kind: str, **values: Any) -> type[BaseModel] | None:
    provided = [(name, value) for name, value in values.items() if value is not None]
    if not provided:
        return None
    first_name, first_value = provided[0]
    for name, value in provided[1:]:
        if value is not first_value:
            raise ValueError(f"Conflicting {kind} schema aliases: {first_name} and {name}.")
    return _ensure_model_schema(first_value, f"{kind}_schema")


def _ensure_model_schema(schema: Any, field_name: str) -> type[BaseModel] | None:
    if schema is None:
        return None
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        return schema
    raise TypeError(f"{field_name} must be a pydantic BaseModel subclass.")


def _schema_info(schema: type[BaseModel] | None) -> dict[str, Any] | None:
    if schema is None:
        return None
    return {"name": schema.__name__, "json_schema": schema.model_json_schema()}


def _return_annotation_is_dict(function: Callable[..., Any]) -> bool:
    try:
        annotation = get_type_hints(function).get("return", inspect.signature(function).return_annotation)
    except Exception:
        annotation = inspect.signature(function).return_annotation
    if annotation is inspect.Signature.empty:
        return False
    if annotation in {dict, dict[str, Any]}:
        return True
    return getattr(annotation, "__origin__", None) is dict


def _function_param_annotation(function: Callable[..., Any], param_name: str) -> Any:
    try:
        return get_type_hints(function).get(param_name, inspect.signature(function).parameters[param_name].annotation)
    except Exception:
        return inspect.signature(function).parameters[param_name].annotation


def _normalize_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {"items": value}
    if isinstance(value, str):
        return {"text": value}
    if value is None:
        return {"ok": True}
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    return {"value": value}


def _payload_to_dict(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    return {"value": payload}


def _result_meta(context: Any, input_payload: Any = None) -> dict[str, Any]:
    tool_input = _payload_to_dict(input_payload)
    meta = {"tool_name": "", "input": tool_input, "tool_input": tool_input}
    if context is not None:
        meta["context_type"] = type(context).__name__
        context_payload = _payload_to_dict(context)
        meta["context"] = context_payload
        if isinstance(context_payload, dict) and context_payload.get("user_prompt"):
            meta["input"] = context_payload["user_prompt"]
    return meta
