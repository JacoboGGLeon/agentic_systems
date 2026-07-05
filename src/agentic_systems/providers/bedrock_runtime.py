"""
Internal Bedrock runtime for Agentic Systems 1.0.

This module contains the reusable Bedrock Converse implementation used by
`agentic_systems.AgenticSystem`:

1. Python-runtime runtime: Bedrock Converse + local tool loop.
2. OpenAI Agents SDK bridge: optional ModelProvider backed by Bedrock.
3. LangGraph utility support used by the higher-level Agent API.

No business tools live in this file.

Tool output contract
--------------------
Runtime tools are normalized into ToolEnvelope(kind, tool_name, ok, data, meta),
where data is always a dictionary. The public Agentic Systems API enforces
business tools as `dict`-returning functions before they reach this runtime.
"""

from __future__ import annotations

import ast
import asyncio
import concurrent.futures
import dataclasses
import hashlib
import inspect
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Sequence, Type

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, ConfigDict, Field, create_model


__version__ = "1.0.0"


class ToolEnvelope(BaseModel):
    """Canonical JSON-first output returned by every registered tool."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(
        ...,
        description="Logical payload kind before dict wrapping: object, list, text, number, boolean, null, pydantic, dataclass, repr.",
    )
    tool_name: str
    ok: bool = True
    data: Dict[str, Any]
    meta: Dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeToolSpec:
    """Neutral tool metadata used by all runtimes/bridges."""

    name: str
    description: str
    func: Callable[..., Any]
    signature: inspect.Signature
    input_model: Type[BaseModel]
    input_schema: Dict[str, Any]
    is_async: bool = False


class RuntimeToolCallRecord(BaseModel):
    """Serializable trace record for one tool invocation."""

    model_config = ConfigDict(extra="forbid")

    tool_use_id: str
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Dict[str, Any]
    ok: bool
    meta: Dict[str, Any] = Field(default_factory=dict)


class BedrockRunResult(BaseModel):
    """Serializable result for Python-runtime and LangGraph runs."""

    model_config = ConfigDict(extra="forbid")

    final_text: str
    messages: List[Dict[str, Any]]
    tool_calls: List[RuntimeToolCallRecord] = Field(default_factory=list)
    raw_responses: List[Dict[str, Any]] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    def compact_trace(self) -> Dict[str, Any]:
        """
        Small trace intended for notebook display and CI summaries.

        Failure semantics are intentionally explicit:

        - ``tools``: every tool-call event.
        - ``failed_tool_events``: every historical failed call.
        - ``recovered_tool_errors``: failed calls followed later by a successful
          call to the same tool in the same run.
        - ``unresolved_failed_tools``: failed calls that were not recovered.
        - ``run_ok``: true when there are no unresolved failed tools and the
          model produced a final text.

        This avoids the ambiguity of a plain ``failed_tools`` field: a run may
        contain a failed tool event and still be valid if the runtime repaired it.
        """

        usage_totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "requests": len(self.raw_responses),
        }

        for raw in self.raw_responses:
            usage = raw.get("usage", {}) or {}
            usage_totals["input_tokens"] += int(usage.get("inputTokens", 0) or 0)
            usage_totals["output_tokens"] += int(usage.get("outputTokens", 0) or 0)
            usage_totals["total_tokens"] += int(usage.get("totalTokens", 0) or 0)

        tool_summaries: List[Dict[str, Any]] = []

        for idx, call in enumerate(self.tool_calls):
            output_data = call.tool_output.get("data")
            error_type = (
                output_data.get("error_type")
                if isinstance(output_data, dict)
                else None
            )

            tool_summaries.append(
                {
                    "index": idx,
                    "tool_use_id": call.tool_use_id,
                    "tool_name": call.tool_name,
                    "ok": call.ok,
                    "input": call.tool_input,
                    "output_kind": call.tool_output.get("kind"),
                    "output_data": output_data,
                    "error_type": error_type,
                }
            )

        failed_tool_events = [
            tool for tool in tool_summaries
            if not tool.get("ok")
        ]

        recovered_tool_errors: List[Dict[str, Any]] = []
        unresolved_failed_tools: List[Dict[str, Any]] = []

        for failed in failed_tool_events:
            failed_index = int(failed.get("index", -1))
            failed_name = failed.get("tool_name")

            recovery = next(
                (
                    tool for tool in tool_summaries
                    if int(tool.get("index", -1)) > failed_index
                    and tool.get("tool_name") == failed_name
                    and tool.get("ok") is True
                ),
                None,
            )

            if recovery:
                recovered_tool_errors.append(
                    {
                        **failed,
                        "recovered": True,
                        "recovered_by_tool_use_id": recovery.get("tool_use_id"),
                        "recovered_by_index": recovery.get("index"),
                    }
                )
            else:
                unresolved_failed_tools.append(
                    {
                        **failed,
                        "recovered": False,
                    }
                )

        stop_reasons = [
            raw.get("stop_reason")
            for raw in self.raw_responses
            if raw.get("stop_reason")
        ]

        run_ok = bool(self.final_text) and len(unresolved_failed_tools) == 0

        return {
            "trace_schema_version": "ada.compact_trace.v3",
            "run_ok": run_ok,
            "final_text": self.final_text,
            "turns": len(self.raw_responses),
            "message_count": len(self.messages),
            "tool_call_count": len(self.tool_calls),
            "successful_tool_count": len([tool for tool in tool_summaries if tool.get("ok")]),
            "failed_tool_event_count": len(failed_tool_events),
            "recovered_tool_error_count": len(recovered_tool_errors),
            "unresolved_failed_tool_count": len(unresolved_failed_tools),

            # Full compact records.
            "tools": tool_summaries,
            "failed_tool_events": failed_tool_events,
            "recovered_tool_errors": recovered_tool_errors,
            "unresolved_failed_tools": unresolved_failed_tools,


            "usage_totals": usage_totals,
            "stop_reasons_available": True,
            "stop_reasons": stop_reasons,
        }

    def trace(self, *, mode: str = "compact") -> Dict[str, Any]:
        """Return either a compact trace or the full Bedrock conversation trace."""

        if mode == "compact":
            return self.compact_trace()
        if mode == "full":
            return self.to_dict()
        raise ValueError("mode must be 'compact' or 'full'")


class BedrockRuntime:
    """
    Bedrock-first runtime with a small public API.

    Public surface:
        - @runtime.tool
        - runtime.run_direct(...)
        - runtime.create_openai_agent(...)
        - runtime.run_openai_agent(...)
        - runtime.as_langgraph_node(...)
    """

    def __init__(
        self,
        *,
        model_id: str,
        region_name: Optional[str] = None,
        max_tokens_default: int = 800,
        temperature_default: float = 0.0,
        logger_name: str = "agentic_systems",
        disable_openai_runtime_tracing: bool = True,
    ) -> None:
        self.model_id = model_id
        self.max_tokens_default = max_tokens_default
        self.temperature_default = temperature_default
        self.disable_openai_runtime_tracing = disable_openai_runtime_tracing

        self.logger = logging.getLogger(logger_name)
        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

        self.session = boto3.Session(region_name=region_name)
        self.region_name = (
            self.session.region_name
            or os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "us-east-1"
        )

        self.runtime = boto3.client("bedrock-runtime", region_name=self.region_name)
        self.bedrock = boto3.client("bedrock", region_name=self.region_name)
        self.sts = boto3.client("sts", region_name=self.region_name)

        self._tools: Dict[str, RuntimeToolSpec] = {}

    # ---------------------------------------------------------------------
    # AWS helpers
    # ---------------------------------------------------------------------

    def whoami(self, *, mask: bool = False) -> Dict[str, Any]:
        """Return the active AWS identity and Bedrock region.

        Set ``mask=True`` when the notebook output may be copied to docs, tickets,
        or commits. Set ``mask=False`` when debugging IAM/role assumptions.
        """

        identity = self.sts.get_caller_identity()
        result = {
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
            "user_id": identity.get("UserId"),
            "region": self.region_name,
            "model_id": self.model_id,
        }
        return self.redact_aws_identity(result) if mask else result

    @staticmethod
    def _mask_middle(value: Any, *, keep_start: int = 6, keep_end: int = 4) -> Any:
        """Mask long identifiers while preserving enough shape for debugging."""

        if value is None:
            return value

        text = str(value)
        if len(text) <= keep_start + keep_end:
            return "*" * len(text)

        return f"{text[:keep_start]}...{text[-keep_end:]}"

    @classmethod
    def redact_aws_identity(cls, identity: Dict[str, Any]) -> Dict[str, Any]:
        """Return a safe-to-share version of AWS identity metadata."""

        redacted = dict(identity)

        account = redacted.get("account")
        if account:
            account_text = str(account)
            redacted["account"] = (
                f"{account_text[:6]}******"
                if len(account_text) >= 6
                else "***"
            )

        user_id = redacted.get("user_id")
        if user_id:
            redacted["user_id"] = cls._mask_middle(user_id)

        arn = redacted.get("arn")
        if arn:
            arn_text = str(arn)
            account_raw = str(identity.get("account") or "")
            if account_raw:
                arn_text = arn_text.replace(account_raw, "****")
            # Keep role family visible but avoid leaking the full role/session path.
            parts = arn_text.split("/")
            if len(parts) >= 3:
                arn_text = "/".join(parts[:2] + [cls._mask_middle(parts[-1])])
            redacted["arn"] = arn_text

        redacted["redacted"] = True
        return redacted

    def model_availability(
        self,
        model_id: Optional[str] = None,
        *,
        full_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Best-effort Bedrock model metadata check.

        Important:
        - This is not a real inference smoke test.
        - Some AWS roles can invoke a model but cannot call Bedrock management APIs.
        - We intentionally avoid get_foundation_model_availability because many
          boto3/botocore Bedrock clients do not expose that method.
        - The strongest runtime check is still a real bedrock-runtime.converse call.
        - Return value is JSON-safe; boto3 may include datetime objects.

        Parameters:
        - full_metadata=True returns the full JSON-safe boto3 metadata payload.
        - full_metadata=False returns a compact, documentation-safe summary.
        """

        selected_model = model_id or self.model_id

        def availability_payload(raw: Any) -> Any:
            safe = self._make_jsonable(raw)
            if full_metadata:
                return safe
            return self._summarize_model_metadata(safe)

        get_error: Optional[Dict[str, Any]] = None

        # Preferred metadata check: exact model lookup.
        if hasattr(self.bedrock, "get_foundation_model"):
            try:
                out = self.bedrock.get_foundation_model(
                    modelIdentifier=selected_model
                )
                return {
                    "model_id": selected_model,
                    "ok": True,
                    "check": "get_foundation_model",
                    "full_metadata": full_metadata,
                    "availability": availability_payload(out),
                    "note": (
                        "Metadata check succeeded. A real Converse call is still "
                        "the strongest runtime/invoke validation."
                    ),
                }
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code")
                message = exc.response.get("Error", {}).get("Message", str(exc))

                if code in {
                    "AccessDeniedException",
                    "UnauthorizedOperation",
                    "AccessDenied",
                }:
                    return {
                        "model_id": selected_model,
                        "ok": None,
                        "check": "get_foundation_model",
                        "full_metadata": full_metadata,
                        "availability": "unknown_due_to_iam",
                        "error_code": code,
                        "message": (
                            "IAM denied Bedrock model metadata check. "
                            "Inference may still work if bedrock-runtime:Converse "
                            "is allowed."
                        ),
                        "raw_message": message,
                    }

                get_error = {
                    "error_code": code,
                    "message": message,
                }
        else:
            get_error = {
                "error_code": "MethodNotAvailable",
                "message": (
                    "This boto3/botocore Bedrock client has no "
                    "get_foundation_model method."
                ),
            }

        # Fallback metadata check: list models in region and look for a match.
        if hasattr(self.bedrock, "list_foundation_models"):
            try:
                out = self.bedrock.list_foundation_models()
                summaries = out.get("modelSummaries", [])

                matches = []
                for model in summaries:
                    candidates = {
                        model.get("modelId"),
                        model.get("foundationModelId"),
                        model.get("modelArn"),
                    }
                    if selected_model in candidates:
                        matches.append(model)

                safe_matches = self._make_jsonable(matches)
                if not full_metadata:
                    safe_matches = [
                        self._summarize_model_metadata(match)
                        for match in safe_matches
                    ]

                return {
                    "model_id": selected_model,
                    "ok": bool(matches),
                    "check": "list_foundation_models",
                    "full_metadata": full_metadata,
                    "matched": safe_matches,
                    "model_count": len(summaries),
                    "previous_get_foundation_model_error": get_error,
                    "note": (
                        "list_foundation_models validates metadata visibility in "
                        "this region, not runtime invoke entitlement. Use "
                        "run_direct for the real Converse smoke test."
                    ),
                }
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code")
                message = exc.response.get("Error", {}).get("Message", str(exc))

                return {
                    "model_id": selected_model,
                    "ok": None,
                    "check": "list_foundation_models",
                    "full_metadata": full_metadata,
                    "availability": "unknown_due_to_error",
                    "error_code": code,
                    "message": message,
                    "previous_get_foundation_model_error": get_error,
                }

        return {
            "model_id": selected_model,
            "ok": None,
            "check": "none",
            "full_metadata": full_metadata,
            "availability": "unknown_due_to_client_capability",
            "message": (
                "This boto3/botocore Bedrock client exposes neither "
                "get_foundation_model nor list_foundation_models."
            ),
            "previous_get_foundation_model_error": get_error,
        }

    # ---------------------------------------------------------------------
    # Tool registry
    # ---------------------------------------------------------------------

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
    def _build_input_model(tool_name: str, signature: inspect.Signature) -> Type[BaseModel]:
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

            annotation = Any if param.annotation is inspect.Signature.empty else param.annotation
            default = ... if param.default is inspect.Signature.empty else param.default
            fields[param_name] = (annotation, default)

        model_name = "".join(part.capitalize() for part in tool_name.split("_")) + "Input"

        return create_model(
            model_name,
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            **fields,
        )

    def _select_tools(self, tool_names: Optional[Sequence[str]] = None) -> List[RuntimeToolSpec]:
        if tool_names is None:
            return list(self._tools.values())

        missing = [name for name in tool_names if name not in self._tools]
        if missing:
            raise KeyError(f"Unknown tools requested: {missing}")

        return [self._tools[name] for name in tool_names]

    def export_tool_specs(self, tool_names: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
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

    def validate_tool_registry(self, tool_names: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        """Run static checks over registered tools before invoking a model."""

        issues: List[Dict[str, Any]] = []
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

        safe = BedrockRuntime._make_jsonable(metadata)
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
            return "list", {"items": cls._make_jsonable(value)}, {"length": len(value), "wrapper_key": "items"}

        if isinstance(value, str):
            return "text", {"text": value}, {"length": len(value), "wrapper_key": "text"}

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
                    parsed["meta"] = {**repaired.get("meta", {}), **(parsed.get("meta") or {})}
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

        if expected_tool_name and envelope.tool_name not in {expected_tool_name, "unknown"}:
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

    def execute_tool(self, tool_name: str, tool_input: Optional[Dict[str, Any]] = None) -> ToolEnvelope:
        """
        Execute one registered tool locally and return a ToolEnvelope.

        This is used by Python-runtime runtime, OpenAI Agents SDK wrappers,
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

    def converse(
        self,
        *,
        messages: List[Dict[str, Any]],
        system: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Thin wrapper around Bedrock Runtime `converse`."""

        inference_config: Dict[str, Any] = {
            "maxTokens": max_tokens or self.max_tokens_default,
            "temperature": self.temperature_default if temperature is None else temperature,
        }

        if top_p is not None:
            inference_config["topP"] = top_p

        if stop_sequences:
            inference_config["stopSequences"] = stop_sequences

        kwargs: Dict[str, Any] = {
            "modelId": model_id or self.model_id,
            "messages": messages,
            "inferenceConfig": inference_config,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["toolConfig"] = {"tools": tools}
            if tool_choice:
                kwargs["toolConfig"]["toolChoice"] = tool_choice

        started_at = time.perf_counter()
        response = self.runtime.converse(**kwargs)
        client_duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
        if isinstance(response, dict):
            response.setdefault("agentic_systems", {})["client_duration_ms"] = client_duration_ms
        return response

    @staticmethod
    def bedrock_safe_tool_name(name: str) -> str:
        """Return a Bedrock Converse-safe tool name.

        Bedrock accepts only ``[a-zA-Z0-9_-]+`` in ``toolSpec.name``. The public
        API may use namespaced tool names such as ``customer_risk.get_customer``.
        This mapper keeps the public name canonical while sending a safe alias to
        Bedrock. A short stable digest is appended only when sanitation changes
        the name enough to risk collisions.
        """

        canonical = str(name or "").strip()
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", canonical).strip("_")
        if not safe:
            safe = "tool"
        if safe != canonical:
            digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:8]
            safe = f"{safe}_{digest}"
        return safe

    def _bedrock_tool_name_maps(
        self,
        tool_names: Optional[Sequence[str]] = None,
    ) -> tuple[Dict[str, str], Dict[str, str]]:
        """Return canonical->Bedrock and Bedrock->canonical tool-name maps."""

        canonical_to_bedrock: Dict[str, str] = {}
        bedrock_to_canonical: Dict[str, str] = {}

        for spec in self._select_tools(tool_names):
            candidate = self.bedrock_safe_tool_name(spec.name)
            if candidate in bedrock_to_canonical and bedrock_to_canonical[candidate] != spec.name:
                digest = hashlib.sha1(spec.name.encode("utf-8")).hexdigest()[:10]
                candidate = f"{candidate}_{digest}"
            canonical_to_bedrock[spec.name] = candidate
            bedrock_to_canonical[candidate] = spec.name

        return canonical_to_bedrock, bedrock_to_canonical

    def as_bedrock_tools(
        self,
        tool_names: Optional[Sequence[str]] = None,
        *,
        canonical_to_bedrock: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Convert registered tools into Bedrock Converse toolSpec objects.

        Public/canonical tool names may contain namespaces such as dots. Bedrock
        does not allow those names in ``toolSpec.name``, so this method emits a
        safe alias while preserving the canonical name in the local registry.
        """

        bedrock_tools: List[Dict[str, Any]] = []
        name_map = canonical_to_bedrock or self._bedrock_tool_name_maps(tool_names)[0]

        for spec in self._select_tools(tool_names):
            bedrock_tools.append(
                {
                    "toolSpec": {
                        "name": name_map.get(spec.name, spec.name),
                        "description": spec.description,
                        "inputSchema": {"json": spec.input_schema},
                    }
                }
            )

        return bedrock_tools

    @staticmethod
    def _map_tool_choice(tool_choice: Optional[str]) -> Optional[Dict[str, Any]]:
        if tool_choice in {None, "auto"}:
            return {"auto": {}}

        if tool_choice in {"required", "any"}:
            return {"any": {}}

        if isinstance(tool_choice, str):
            return {"tool": {"name": tool_choice}}

        return {"auto": {}}

    @staticmethod
    def _tool_choice_for_turn(
        requested_tool_choice: Optional[str],
        *,
        turn_index: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Map the notebook-level tool choice to Bedrock's toolChoice.

        Practical note:
        - `required` is useful on the first turn to prove tool calling works.
        - Keeping `required` on every subsequent turn can force the model to emit
          another tool call even after it already has enough tool results. Some
          models then produce malformed toolUse blocks such as an empty `name`.
        - Therefore this runtime treats `required` as "require at least one tool
          call at the start, then allow auto/final answer after tool results".
        """

        if requested_tool_choice in {"required", "any"} and turn_index > 0:
            return {"auto": {}}

        return BedrockRuntime._map_tool_choice(requested_tool_choice)

    def _sanitize_bedrock_assistant_content(
        self,
        content: Sequence[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[RuntimeToolCallRecord]]:
        """
        Return Bedrock-safe assistant content plus valid toolUse blocks.

        Bedrock validates the full conversation history on every Converse call.
        If a model emits `toolUse.name == ""`, passing that assistant message
        back into the next request raises ParamValidationError before the model is
        even invoked.

        This method removes invalid toolUse blocks from the history and records
        them in the local trace instead of resending invalid Bedrock payloads.
        """

        safe_content: List[Dict[str, Any]] = []
        valid_tool_uses: List[Dict[str, Any]] = []
        invalid_records: List[RuntimeToolCallRecord] = []

        for block in content or []:
            if not isinstance(block, dict):
                continue

            if "toolUse" not in block:
                # Text and other Bedrock-supported blocks are preserved.
                safe_content.append(block)
                continue

            tool_use = block.get("toolUse") or {}
            tool_use_id = str(tool_use.get("toolUseId") or "").strip()
            tool_name = str(tool_use.get("name") or "").strip()
            tool_input = tool_use.get("input", {}) or {}

            if tool_use_id and tool_name:
                safe_tool_use = {
                    "toolUseId": tool_use_id,
                    "name": tool_name,
                    "input": tool_input if isinstance(tool_input, dict) else {"value": tool_input},
                }
                valid_tool_uses.append(safe_tool_use)
                safe_content.append({"toolUse": safe_tool_use})
                continue

            synthetic_id = tool_use_id or f"invalid_tool_use_{uuid.uuid4().hex}"
            envelope = self.to_envelope(
                {
                    "error_type": "InvalidBedrockToolUse",
                    "message": "Model emitted a toolUse block with empty toolUseId or name.",
                    "raw_tool_use": tool_use,
                },
                tool_name=tool_name or "<invalid-empty-tool-name>",
                ok=False,
                extra_meta={"handled_by": "_sanitize_bedrock_assistant_content"},
            )
            invalid_records.append(
                RuntimeToolCallRecord(
                    tool_use_id=synthetic_id,
                    tool_name=tool_name or "<invalid-empty-tool-name>",
                    tool_input=tool_input if isinstance(tool_input, dict) else {"value": tool_input},
                    tool_output=envelope.model_dump(mode="json"),
                    ok=False,
                )
            )

        return safe_content, valid_tool_uses, invalid_records

    # ---------------------------------------------------------------------
    # Python-runtime runtime
    # ---------------------------------------------------------------------

    def run_direct(
        self,
        prompt: str,
        *,
        instructions: Optional[str] = None,
        model_id: Optional[str] = None,
        tool_choice: Optional[str] = "auto",
        tool_names: Optional[Sequence[str]] = None,
        max_turns: int = 8,
        max_tool_calls: Optional[int] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        retry_tool_errors: bool = True,
        max_tool_error_repairs: int = 2,
        synthesize_final_on_max_turns: bool = True,
        required_tools: Optional[Sequence[str]] = None,
        stop_when_required_tools_ok: bool = False,
    ) -> BedrockRunResult:
        """
        Run Bedrock Converse directly with a local tool loop.

        This is the reference runtime. Framework bridges should match its
        behavior as closely as possible.

        Error-repair policy:
        - If a tool call fails with a recoverable tool error, such as a
          Pydantic ValidationError or UnknownToolError, the runtime sends the
          ToolEnvelope error back to the model and forces another tool turn.
        - This gives the model a chance to call the same/correct tool with valid
          arguments instead of ending the run with a failed business step.
        - Non-recoverable runtime errors, such as ZeroDivisionError inside a
          business tool, are returned as normal ToolEnvelope errors and are not
          automatically retried forever.
        - If the model keeps calling tools until max_turns is reached but all
          recoverable failures have been resolved, the runtime can perform one
          final no-tool synthesis pass. This uses the language model, not
          business hardcodes, to write the final answer from the accumulated
          ToolEnvelope results.
        """

        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": [{"text": prompt}]}
        ]
        system = [{"text": instructions}] if instructions else None
        selected_model_id = model_id or self.model_id
        canonical_to_bedrock, bedrock_to_canonical = self._bedrock_tool_name_maps(tool_names)
        bedrock_tools = self.as_bedrock_tools(tool_names, canonical_to_bedrock=canonical_to_bedrock)

        final_text_parts: List[str] = []
        tool_records: List[RuntimeToolCallRecord] = []
        raw_responses: List[Dict[str, Any]] = []

        repair_attempts = 0
        force_tool_retry_next_turn = False

        recoverable_error_types = {
            "ValidationError",
            "UnknownToolError",
        }
        required_tool_names = {str(name) for name in (required_tools or []) if str(name).strip()}

        def _required_tools_are_ok() -> bool:
            """Return True when every required tool has at least one successful call.

            This is a generic batch/demo completion contract, not business logic.
            The caller decides which tools are required for a run. The runtime only
            checks the trace evidence and stops asking for more tools once the
            contract is satisfied.
            """
            if not required_tool_names:
                return False
            successful = {record.tool_name for record in tool_records if record.ok}
            return required_tool_names.issubset(successful)

        def _synthesize_final_answer(reason: str) -> Optional[BedrockRunResult]:
            """Create the final answer from a clean, text-only evidence payload.

            Bedrock Converse requires `toolConfig` whenever historical messages
            contain `toolUse`/`toolResult` blocks. For the final synthesis pass we
            intentionally avoid re-sending those raw tool blocks. Instead, we send
            a compact JSON evidence list as plain text. This keeps synthesis
            model-driven while preserving Bedrock's message grammar.
            """
            evidence = [
                {
                    "index": idx,
                    "tool_name": record.tool_name,
                    "ok": record.ok,
                    "input": self._make_jsonable(record.tool_input),
                    "output": self._make_jsonable(record.tool_output),
                }
                for idx, record in enumerate(tool_records)
            ]

            synthesis_payload = {
                "reason": reason,
                "original_prompt": prompt,
                "tool_evidence": evidence,
            }

            synthesis_messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": (
                                "BedrockRuntime final synthesis instruction:\n"
                                "Do not call tools. Produce the final user-facing answer "
                                "requested by the original prompt using only this JSON "
                                "ToolEnvelope evidence. If a required value is unavailable, "
                                "state that explicitly.\n\n"
                                f"{json.dumps(synthesis_payload, ensure_ascii=False, indent=2)}"
                            )
                        }
                    ],
                }
            ]
            try:
                synthesis_response = self.converse(
                    messages=synthesis_messages,
                    model_id=selected_model_id,
                    system=system,
                    tools=None,
                    tool_choice=None,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                raw_responses.append(self._compact_response_metadata(synthesis_response))
                synthesis_message = synthesis_response.get("output", {}).get("message", {})
                synthesis_content = synthesis_message.get("content", [])
                synthesis_parts = [
                    str(block.get("text"))
                    for block in synthesis_content
                    if isinstance(block, dict) and block.get("text")
                ]
                synthesized_text = "\n".join(synthesis_parts).strip()
                if synthesized_text:
                    return BedrockRunResult(
                        final_text=synthesized_text,
                        messages=messages + [
                            {"role": "user", "content": synthesis_messages[0]["content"]},
                            {"role": "assistant", "content": synthesis_content},
                        ],
                        tool_calls=tool_records,
                        raw_responses=raw_responses,
                    )
            except Exception:
                # Do not contaminate the final user-facing answer with synthesis
                # infrastructure failures. The existing tool evidence remains in
                # the trace and callers can inspect raw_responses if needed.
                return None
            return None

        def _tool_error_type(envelope_dict: Dict[str, Any]) -> Optional[str]:
            data = envelope_dict.get("data")
            if isinstance(data, dict):
                err = data.get("error_type")
                return str(err) if err else None
            return None

        def _has_recoverable_error(envelope_dict: Dict[str, Any]) -> bool:
            if envelope_dict.get("ok") is not False:
                return False
            return _tool_error_type(envelope_dict) in recoverable_error_types

        for _turn in range(max_turns):
            requested_tool_choice = tool_choice
            if isinstance(requested_tool_choice, str) and requested_tool_choice not in {"auto", "required", "any"}:
                requested_tool_choice = canonical_to_bedrock.get(requested_tool_choice, requested_tool_choice)

            if force_tool_retry_next_turn and bedrock_tools:
                bedrock_tool_choice = {"any": {}}
            else:
                bedrock_tool_choice = (
                    self._tool_choice_for_turn(requested_tool_choice, turn_index=_turn)
                    if bedrock_tools
                    else None
                )

            response = self.converse(
                messages=messages,
                model_id=selected_model_id,
                system=system,
                tools=bedrock_tools or None,
                tool_choice=bedrock_tool_choice,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            raw_responses.append(self._compact_response_metadata(response))

            output_message = response.get("output", {}).get("message", {})
            content = output_message.get("content", [])

            for block in content:
                if block.get("text"):
                    final_text_parts.append(str(block["text"]))

            safe_content, tool_uses, invalid_tool_records = (
                self._sanitize_bedrock_assistant_content(content)
            )
            tool_records.extend(invalid_tool_records)

            if invalid_tool_records and not tool_uses and not final_text_parts:
                final_text_parts.append(
                    "[BedrockRuntime] El modelo emitió un toolUse inválido "
                    "sin nombre de tool. Se detuvo el loop antes de reenviar "
                    "historial inválido a Bedrock."
                )

            if not tool_uses:
                return BedrockRunResult(
                    final_text="\n".join(part for part in final_text_parts if part).strip(),
                    messages=messages + [{"role": "assistant", "content": safe_content}],
                    tool_calls=tool_records,
                    raw_responses=raw_responses,
                )

            messages.append({"role": "assistant", "content": safe_content})

            tool_result_blocks: List[Dict[str, Any]] = []
            recoverable_failures_this_turn: List[Dict[str, Any]] = []

            for tool_use in tool_uses:
                tool_use_id = tool_use["toolUseId"]
                bedrock_tool_name = tool_use["name"]
                tool_name = bedrock_to_canonical.get(bedrock_tool_name, bedrock_tool_name)
                tool_input = tool_use.get("input", {}) or {}

                if max_tool_calls is not None and len(tool_records) >= max_tool_calls:
                    envelope = self.to_envelope(
                        {
                            "error_type": "MaxToolCallsExceeded",
                            "message": f"The run exceeded max_tool_calls={max_tool_calls}.",
                            "requested_tool": tool_name,
                        },
                        tool_name=tool_name,
                        ok=False,
                        extra_meta={"bedrock_tool_name": bedrock_tool_name},
                    )
                else:
                    envelope = self.execute_tool(tool_name, tool_input)

                envelope_dict = envelope.model_dump(mode="json")
                if bedrock_tool_name != tool_name:
                    envelope_dict.setdefault("meta", {})["bedrock_tool_name"] = bedrock_tool_name
                    envelope_dict.setdefault("meta", {})["canonical_tool_name"] = tool_name

                tool_result: Dict[str, Any] = {
                    "toolUseId": tool_use_id,
                    "content": [{"json": envelope_dict}],
                }
                if not envelope.ok:
                    tool_result["status"] = "error"

                tool_result_blocks.append({"toolResult": tool_result})

                tool_records.append(
                    RuntimeToolCallRecord(
                        tool_use_id=tool_use_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_output=envelope_dict,
                        ok=envelope.ok,
                        meta={"bedrock_tool_name": bedrock_tool_name} if bedrock_tool_name != tool_name else {},
                    )
                )

                if _has_recoverable_error(envelope_dict):
                    recoverable_failures_this_turn.append(
                        {
                            "tool_use_id": tool_use_id,
                            "tool_name": tool_name,
                            "input": tool_input,
                            "error_type": _tool_error_type(envelope_dict),
                            "error_message": (
                                envelope_dict.get("data", {}).get("message")
                                if isinstance(envelope_dict.get("data"), dict)
                                else None
                            ),
                        }
                    )

            should_retry_tools = (
                retry_tool_errors
                and bool(recoverable_failures_this_turn)
                and repair_attempts < max_tool_error_repairs
            )

            if should_retry_tools:
                repair_attempts += 1
                force_tool_retry_next_turn = True

                tool_result_blocks.append(
                    {
                        "text": (
                            "BedrockRuntime repair instruction:\n"
                            "One or more tool calls failed with recoverable input errors. "
                            "Do not produce a final answer yet. Correct the failed tool "
                            "call(s) using the provided tool schema and call the appropriate "
                            "tool again. Failed calls:\n"
                            f"{json.dumps(recoverable_failures_this_turn, ensure_ascii=False)}"
                        )
                    }
                )
            else:
                force_tool_retry_next_turn = False

            messages.append({"role": "user", "content": tool_result_blocks})

            if stop_when_required_tools_ok and _required_tools_are_ok():
                synthesized = _synthesize_final_answer(
                    "All caller-declared required tools have successful ToolEnvelope evidence."
                )
                if synthesized is not None:
                    return synthesized

        final_text = "\n".join(part for part in final_text_parts if part).strip()

        if synthesize_final_on_max_turns and not final_text and messages:
            synthesized = _synthesize_final_answer("The maximum tool-loop turns were reached.")
            if synthesized is not None:
                return synthesized
            final_text = "\n".join(part for part in final_text_parts if part).strip()

        return BedrockRunResult(
            final_text=final_text,
            messages=messages,
            tool_calls=tool_records,
            raw_responses=raw_responses,
        )

    @staticmethod
    def _compact_response_metadata(response: Dict[str, Any]) -> Dict[str, Any]:
        """Keep raw response metadata useful but small for notebook display."""

        meta = response.get("ResponseMetadata", {}) or {}
        usage = response.get("usage", {}) or {}
        metrics = response.get("metrics", {}) or {}
        runtime_meta = response.get("agentic_systems", {}) or {}
        return {
            "request_id": meta.get("RequestId"),
            "http_status_code": meta.get("HTTPStatusCode"),
            "usage": usage,
            "stop_reason": response.get("stopReason"),
            "service_latency_ms": metrics.get("latencyMs"),
            "client_duration_ms": runtime_meta.get("client_duration_ms"),
        }

    @staticmethod
    def print_run_result(result: BedrockRunResult, *, mode: str = "compact") -> None:
        """Pretty-print compact or full run trace."""

        print(json.dumps(result.trace(mode=mode), indent=2, ensure_ascii=False))

    # ---------------------------------------------------------------------
    # OpenAI runtime bridge
    # ---------------------------------------------------------------------

    def as_openai_runtime_tools(self, tool_names: Optional[Sequence[str]] = None) -> List[Any]:
        """
        Convert neutral ADA tools into OpenAI runtime FunctionTool objects.

        Important contract:
        - The SDK may orchestrate tool calls.
        - BedrockRuntime must execute every tool call.
        - Every tool output must be a ToolEnvelope JSON string.

        We intentionally avoid the SDK `function_tool(...)` decorator here because
        it can intercept validation errors and return framework-owned text such as
        "An error occurred while running the tool" before the runtime can
        canonize the failure. Manual FunctionTool wiring keeps the bridge strict
        and runtime-agnostic.
        """

        return [
            self._make_openai_function_tool(spec)
            for spec in self._select_tools(tool_names)
        ]

    @staticmethod
    def _coerce_framework_tool_arguments(raw_args: Any) -> Any:
        """Coerce framework-provided tool arguments into a JSON-like object.

        The OpenAI runtime documents ``on_invoke_tool`` arguments as a JSON
        string, but runtimes should not depend on that representation. Across
        SDK versions, tests, or custom runners, the value may already be a dict,
        may be bytes, or may be an object exposing pydantic/model-dump methods.
        This helper is intentionally generic and does not know any tool names.
        """

        if raw_args is None or raw_args == "":
            return {}

        if isinstance(raw_args, dict):
            return raw_args

        if isinstance(raw_args, bytes):
            raw_args = raw_args.decode("utf-8")

        if isinstance(raw_args, str):
            return json.loads(raw_args)

        if hasattr(raw_args, "model_dump"):
            return raw_args.model_dump(mode="json")

        if hasattr(raw_args, "dict"):
            return raw_args.dict()

        return raw_args

    @staticmethod
    def _ensure_openai_strict_json_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Return an OpenAI-compatible strict JSON schema without tool-specific logic.

        The runtime recommends strict JSON schema for FunctionTool. Some SDK
        versions do not fully normalize schemas supplied to FunctionTool directly,
        so the runtime makes the neutral tool schema explicit: object schemas get
        ``properties`` and ``additionalProperties=False`` recursively.
        """

        def _strict(node: Any) -> Any:
            if isinstance(node, list):
                return [_strict(item) for item in node]
            if not isinstance(node, dict):
                return node

            out = {key: _strict(value) for key, value in node.items()}

            node_type = out.get("type")
            if node_type == "object" or "properties" in out:
                out.setdefault("type", "object")
                out.setdefault("properties", {})
                out["additionalProperties"] = False
                if isinstance(out.get("properties"), dict):
                    out["properties"] = {
                        key: _strict(value)
                        for key, value in out["properties"].items()
                    }

            if "items" in out:
                out["items"] = _strict(out["items"])

            for combinator in ("anyOf", "oneOf", "allOf"):
                if combinator in out:
                    out[combinator] = _strict(out[combinator])

            return out

        return _strict(dict(schema or {"type": "object", "properties": {}}))

    @classmethod
    def _openai_function_tool_schema(cls, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a neutral tool schema for OpenAI runtime FunctionTool."""

        strict_schema = cls._ensure_openai_strict_json_schema(schema)
        try:
            from agents.strict_schema import ensure_strict_json_schema

            return ensure_strict_json_schema(strict_schema)
        except Exception:
            return strict_schema

    def _make_openai_function_tool(self, spec: RuntimeToolSpec) -> Any:
        """Create a native OpenAI runtime FunctionTool backed by execute_tool().

        This is intentionally native SDK usage: Agent + Runner + FunctionTool +
        ModelProvider. The runtime only owns the tool contract and Bedrock model
        transport; it does not replace the SDK loop with run_direct().
        """

        from agents import FunctionTool

        async def _on_invoke_tool(context: Any, raw_args: Any) -> str:
            try:
                parsed_args = self._coerce_framework_tool_arguments(raw_args)

                if not isinstance(parsed_args, dict):
                    envelope = self.to_envelope(
                        {
                            "error_type": "InvalidToolArguments",
                            "message": "Tool arguments must be a JSON object after bridge coercion.",
                            "raw_arguments": self._make_jsonable(raw_args),
                            "coerced_arguments": self._make_jsonable(parsed_args),
                        },
                        tool_name=spec.name,
                        ok=False,
                        extra_meta={
                            "bridge": "openai_runtime",
                            "handled_by": "_make_openai_function_tool",
                        },
                    )
                    return envelope.model_dump_json()

                envelope = self.execute_tool(spec.name, parsed_args)
                return envelope.model_dump_json()

            except Exception as exc:
                envelope = self.to_envelope(
                    {
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                        "raw_arguments": self._make_jsonable(raw_args),
                    },
                    tool_name=spec.name,
                    ok=False,
                    extra_meta={
                        "bridge": "openai_runtime",
                        "handled_by": "_make_openai_function_tool",
                    },
                )
                return envelope.model_dump_json()

        return FunctionTool(
            name=spec.name,
            description=spec.description,
            params_json_schema=self._openai_function_tool_schema(spec.input_schema),
            on_invoke_tool=_on_invoke_tool,
            strict_json_schema=True,
        )

    def _make_openai_tool_wrapper(self, spec: RuntimeToolSpec) -> Callable[..., str]:
        """
        Internal helper retained for downstream stability. Prefer
        _make_openai_function_tool(), which avoids SDK-side error text leakage.
        """

        @wraps(spec.func)
        def _wrapper(*args: Any, **kwargs: Any) -> str:
            bound = spec.signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            envelope = self.execute_tool(spec.name, dict(bound.arguments))
            return envelope.model_dump_json()

        _wrapper.__name__ = spec.name
        _wrapper.__qualname__ = spec.name
        _wrapper.__doc__ = spec.description
        _wrapper.__signature__ = spec.signature

        return _wrapper

    def create_openai_agent(
        self,
        *,
        name: str,
        instructions: str,
        tool_names: Optional[Sequence[str]] = None,
    ) -> Any:
        """Create an OpenAI runtime Agent backed by this runtime's tools."""

        from agents import Agent, set_tracing_disabled

        if self.disable_openai_runtime_tracing:
            set_tracing_disabled(True)

        return Agent(
            name=name,
            instructions=instructions,
            tools=self.as_openai_runtime_tools(tool_names),
        )

    def openai_runtime_model_provider(self) -> Any:
        """Return an OpenAI runtime ModelProvider that calls Bedrock Converse."""

        from agents import Model, ModelProvider, ModelSettings
        from agents.items import (
            ModelResponse,
            ResponseFunctionToolCall,
            ResponseOutputMessage,
            ResponseOutputText,
            Usage,
        )

        runtime = self

        class BedrockOpenAIAgentsModel(Model):
            def __init__(self, model_name: str) -> None:
                self.model_name = model_name

            async def get_response(
                self,
                system_instructions,
                input,
                model_settings,
                tools,
                output_schema,
                handoffs,
                tracing,
                *,
                previous_response_id=None,
                conversation_id=None,
                prompt=None,
            ) -> ModelResponse:
                settings = self._coerce_settings(model_settings)

                messages, extra_system = runtime._openai_input_to_bedrock_messages(input)
                unresolved_failed_tools = runtime._openai_unresolved_failed_tools_from_input(input)

                system_blocks: List[Dict[str, str]] = []
                if system_instructions:
                    system_blocks.append({"text": str(system_instructions)})
                system_blocks.extend(extra_system)
                if unresolved_failed_tools:
                    repair_items = []
                    for failure in unresolved_failed_tools:
                        repair_items.append(
                            {
                                "tool_name": failure.get("tool_name"),
                                "failed_input": failure.get("input"),
                                "error_type": failure.get("error_type"),
                                "error_data": failure.get("output_data"),
                            }
                        )
                    system_blocks.append(
                        {
                            "text": (
                                "Hay toolResult con ok=false que siguen sin recuperarse. "
                                "No redactes una respuesta final todavía. Vuelve a llamar las tools fallidas "
                                "con argumentos completos y válidos, usando la evidencia disponible en el historial. "
                                "No repitas tools que ya tienen ToolEnvelope ok=true salvo que sean necesarias como entrada. "
                                f"Fallas pendientes: {json.dumps(repair_items, ensure_ascii=False)}"
                            )
                        }
                    )

                bedrock_tools = runtime._openai_tools_to_bedrock_tools(tools or [])
                requested_tool_choice = getattr(settings, "tool_choice", None)
                if runtime._openai_input_has_tool_results(input):
                    if unresolved_failed_tools:
                        requested_tool_choice = "any"
                    elif requested_tool_choice in {"required", "any"}:
                        # Same policy as run_direct(): require tools on the first turn,
                        # then allow the model to produce the final answer after it has
                        # received successful tool results.
                        requested_tool_choice = "auto"

                bedrock_tool_choice = runtime._openai_tool_choice_to_bedrock(
                    requested_tool_choice,
                    bool(bedrock_tools),
                )

                response = runtime.converse(
                    model_id=self.model_name,
                    messages=messages,
                    system=system_blocks or None,
                    tools=bedrock_tools or None,
                    tool_choice=bedrock_tool_choice,
                    max_tokens=getattr(settings, "max_tokens", None),
                    temperature=getattr(settings, "temperature", None),
                    top_p=getattr(settings, "top_p", None),
                )

                return self._bedrock_to_model_response(response)

            async def stream_response(
                self,
                system_instructions,
                input,
                model_settings,
                tools,
                output_schema,
                handoffs,
                tracing,
                *,
                previous_response_id=None,
                conversation_id=None,
                prompt=None,
            ):
                raise NotImplementedError(
                    "BedrockRuntime light version supports non-streaming Converse only."
                )

            @staticmethod
            def _coerce_settings(model_settings: Any) -> Any:
                if model_settings is None:
                    return ModelSettings()
                if isinstance(model_settings, dict):
                    return ModelSettings(**model_settings)
                return model_settings

            @staticmethod
            def _bedrock_to_model_response(response: Dict[str, Any]) -> ModelResponse:
                output_items: List[Any] = []
                content = response.get("output", {}).get("message", {}).get("content", [])

                for block in content:
                    if "text" in block and str(block["text"]).strip():
                        output_items.append(
                            ResponseOutputMessage(
                                id=f"msg_{uuid.uuid4().hex}",
                                type="message",
                                role="assistant",
                                status="completed",
                                content=[
                                    ResponseOutputText(
                                        type="output_text",
                                        text=str(block["text"]),
                                        annotations=[],
                                    )
                                ],
                            )
                        )

                    elif "toolUse" in block:
                        tool_use = block.get("toolUse") or {}
                        tool_use_id = str(tool_use.get("toolUseId") or "").strip()
                        tool_name = str(tool_use.get("name") or "").strip()

                        if not tool_use_id or not tool_name:
                            # Do not emit an invalid ResponseFunctionToolCall.
                            # If it later re-enters the Bedrock history, Bedrock
                            # rejects the whole request because toolUse.name has
                            # min length 1.
                            output_items.append(
                                ResponseOutputMessage(
                                    id=f"msg_{uuid.uuid4().hex}",
                                    type="message",
                                    role="assistant",
                                    status="completed",
                                    content=[
                                        ResponseOutputText(
                                            type="output_text",
                                            text=(
                                                "[BedrockRuntime] Ignoré un toolUse inválido "
                                                "emitido por el modelo porque no tenía nombre de tool."
                                            ),
                                            annotations=[],
                                        )
                                    ],
                                )
                            )
                            continue

                        output_items.append(
                            ResponseFunctionToolCall(
                                id=f"fc_{tool_use_id}",
                                type="function_call",
                                call_id=tool_use_id,
                                name=tool_name,
                                arguments=json.dumps(
                                    tool_use.get("input", {}),
                                    ensure_ascii=False,
                                ),
                                status="completed",
                            )
                        )

                usage_raw = response.get("usage", {}) or {}
                request_id = response.get("ResponseMetadata", {}).get("RequestId")

                usage = Usage(
                    requests=1,
                    input_tokens=usage_raw.get("inputTokens", 0),
                    output_tokens=usage_raw.get("outputTokens", 0),
                    total_tokens=usage_raw.get("totalTokens", 0),
                )

                return ModelResponse(
                    output=output_items,
                    usage=usage,
                    response_id=request_id,
                    request_id=request_id,
                )

        class BedrockOpenAIAgentsModelProvider(ModelProvider):
            def get_model(self, model_name: Optional[str]) -> Model:
                return BedrockOpenAIAgentsModel(model_name or runtime.model_id)

        return BedrockOpenAIAgentsModelProvider()

    def _openai_run_config(
        self,
        *,
        model_id: Optional[str] = None,
        tool_choice: Optional[str] = "auto",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        """Build a RunConfig for OpenAI runtime executions."""

        from agents import ModelSettings, RunConfig

        settings = ModelSettings(
            max_tokens=max_tokens or self.max_tokens_default,
            temperature=self.temperature_default if temperature is None else temperature,
            tool_choice=tool_choice,
        )
        return RunConfig(
            model_provider=self.openai_runtime_model_provider(),
            model=model_id or self.model_id,
            model_settings=settings,
        )

    def run_openai_agent_sync(
        self,
        *,
        agent: Any,
        prompt: str,
        model_id: Optional[str] = None,
        tool_choice: Optional[str] = "auto",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_turns: Optional[int] = 12,
    ) -> Any:
        """Run an OpenAI Agents SDK Agent through the sync ``Runner`` path.

        ``agents.Runner.run_sync`` owns an asyncio event loop internally. That
        is fine in scripts, but notebooks and async apps already have a running
        loop. In that case we isolate the SDK sync runner in a worker thread so
        public ``agent.run(...)`` remains usable without patching the notebook
        event loop or requiring ``nest_asyncio``. Async callers should still
        prefer ``agent.arun(...)`` because it uses the SDK's native async path.
        """

        from agents import Runner

        run_config = self._openai_run_config(
            model_id=model_id,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        def _run() -> Any:
            return Runner.run_sync(
                agent,
                prompt,
                max_turns=max_turns,
                run_config=run_config,
            )

        if _has_running_event_loop():
            return _run_in_worker_thread(_run)
        return _run()

    async def run_openai_agent(
        self,
        *,
        agent: Any,
        prompt: str,
        model_id: Optional[str] = None,
        tool_choice: Optional[str] = "auto",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_turns: Optional[int] = 12,
    ) -> Any:
        """Run an OpenAI Agents SDK Agent through async ``Runner.run``."""

        from agents import Runner

        return await Runner.run(
            agent,
            prompt,
            max_turns=max_turns,
            run_config=self._openai_run_config(
                model_id=model_id,
                tool_choice=tool_choice,
                max_tokens=max_tokens,
                temperature=temperature,
            ),
        )

    @staticmethod
    def _openai_input_has_tool_results(input_data: Any) -> bool:
        """Return True when the Agents SDK is calling the model after tool execution."""

        if not isinstance(input_data, list):
            return False

        return any(
            isinstance(item, dict) and item.get("type") == "function_call_output"
            for item in input_data
        )

    def _openai_unresolved_failed_tools_from_input(self, input_data: Any) -> List[Dict[str, Any]]:
        """Return unresolved failed tool outputs from OpenAI Agents SDK history.

        This powers native-SDK repair semantics: when the SDK calls the model
        after a failed FunctionTool output, the custom ModelProvider asks the
        model to repair the failed tools instead of accepting a final answer
        unsupported by successful tool evidence.
        """

        if not isinstance(input_data, list):
            return []

        calls_by_id: Dict[str, Dict[str, Any]] = {}
        ordered_events: List[Dict[str, Any]] = []

        for item in input_data:
            if not isinstance(item, dict):
                continue

            if item.get("type") == "function_call":
                call_id = str(item.get("call_id") or "")
                if not call_id:
                    continue
                calls_by_id[call_id] = {
                    "tool_name": item.get("name"),
                    "input": self._parse_json_maybe(item.get("arguments", {})),
                }

            elif item.get("type") == "function_call_output":
                call_id = str(item.get("call_id") or "")
                prior = calls_by_id.get(call_id, {})
                parsed_output = self.parse_framework_tool_output(
                    item.get("output"),
                    expected_tool_name=prior.get("tool_name"),
                )
                output_data = parsed_output.get("data")
                ordered_events.append(
                    {
                        "index": len(ordered_events),
                        "tool_use_id": call_id,
                        "tool_name": prior.get("tool_name") or parsed_output.get("tool_name") or "unknown",
                        "ok": bool(parsed_output.get("ok")),
                        "input": prior.get("input", {}),
                        "output_kind": parsed_output.get("kind"),
                        "output_data": output_data,
                        "error_type": output_data.get("error_type") if isinstance(output_data, dict) else None,
                    }
                )

        return self._failure_semantics_from_tool_summaries(ordered_events)["unresolved_failed_tools"]

    @staticmethod
    def _extract_openai_content_text(content: Any) -> str:
        if content is None:
            return ""

        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            if "text" in content:
                return str(content["text"])
            return json.dumps(content, ensure_ascii=False)

        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        parts.append(str(item["text"]))
                    elif item.get("type") in {"text", "input_text", "output_text"}:
                        parts.append(str(item.get("text", "")))
                else:
                    parts.append(str(item))
            return "".join(parts)

        return str(content)

    def _openai_input_to_bedrock_messages(
        self,
        input_data: Any,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        """
        Convert OpenAI Agents SDK input history into Bedrock Converse messages.

        Bedrock Converse has a strict grammar for tool use:
            assistant(toolUse*) -> user(toolResult*)

        A toolResult block is only valid when it answers a toolUse block from the
        immediately preceding assistant turn. OpenAI Agents SDK histories can
        contain accumulated function_call_output events, especially after repair
        loops. This converter therefore fails closed: orphan or duplicated
        function_call_output events are kept out of the Bedrock payload instead
        of being emitted as invalid toolResult blocks.
        """

        if isinstance(input_data, str):
            return [{"role": "user", "content": [{"text": input_data}]}], []

        messages: List[Dict[str, Any]] = []
        extra_system: List[Dict[str, str]] = []

        if not isinstance(input_data, list):
            return [{"role": "user", "content": [{"text": str(input_data)}]}], []

        call_id_to_tool_name = {
            str(history_item.get("call_id")): str(history_item.get("name"))
            for history_item in input_data
            if isinstance(history_item, dict)
            and history_item.get("type") == "function_call"
            and history_item.get("call_id")
            and history_item.get("name")
        }

        pending_call_ids: List[str] = []
        skipped_orphan_outputs = 0
        i = 0
        n = len(input_data)

        while i < n:
            item = input_data[i]

            if not isinstance(item, dict):
                i += 1
                continue

            role = item.get("role")
            item_type = item.get("type")

            if role in {"system", "developer", "user", "assistant"} and "content" in item:
                # A normal message breaks immediate toolResult pairing.
                pending_call_ids = []
                text = self._extract_openai_content_text(item.get("content"))
                if role in {"system", "developer"}:
                    if text:
                        extra_system.append({"text": text})
                elif role in {"user", "assistant"}:
                    messages.append({"role": role, "content": [{"text": text}]})
                i += 1
                continue

            if item_type == "message":
                pending_call_ids = []
                role = item.get("role", "assistant")
                text = self._extract_openai_content_text(item.get("content"))
                if role in {"system", "developer"}:
                    if text:
                        extra_system.append({"text": text})
                elif role in {"user", "assistant"}:
                    messages.append({"role": role, "content": [{"text": text}]})
                i += 1
                continue

            if item_type == "function_call":
                content_blocks: List[Dict[str, Any]] = []
                pending_call_ids = []

                while i < n:
                    current = input_data[i]
                    if not isinstance(current, dict) or current.get("type") != "function_call":
                        break

                    raw_args = current.get("arguments", {})
                    parsed_args = self._parse_json_maybe(raw_args)
                    if not isinstance(parsed_args, dict):
                        parsed_args = {"value": parsed_args}

                    call_id = str(current.get("call_id") or "").strip()
                    name = str(current.get("name") or "").strip()

                    if call_id and name:
                        content_blocks.append(
                            {
                                "toolUse": {
                                    "toolUseId": call_id,
                                    "name": name,
                                    "input": parsed_args,
                                }
                            }
                        )
                        pending_call_ids.append(call_id)
                    i += 1

                if content_blocks:
                    messages.append({"role": "assistant", "content": content_blocks})
                continue

            if item_type == "function_call_output":
                content_blocks: List[Dict[str, Any]] = []
                expected_call_ids = set(pending_call_ids)
                emitted_call_ids: set[str] = set()

                while i < n:
                    current = input_data[i]
                    if not isinstance(current, dict) or current.get("type") != "function_call_output":
                        break

                    call_id = str(current.get("call_id") or "").strip()
                    can_emit = (
                        bool(call_id)
                        and call_id in expected_call_ids
                        and call_id not in emitted_call_ids
                    )

                    if can_emit:
                        parsed_output = self.parse_framework_tool_output(
                            current.get("output"),
                            expected_tool_name=call_id_to_tool_name.get(call_id),
                        )

                        tool_result: Dict[str, Any] = {
                            "toolUseId": call_id,
                            "content": [{"json": parsed_output}],
                        }
                        if parsed_output.get("ok") is False:
                            tool_result["status"] = "error"

                        content_blocks.append({"toolResult": tool_result})
                        emitted_call_ids.add(call_id)
                    else:
                        skipped_orphan_outputs += 1
                    i += 1

                if content_blocks:
                    messages.append({"role": "user", "content": content_blocks})
                pending_call_ids = [cid for cid in pending_call_ids if cid not in emitted_call_ids]
                continue

            # Unknown SDK item. Do not let it keep stale toolUse pairing alive.
            pending_call_ids = []
            i += 1

        if skipped_orphan_outputs:
            extra_system.append(
                {
                    "text": (
                        "BedrockRuntime bridge note: skipped "
                        f"{skipped_orphan_outputs} orphan or duplicated OpenAI Agents "
                        "function_call_output event(s) while converting history to "
                        "Bedrock Converse. This prevents invalid toolResult blocks."
                    )
                }
            )

        return messages, extra_system

    @staticmethod
    def _openai_tools_to_bedrock_tools(tools: Sequence[Any]) -> List[Dict[str, Any]]:
        bedrock_tools: List[Dict[str, Any]] = []

        for tool in tools:
            name = getattr(tool, "name", None)
            if not name:
                continue

            schema = getattr(tool, "params_json_schema", None) or {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            }

            bedrock_tools.append(
                {
                    "toolSpec": {
                        "name": name,
                        "description": getattr(tool, "description", None) or f"Tool {name}",
                        "inputSchema": {"json": schema},
                    }
                }
            )

        return bedrock_tools

    @staticmethod
    def _openai_tool_choice_to_bedrock(
        tool_choice: Optional[str],
        has_tools: bool,
    ) -> Optional[Dict[str, Any]]:
        if not has_tools:
            return None

        if tool_choice in {None, "auto"}:
            return {"auto": {}}

        if tool_choice in {"required", "any"}:
            return {"any": {}}

        if isinstance(tool_choice, str):
            return {"tool": {"name": tool_choice}}

        return {"auto": {}}

    def audit_openai_tool_outputs(self, result: Any) -> List[Dict[str, Any]]:
        """Parse OpenAI Agents SDK function_call_output items into JSON envelopes."""

        audit: List[Dict[str, Any]] = []

        for item in self._safe_openai_input_list(result):
            if isinstance(item, dict) and item.get("type") == "function_call_output":
                call_id = str(item.get("call_id") or "")
                tool_name = None
                for prior in self._safe_openai_input_list(result):
                    if (
                        isinstance(prior, dict)
                        and prior.get("type") == "function_call"
                        and str(prior.get("call_id") or "") == call_id
                    ):
                        tool_name = prior.get("name")
                        break

                audit.append(
                    {
                        "call_id": item.get("call_id"),
                        "tool_name": tool_name,
                        "parsed_output": self.parse_framework_tool_output(
                            item.get("output"),
                            expected_tool_name=str(tool_name) if tool_name else None,
                        ),
                    }
                )

        return audit

    @staticmethod
    def _safe_openai_input_list(result: Any) -> List[Dict[str, Any]]:
        """Best-effort access to OpenAI Agents SDK result history."""

        try:
            items = result.to_input_list()
        except Exception:
            return []

        if not isinstance(items, list):
            return []

        return [item for item in items if isinstance(item, dict)]

    @staticmethod
    def _parse_json_maybe(value: Any) -> Any:
        """Parse a JSON string when possible; otherwise return the original value."""

        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value

    @staticmethod
    def _get_usage_field(usage: Any, *names: str) -> int:
        """Read a token field from pydantic objects, dataclasses, dicts, or SDK objects."""

        for name in names:
            if isinstance(usage, dict) and name in usage:
                try:
                    return int(usage.get(name) or 0)
                except Exception:
                    return 0

            if hasattr(usage, name):
                try:
                    return int(getattr(usage, name) or 0)
                except Exception:
                    return 0

        return 0

    def _openai_usage_totals(self, result: Any) -> Dict[str, int]:
        """
        Extract token usage from OpenAI Agents SDK results when available.

        The SDK object shape may change across versions, so this method is
        defensive: it prefers `result.raw_responses[*].usage`, and falls back
        to `result.usage` if present.
        """

        totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
        }

        raw_responses = getattr(result, "raw_responses", None) or []
        if raw_responses:
            for response in raw_responses:
                usage = getattr(response, "usage", None)
                if usage is None and isinstance(response, dict):
                    usage = response.get("usage")
                if usage is None:
                    continue

                totals["input_tokens"] += self._get_usage_field(usage, "input_tokens", "inputTokens")
                totals["output_tokens"] += self._get_usage_field(usage, "output_tokens", "outputTokens")
                totals["total_tokens"] += self._get_usage_field(usage, "total_tokens", "totalTokens")
                totals["requests"] += self._get_usage_field(usage, "requests") or 1

            return totals

        usage = getattr(result, "usage", None)
        if usage is None and isinstance(result, dict):
            usage = result.get("usage")

        if usage is not None:
            totals["input_tokens"] = self._get_usage_field(usage, "input_tokens", "inputTokens")
            totals["output_tokens"] = self._get_usage_field(usage, "output_tokens", "outputTokens")
            totals["total_tokens"] = self._get_usage_field(usage, "total_tokens", "totalTokens")
            totals["requests"] = self._get_usage_field(usage, "requests") or 1

        return totals

    @staticmethod
    def _failure_semantics_from_tool_summaries(
        tool_summaries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Classify historical, recovered, and unresolved tool failures."""

        failed_tool_events = [
            tool for tool in tool_summaries
            if not tool.get("ok")
        ]

        recovered_tool_errors: List[Dict[str, Any]] = []
        unresolved_failed_tools: List[Dict[str, Any]] = []

        for failed in failed_tool_events:
            failed_index = int(failed.get("index", -1))
            failed_name = failed.get("tool_name")

            recovery = next(
                (
                    tool for tool in tool_summaries
                    if int(tool.get("index", -1)) > failed_index
                    and tool.get("tool_name") == failed_name
                    and tool.get("ok") is True
                ),
                None,
            )

            if recovery:
                recovered_tool_errors.append(
                    {
                        **failed,
                        "recovered": True,
                        "recovered_by_tool_use_id": recovery.get("tool_use_id"),
                        "recovered_by_index": recovery.get("index"),
                    }
                )
            else:
                unresolved_failed_tools.append(
                    {
                        **failed,
                        "recovered": False,
                    }
                )

        return {
            "failed_tool_events": failed_tool_events,
            "recovered_tool_errors": recovered_tool_errors,
            "unresolved_failed_tools": unresolved_failed_tools,
        }

    def openai_compact_trace(self, result: Any) -> Dict[str, Any]:
        """
        Build a compact trace for OpenAI runtime results.

        This intentionally mirrors `BedrockRunResult.compact_trace()` as much as
        possible, but it extracts data from the SDK result object rather than
        from the direct Bedrock runtime.

        Validation should use this trace's tool outputs, not `final_text`,
        because final text is naturally variable across runtimes.
        """

        final_text = str(getattr(result, "final_output", "") or "")
        items = self._safe_openai_input_list(result)

        calls_by_id: Dict[str, Dict[str, Any]] = {}
        ordered_events: List[Dict[str, Any]] = []

        for item in items:
            if item.get("type") == "function_call":
                call_id = str(item.get("call_id") or "")
                if not call_id:
                    continue

                calls_by_id[call_id] = {
                    "tool_use_id": call_id,
                    "tool_name": item.get("name"),
                    "input": self._parse_json_maybe(item.get("arguments", {})),
                }

            elif item.get("type") == "function_call_output":
                call_id = str(item.get("call_id") or "")
                prior_call = calls_by_id.get(call_id, {})
                parsed_output = self.parse_framework_tool_output(
                    item.get("output"),
                    expected_tool_name=prior_call.get("tool_name"),
                )

                output_data = parsed_output.get("data")
                error_type = (
                    output_data.get("error_type")
                    if isinstance(output_data, dict)
                    else None
                )

                ordered_events.append(
                    {
                        "index": len(ordered_events),
                        "tool_use_id": call_id,
                        "tool_name": (
                            prior_call.get("tool_name")
                            or parsed_output.get("tool_name")
                            or "unknown"
                        ),
                        "ok": bool(parsed_output.get("ok")),
                        "input": prior_call.get("input", {}),
                        "output_kind": parsed_output.get("kind"),
                        "output_data": output_data,
                        "error_type": error_type,
                    }
                )

        semantics = self._failure_semantics_from_tool_summaries(ordered_events)
        failed_tool_events = semantics["failed_tool_events"]
        recovered_tool_errors = semantics["recovered_tool_errors"]
        unresolved_failed_tools = semantics["unresolved_failed_tools"]

        raw_responses = getattr(result, "raw_responses", None) or []

        return {
            "trace_schema_version": "ada.compact_trace.v3",
            "runtime": "openai_runtime",
            "run_ok": bool(final_text) and len(unresolved_failed_tools) == 0,
            "final_text": final_text,
            "turns": len(raw_responses),
            "message_count": len(items),
            "tool_call_count": len(ordered_events),
            "successful_tool_count": len([tool for tool in ordered_events if tool.get("ok")]),
            "failed_tool_event_count": len(failed_tool_events),
            "recovered_tool_error_count": len(recovered_tool_errors),
            "unresolved_failed_tool_count": len(unresolved_failed_tools),
            "tools": ordered_events,
            "failed_tool_events": failed_tool_events,
            "recovered_tool_errors": recovered_tool_errors,
            "unresolved_failed_tools": unresolved_failed_tools,


            "usage_totals": self._openai_usage_totals(result),
            "stop_reasons_available": False,
            "stop_reasons": None,
            "stop_reason_note": (
                "OpenAI Agents SDK result objects in this bridge do not expose "
                "Bedrock stop reasons. None means unavailable, not an empty list."
            ),
        }

    @staticmethod
    def _contains_subset(actual: Any, expected_subset: Any) -> bool:
        """Return True if actual contains the expected subset recursively."""

        if isinstance(expected_subset, dict):
            if not isinstance(actual, dict):
                return False
            for key, expected_value in expected_subset.items():
                if key not in actual:
                    return False
                if not BedrockRuntime._contains_subset(actual[key], expected_value):
                    return False
            return True

        if isinstance(expected_subset, list):
            return actual == expected_subset

        if isinstance(expected_subset, str) and isinstance(actual, str):
            return expected_subset in actual

        return actual == expected_subset

    def validate_expected_tool_outputs(
        self,
        trace: Dict[str, Any],
        expected: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate a run using tool outputs, never the model's final prose.

        The validator uses the latest successful call per tool. This makes it
        robust to repair loops where an earlier call failed and a later call
        fixed the input.

        Each check record is deliberately explicit, so the notebook can show
        not just that a tool passed, but which assertions were evaluated.
        """

        issues: List[Dict[str, Any]] = []
        checks: List[Dict[str, Any]] = []

        if not isinstance(trace, dict):
            return {
                "ok": False,
                "checks": [],
                "issues": [{
                    "type": "invalid_trace",
                    "message": "Trace must be a dict.",
                }],
            }

        if expected.get("require_run_ok", True) and trace.get("run_ok") is not True:
            issues.append({
                "type": "run_not_ok",
                "actual": trace.get("run_ok"),
            })

        final_text = str(trace.get("final_text") or "")
        for needle in expected.get("final_text_contains", []) or []:
            needle_text = str(needle)
            contains_ok = needle_text.lower() in final_text.lower()
            if not contains_ok:
                issues.append({
                    "type": "final_text_missing_substring",
                    "expected_substring": needle_text,
                })

        successful_by_name: Dict[str, Dict[str, Any]] = {}
        for event in trace.get("tools", []) or []:
            if event.get("ok") is True:
                successful_by_name[str(event.get("tool_name"))] = event

        for tool_name, spec in (expected.get("tools") or {}).items():
            event = successful_by_name.get(tool_name)

            check_record: Dict[str, Any] = {
                "tool_name": tool_name,
                "found": event is not None,
                "tool_use_id": event.get("tool_use_id") if event else None,
                "assertions": {},
            }

            if event is None:
                check_record["ok"] = False
                issues.append({
                    "type": "missing_successful_tool_output",
                    "tool_name": tool_name,
                })
                checks.append(check_record)
                continue

            output_data = event.get("output_data")
            check_ok = True

            if "kind" in spec:
                kind_ok = event.get("output_kind") == spec["kind"]
                check_record["assertions"]["kind"] = {
                    "ok": kind_ok,
                    "expected": spec["kind"],
                    "actual": event.get("output_kind"),
                }
                check_ok = check_ok and kind_ok
                if not kind_ok:
                    issues.append({
                        "type": "kind_mismatch",
                        "tool_name": tool_name,
                        "expected": spec["kind"],
                        "actual": event.get("output_kind"),
                    })

            if "data_equals" in spec:
                data_equals_ok = output_data == spec["data_equals"]
                check_record["assertions"]["data_equals"] = {
                    "ok": data_equals_ok,
                    "expected": spec["data_equals"],
                    "actual": output_data,
                }
                check_ok = check_ok and data_equals_ok
                if not data_equals_ok:
                    issues.append({
                        "type": "data_equals_mismatch",
                        "tool_name": tool_name,
                        "expected": spec["data_equals"],
                        "actual": output_data,
                    })

            if "data_contains" in spec:
                data_contains_ok = self._contains_subset(output_data, spec["data_contains"])
                check_record["assertions"]["data_contains"] = {
                    "ok": data_contains_ok,
                    "expected_subset": spec["data_contains"],
                    "actual": output_data,
                }
                check_ok = check_ok and data_contains_ok
                if not data_contains_ok:
                    issues.append({
                        "type": "data_contains_mismatch",
                        "tool_name": tool_name,
                        "expected_subset": spec["data_contains"],
                        "actual": output_data,
                    })

            if "data_length" in spec:
                try:
                    actual_length = len(output_data)
                except Exception:
                    actual_length = None

                data_length_ok = actual_length == spec["data_length"]
                check_record["assertions"]["data_length"] = {
                    "ok": data_length_ok,
                    "expected": spec["data_length"],
                    "actual": actual_length,
                }
                check_ok = check_ok and data_length_ok
                if not data_length_ok:
                    issues.append({
                        "type": "data_length_mismatch",
                        "tool_name": tool_name,
                        "expected": spec["data_length"],
                        "actual": actual_length,
                    })

            check_record["ok"] = check_ok
            checks.append(check_record)

        unresolved = trace.get("unresolved_failed_tool_count")
        if expected.get("require_no_unresolved_tool_failures", True) and unresolved not in {0, None}:
            issues.append({
                "type": "unresolved_tool_failures",
                "actual": unresolved,
                "unresolved_failed_tools": trace.get("unresolved_failed_tools"),
            })

        return {
            "ok": len(issues) == 0,
            "checks": checks,
            "issues": issues,
        }

    def print_openai_audit(self, result: Any, *, trace_mode: str = "compact") -> None:
        print("=== OpenAI Agents SDK result.final_output ===")
        print(result.final_output)

        print("\n=== OpenAI Agents SDK tool outputs parsed ===")
        print(json.dumps(self.audit_openai_tool_outputs(result), indent=2, ensure_ascii=False))

        if trace_mode == "compact":
            print("\n=== OpenAI Agents SDK TRACE (compact) ===")
            print(json.dumps(self.openai_compact_trace(result), indent=2, ensure_ascii=False))

    # ---------------------------------------------------------------------
    # LangGraph bridge
    # ---------------------------------------------------------------------

    def as_langgraph_node(
        self,
        *,
        instructions: Optional[str] = None,
        tool_choice: Optional[str] = "auto",
        tool_names: Optional[Sequence[str]] = None,
        max_turns: int = 8,
        max_tool_calls: Optional[int] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        retry_tool_errors: bool = True,
        max_tool_error_repairs: int = 2,
        synthesize_final_on_max_turns: bool = True,
        required_tools: Optional[Sequence[str]] = None,
        stop_when_required_tools_ok: bool = False,
        input_key: str = "prompt",
        output_key: str = "final_text",
        trace_key: str = "ada_trace",
        trace_mode: str = "compact",
    ) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        """
        Export this runtime as a LangGraph-compatible node.

        The LangGraph node intentionally delegates to `run_direct()` so that
        LangGraph uses the same Bedrock tool loop, ToolEnvelope contract, and
        tracing shape as the Python-runtime runtime.

        Keep this bridge thin: LangGraph owns orchestration/state transitions;
        BedrockRuntime owns Bedrock Converse and tool execution.
        """

        def _node(state: Dict[str, Any]) -> Dict[str, Any]:
            prompt = state.get(input_key) or state.get("user_request") or state.get("input")
            if prompt is None:
                prompt = json.dumps(state, ensure_ascii=False)

            result = self.run_direct(
                str(prompt),
                instructions=instructions,
                tool_choice=tool_choice,
                tool_names=tool_names,
                max_turns=max_turns,
                max_tokens=max_tokens,
                temperature=temperature,
                retry_tool_errors=retry_tool_errors,
                max_tool_error_repairs=max_tool_error_repairs,
                synthesize_final_on_max_turns=synthesize_final_on_max_turns,
                required_tools=required_tools,
                stop_when_required_tools_ok=stop_when_required_tools_ok,
            )

            new_state = dict(state)
            new_state[output_key] = result.final_text
            new_state[trace_key] = result.trace(mode=trace_mode)
            return new_state

        return _node

def _has_running_event_loop() -> bool:
    """Return True when called from a thread with an active asyncio loop."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def _run_in_worker_thread(fn: Callable[[], Any]) -> Any:
    """Run a blocking function in a short-lived worker thread.

    This keeps sync APIs usable from notebooks without mutating global event
    loop policy. Exceptions raised by ``fn`` are propagated unchanged.
    """

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        return future.result()


__all__ = [
    "BedrockRuntime",
    "BedrockRunResult",
    "RuntimeToolCallRecord",
    "RuntimeToolSpec",
    "ToolEnvelope",
]
