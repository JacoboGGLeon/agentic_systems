from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Type

from pydantic import BaseModel, ConfigDict, Field


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
                output_data.get("error_type") if isinstance(output_data, dict) else None
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

        failed_tool_events = [tool for tool in tool_summaries if not tool.get("ok")]

        recovered_tool_errors: List[Dict[str, Any]] = []
        unresolved_failed_tools: List[Dict[str, Any]] = []

        for failed in failed_tool_events:
            failed_index = int(failed.get("index", -1))
            failed_name = failed.get("tool_name")

            recovery = next(
                (
                    tool
                    for tool in tool_summaries
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
            "successful_tool_count": len(
                [tool for tool in tool_summaries if tool.get("ok")]
            ),
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
