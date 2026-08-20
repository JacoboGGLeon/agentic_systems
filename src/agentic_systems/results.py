"""Run result and trace schema for Agentic Systems 1.0."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from .contracts import AgentContract, ValidationResult, validate_tool_expectation
from .engines.names import BEDROCK_RUNTIME_ENGINE
from .final_answer import final_answer
from .tools.events import ToolEvent

TRACE_SCHEMA_VERSION = "agentic_systems.trace.v1"
RUN_SCHEMA_VERSION = "agentic_systems.run.v1"
TOOL_RESULT_SCHEMA_VERSION = "agentic_systems.tool_result.v1"


def _contains_subset(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(
            key in actual and _contains_subset(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        return all(
            any(_contains_subset(item, exp) for item in actual) for exp in expected
        )
    if isinstance(actual, str) and isinstance(expected, str):
        return expected in actual
    return actual == expected


def _classify_tool_failures(
    tool_events: list[ToolEvent],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    recovered: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for index, event in enumerate(tool_events):
        if event.ok:
            continue
        payload = event.model_dump(mode="json")
        recovery = next(
            (
                later
                for later in tool_events[index + 1 :]
                if later.name == event.name and later.ok
            ),
            None,
        )
        if recovery is None:
            unresolved.append(payload)
        else:
            recovered.append({**payload, "recovered_by_tool_event_id": recovery.id})
    return recovered, unresolved


def _append_unique_error(errors: list[dict[str, Any]], error: dict[str, Any]) -> None:
    identity = (
        error.get("code"),
        error.get("message"),
        error.get("path"),
        error.get("tool_event_id"),
    )
    if not any(
        (
            item.get("code"),
            item.get("message"),
            item.get("path"),
            item.get("tool_event_id"),
        )
        == identity
        for item in errors
    ):
        errors.append(error)


def _result_errors(result: "RunResult") -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if not result.ok and result.text:
        errors.append({"code": "run_failed", "message": result.text})
    recovered, _unresolved = _classify_tool_failures(result.tool_events)
    recovered_by_id = {
        item.get("id"): item.get("recovered_by_tool_event_id") for item in recovered
    }
    for event in result.tool_events:
        if event.ok:
            continue
        payload = (
            event.model_dump(mode="json")
            if hasattr(event, "model_dump")
            else dict(event)
        )
        error = payload.get("error") or payload.get("output") or {}
        recovered_by = recovered_by_id.get(payload.get("id"))
        entry = {
            "code": "tool_failed",
            "tool": payload.get("name"),
            "tool_event_id": payload.get("id"),
            "error": error,
            "resolved": recovered_by is not None,
        }
        if recovered_by is not None:
            entry["recovered_by_tool_event_id"] = recovered_by
        errors.append(entry)
    return errors


class RunResult(BaseModel):
    """Normalized result returned by every Agentic Systems engine."""

    model_config = ConfigDict(extra="forbid")

    text: str = ""
    final: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)
    ok: bool = True
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_events: list[ToolEvent] = Field(default_factory=list)
    raw_responses: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    engine: str = BEDROCK_RUNTIME_ENGINE
    model: str = ""
    mode: str = "default"
    trace_schema_version: str = TRACE_SCHEMA_VERSION
    validation: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    execution_id: str | None = None
    parent_execution_id: str | None = None
    children: list["RunResult"] = Field(default_factory=list)

    _native_result: Any = PrivateAttr(default=None)

    @property
    def native_result(self) -> Any:
        """Return the original Framework SDK result without serializing it."""
        return self._native_result

    def add_child(self, child: "RunResult") -> "RunResult":
        """Attach a child execution and preserve explicit parent lineage."""

        if not isinstance(child, RunResult):
            raise TypeError(f"Expected RunResult, got {type(child).__name__}.")
        if self.execution_id and child.parent_execution_id is None:
            child.parent_execution_id = self.execution_id
        self.children.append(child)
        return self

    def walk(self):
        """Yield this result and every descendant depth-first."""

        yield self
        for child in self.children:
            yield from child.walk()

    @model_validator(mode="after")
    def _ensure_final_answer(self) -> "RunResult":
        """Populate ``final`` when old call sites only set text/data.

        ``final`` is the user-facing answer payload.  ``data`` remains the
        reusable business/evidence payload, and runtime metadata stays in the
        rest of the envelope.
        """

        if not self.final:
            self.final = final_answer(self.data, text=self.text)
        if not self.errors:
            self.errors = _result_errors(self)
        if self.validation is not None:
            self.apply_validation(self.validation)
        return self

    @classmethod
    def from_bedrock_runtime(
        cls,
        runtime_result: Any,
        *,
        engine: str,
        model: str,
        mode: str = "default",
        data: dict[str, Any] | None = None,
        contract: AgentContract | dict[str, Any] | None = None,
    ) -> "RunResult":
        raw = (
            runtime_result.model_dump(mode="json")
            if hasattr(runtime_result, "model_dump")
            else dict(runtime_result)
        )
        raw_responses = raw.get("raw_responses") or []
        usage = _usage_totals(raw_responses)
        result = cls(
            text=str(raw.get("final_text") or raw.get("text") or ""),
            data=data or {},
            ok=bool(raw.get("final_text") or raw.get("text")),
            messages=raw.get("messages") or [],
            tool_events=[
                ToolEvent.from_runtime_record(item)
                for item in raw.get("tool_calls") or []
            ],
            raw_responses=raw_responses,
            usage=usage,
            engine=engine,
            model=model,
            mode=mode,
            meta={"source_result_type": type(runtime_result).__name__},
        )
        return result.apply_validation(result.validate(contract))

    def apply_validation(
        self, validation: ValidationResult | dict[str, Any]
    ) -> "RunResult":
        """Apply contract validation without allowing success to contradict it."""

        if isinstance(validation, ValidationResult):
            validation_payload = validation.to_dict()
            validation_issues = validation.issues
            validation_ok = validation.ok
        else:
            validation_payload = dict(validation)
            validation_ok = bool(validation_payload.get("ok", True))
            validation_issues = validation_payload.get("issues") or []

        self.validation = validation_payload
        self.ok = self.ok and validation_ok
        for issue in validation_issues:
            if hasattr(issue, "model_dump"):
                issue_payload = issue.model_dump(mode="json")
            elif isinstance(issue, dict):
                issue_payload = issue
            else:
                issue_payload = {"code": "validation_failed", "message": str(issue)}
            if issue_payload.get("severity", "error") != "error":
                continue
            self.ok = False
            validation_code = str(issue_payload.get("code") or "validation_failed")
            _append_unique_error(
                self.errors,
                {
                    "code": "validation_failed",
                    "message": str(issue_payload.get("message") or validation_code),
                    "path": issue_payload.get("path"),
                    "validation_code": validation_code,
                    "meta": issue_payload.get("meta") or {},
                },
            )
        return self

    def check_invariants(self) -> ValidationResult:
        """Return structural consistency issues without changing this result."""

        result = ValidationResult(ok=True)
        validation = self.validation or {}
        validation_issues = validation.get("issues") or []
        validation_has_errors = any(
            isinstance(issue, dict) and issue.get("severity", "error") == "error"
            for issue in validation_issues
        )
        if validation and validation.get("ok") is False and self.ok:
            result.add(
                "success_with_failed_validation",
                "RunResult.ok cannot be true when required contract validation failed.",
                path="ok",
            )
        if validation.get("ok") is True and validation_has_errors:
            result.add(
                "validation_status_mismatch",
                "RunResult.validation.ok is true but validation contains error-severity issues.",
                path="validation.ok",
            )

        event_ids = [event.id for event in self.tool_events if event.id]
        duplicate_ids = sorted(
            {event_id for event_id in event_ids if event_ids.count(event_id) > 1}
        )
        if duplicate_ids:
            result.add(
                "duplicate_tool_event_id",
                f"Tool event ids must be unique; duplicates: {duplicate_ids}.",
                path="tool_events",
                meta={"duplicate_ids": duplicate_ids},
            )
        for index, event in enumerate(self.tool_events):
            if event.ok and event.error:
                result.add(
                    "successful_tool_event_with_error",
                    f"Tool event '{event.id}' is successful but still carries an error.",
                    path=f"tool_events[{index}].error",
                )

        recovered, unresolved = _classify_tool_failures(self.tool_events)
        if self.ok and unresolved:
            result.add(
                "success_with_unresolved_tool_failure",
                "RunResult is successful with unresolved Tool failures; this is valid only under an explicit partial-failure policy.",
                severity="warning",
                path="tool_events",
                meta={"tool_event_ids": [item.get("id") for item in unresolved]},
            )
        if self.ok and self.errors:
            result.add(
                "success_with_recorded_errors",
                "RunResult is successful and contains errors; recorded errors must be recovered or allowed by policy.",
                severity="warning",
                path="errors",
            )
        if (
            not self.ok
            and not self.errors
            and not unresolved
            and not validation_has_errors
        ):
            result.add(
                "failure_without_error_evidence",
                "RunResult.ok is false but no error, failed validation, or unresolved Tool failure explains it.",
                severity="warning",
                path="errors",
            )

        for key, value in self.usage.items():
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and value < 0
            ):
                result.add(
                    "negative_usage_value",
                    f"Usage metric '{key}' cannot be negative; received {value}.",
                    path=f"usage.{key}",
                )

        if self.ok and not self.final and not self.data and not self.text:
            result.add(
                "success_without_answer",
                "Successful RunResult has no final, data, or text answer projection.",
                severity="warning",
                path="final",
            )

        try:
            self.model_dump(mode="json")
        except Exception as exc:  # noqa: BLE001 - report serialization failures as invariant issues.
            result.add(
                "not_json_serializable",
                f"RunResult must serialize in JSON mode: {type(exc).__name__}: {exc}",
                path="serialization",
            )

        result_meta = {
            "recovered_tool_error_count": len(recovered),
            "unresolved_tool_error_count": len(unresolved),
        }
        for issue in result.issues:
            issue.meta = {**result_meta, **issue.meta}
        return result

    def raise_if_inconsistent(self) -> "RunResult":
        """Raise a clear ValueError when structural RunResult invariants fail."""

        self.check_invariants().raise_if_failed()
        return self

    def normalized(self) -> dict[str, Any]:
        """Return the framework-agnostic run schema used by traces and notebooks.

        The schema is intentionally shared by JSON traces and the plain human
        view. That keeps direct tools, Bedrock agents, LangGraph and OpenAI
        Agents SDK comparable even when their raw runtimes return different
        object types.
        """

        runtime = {
            "engine": self.engine,
            "runtime_engine": self.meta.get("runtime_engine", self.engine),
            "framework": self.meta.get("framework"),
            "model": self.model,
            "mode": self.mode,
        }
        input_payload = self.meta.get("input")
        answer = {
            "text": self.text,
            "final": self.final,
            "data": self.data,
        }
        tools = [_normalize_tool_event(event) for event in self.tool_events]
        return {
            "schema_version": RUN_SCHEMA_VERSION,
            "ok": self.ok,
            "runtime": runtime,
            "input": input_payload,
            "answer": answer,
            "tools": tools,
            "usage": self.usage,
            "validation": self.validation,
            "errors": self.errors,
            "final": self.final,
            "blocks": {
                "user_input": input_payload,
                "runtime": runtime,
                "agent_answer": answer,
                "final_answer": self.final,
                "tool_actions": [
                    {
                        "name": tool.get("name"),
                        "ok": tool.get("ok"),
                        "input": tool.get("input"),
                        "summary": tool.get("summary"),
                        "route": tool.get("route"),
                        "query_id": tool.get("query_id"),
                        "row_count": tool.get("row_count"),
                    }
                    for tool in tools
                ],
                "sql": [
                    {"tool": tool.get("name"), "sql": tool.get("sql")}
                    for tool in tools
                    if tool.get("sql")
                ],
                "tables": [
                    {
                        "tool": tool.get("name"),
                        "row_count": tool.get("row_count"),
                        "rows": tool.get("rows"),
                    }
                    for tool in tools
                    if tool.get("rows")
                ],
                "usage": self.usage,
                "validation": self.validation,
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def lineage(self, **kwargs: Any):
        """Project this run into compact, explainable Lineage Memory."""

        from .lineage import LineageMemory

        return LineageMemory.from_run_result(self, **kwargs)

    def compact_trace(self) -> dict[str, Any]:
        return self.trace("compact")

    def trace(self, mode: str = "compact") -> dict[str, Any]:
        failed = [event for event in self.tool_events if not event.ok]
        recovered, unresolved = _classify_tool_failures(self.tool_events)

        compact = {
            "trace_schema_version": self.trace_schema_version,
            "run_ok": self.ok,
            "engine": self.engine,
            "model": self.model,
            "mode": self.mode,
            "text": self.text,
            "data": self.data,
            "turns": len(self.raw_responses),
            "message_count": len(self.messages),
            "tool_event_count": len(self.tool_events),
            "successful_tool_count": len(
                [event for event in self.tool_events if event.ok]
            ),
            "failed_tool_event_count": len(failed),
            "recovered_tool_error_count": len(recovered),
            "unresolved_failed_tool_count": len(unresolved),
            "tool_events": [
                event.model_dump(mode="json") for event in self.tool_events
            ],
            "normalized": self.normalized(),
            "recovered_tool_errors": recovered,
            "unresolved_failed_tools": unresolved,
            "usage": self.usage,
            "validation": self.validation,
            "errors": self.errors,
            "final": self.final,
        }
        if mode == "compact":
            return compact
        if mode == "full":
            full = self.to_dict()
            full["compact"] = compact
            return full
        raise ValueError("mode must be 'compact' or 'full'")

    def validate(
        self, contract: AgentContract | dict[str, Any] | None = None
    ) -> ValidationResult:
        contract_obj = AgentContract.coerce(contract)
        result = ValidationResult(ok=True)
        called = [event.name for event in self.tool_events]

        for name in contract_obj.must_call:
            if name not in called:
                result.add(
                    "missing_required_tool",
                    f"Required tool '{name}' was not called.",
                    path="contract.must_call",
                    meta={"called_tools": called},
                )

        for name in contract_obj.must_not_call:
            if name in called:
                result.add(
                    "forbidden_tool_called",
                    f"Forbidden tool '{name}' was called.",
                    path="contract.must_not_call",
                )

        if contract_obj.tool_expectation:
            tool_check = validate_tool_expectation(
                called, contract_obj.tool_expectation
            )
            for issue in tool_check.get("issues", []):
                result.add(
                    str(issue.get("code") or "tool_expectation_failed"),
                    str(issue.get("message") or "Tool expectation failed."),
                    path="contract.tool_expectation",
                    meta={
                        "called_tools": called,
                        "expectation": tool_check.get("expectation"),
                        "issue": issue,
                    },
                )

        if contract_obj.failure_policy in {"no_unresolved", "fail_fast"}:
            for idx, event in enumerate(self.tool_events):
                if event.ok:
                    continue
                recovered = any(
                    later.name == event.name and later.ok
                    for later in self.tool_events[idx + 1 :]
                )
                if not recovered:
                    result.add(
                        "unresolved_tool_failure",
                        f"Tool '{event.name}' failed and was not recovered.",
                        path="tool_events",
                        meta={"tool_event_id": event.id, "error": event.error or {}},
                    )

        if contract_obj.expected_output is not None and not _contains_subset(
            self.data or {"text": self.text}, contract_obj.expected_output
        ):
            result.add(
                "expected_output_mismatch",
                "Run output does not contain the expected subset.",
                path="data",
                meta={"expected": contract_obj.expected_output, "actual": self.data},
            )

        for tool_name, expected_subset in contract_obj.expected_tool_outputs.items():
            matching = [
                event
                for event in self.tool_events
                if event.name == tool_name and event.ok
            ]
            if not matching:
                result.add(
                    "expected_tool_output_missing_tool",
                    f"No successful output found for expected tool '{tool_name}'.",
                    path="contract.expected_tool_outputs",
                )
                continue
            if not any(
                _contains_subset(
                    event.output.get("data", event.output), expected_subset
                )
                for event in matching
            ):
                result.add(
                    "expected_tool_output_mismatch",
                    f"Tool '{tool_name}' output does not contain expected subset.",
                    path=f"tool_events.{tool_name}",
                    meta={"expected": expected_subset},
                )

        return result


def _usage_totals(raw_responses: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, Any] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "requests": len(raw_responses),
    }
    service_latency_ms = 0.0
    service_latency_count = 0
    client_duration_ms = 0.0
    client_duration_count = 0

    for raw in raw_responses:
        usage = raw.get("usage", {}) or {}
        totals["input_tokens"] += int(
            usage.get("inputTokens", usage.get("input_tokens", 0)) or 0
        )
        totals["output_tokens"] += int(
            usage.get("outputTokens", usage.get("output_tokens", 0)) or 0
        )
        totals["total_tokens"] += int(
            usage.get("totalTokens", usage.get("total_tokens", 0)) or 0
        )

        service_value = _coerce_number(raw.get("service_latency_ms"))
        if service_value is not None:
            service_latency_ms += service_value
            service_latency_count += 1

        client_value = _coerce_number(raw.get("client_duration_ms"))
        if client_value is not None:
            client_duration_ms += client_value
            client_duration_count += 1

    if service_latency_count:
        totals["service_latency_ms"] = round(service_latency_ms, 3)
    if client_duration_count:
        totals["client_duration_ms"] = round(client_duration_ms, 3)
    return totals


def _coerce_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _tool_summary(payload: dict[str, Any]) -> str:
    if payload.get("summary"):
        return str(payload["summary"])
    if payload.get("error"):
        return str(payload["error"])
    if payload.get("text"):
        return str(payload["text"])
    important = {
        key: payload[key] for key in ("operation", "result", "value") if key in payload
    }
    if important:
        import json

        return json.dumps(important, ensure_ascii=False, default=str)
    if payload:
        import json

        return json.dumps(payload, ensure_ascii=False, default=str)[:220]
    return ""


def _normalize_tool_event(event: ToolEvent) -> dict[str, Any]:
    raw = event.model_dump(mode="json")
    output = raw.get("output") or {}
    payload = (
        output.get("data")
        if isinstance(output, dict) and isinstance(output.get("data"), dict)
        else output
    )
    if not isinstance(payload, dict):
        payload = {"value": payload}
    table = payload.get("table") if isinstance(payload.get("table"), dict) else {}
    query = payload.get("query") if isinstance(payload.get("query"), dict) else {}
    return {
        "schema_version": TOOL_RESULT_SCHEMA_VERSION,
        "id": event.id,
        "name": event.name or payload.get("tool") or "tool",
        "ok": event.ok,
        "input": event.input,
        "output": payload,
        "summary": _tool_summary(payload),
        "route": payload.get("route"),
        "query_id": query.get("query_id"),
        "sql": payload.get("sql"),
        "row_count": table.get("n_rows"),
        "columns": table.get("columns") or [],
        "rows": table.get("rows") or [],
        "error": event.error,
        "duration_ms": event.duration_ms,
    }
