from __future__ import annotations

import json
from typing import Any, Dict, List


class _ValidationMixin:
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

                totals["input_tokens"] += self._get_usage_field(
                    usage, "input_tokens", "inputTokens"
                )
                totals["output_tokens"] += self._get_usage_field(
                    usage, "output_tokens", "outputTokens"
                )
                totals["total_tokens"] += self._get_usage_field(
                    usage, "total_tokens", "totalTokens"
                )
                totals["requests"] += self._get_usage_field(usage, "requests") or 1

            return totals

        usage = getattr(result, "usage", None)
        if usage is None and isinstance(result, dict):
            usage = result.get("usage")

        if usage is not None:
            totals["input_tokens"] = self._get_usage_field(
                usage, "input_tokens", "inputTokens"
            )
            totals["output_tokens"] = self._get_usage_field(
                usage, "output_tokens", "outputTokens"
            )
            totals["total_tokens"] = self._get_usage_field(
                usage, "total_tokens", "totalTokens"
            )
            totals["requests"] = self._get_usage_field(usage, "requests") or 1

        return totals

    @staticmethod
    def _failure_semantics_from_tool_summaries(
        tool_summaries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Classify historical, recovered, and unresolved tool failures."""

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
            "successful_tool_count": len(
                [tool for tool in ordered_events if tool.get("ok")]
            ),
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
                if not _ValidationMixin._contains_subset(actual[key], expected_value):
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
                "issues": [
                    {
                        "type": "invalid_trace",
                        "message": "Trace must be a dict.",
                    }
                ],
            }

        if expected.get("require_run_ok", True) and trace.get("run_ok") is not True:
            issues.append(
                {
                    "type": "run_not_ok",
                    "actual": trace.get("run_ok"),
                }
            )

        final_text = str(trace.get("final_text") or "")
        for needle in expected.get("final_text_contains", []) or []:
            needle_text = str(needle)
            contains_ok = needle_text.lower() in final_text.lower()
            if not contains_ok:
                issues.append(
                    {
                        "type": "final_text_missing_substring",
                        "expected_substring": needle_text,
                    }
                )

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
                issues.append(
                    {
                        "type": "missing_successful_tool_output",
                        "tool_name": tool_name,
                    }
                )
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
                    issues.append(
                        {
                            "type": "kind_mismatch",
                            "tool_name": tool_name,
                            "expected": spec["kind"],
                            "actual": event.get("output_kind"),
                        }
                    )

            if "data_equals" in spec:
                data_equals_ok = output_data == spec["data_equals"]
                check_record["assertions"]["data_equals"] = {
                    "ok": data_equals_ok,
                    "expected": spec["data_equals"],
                    "actual": output_data,
                }
                check_ok = check_ok and data_equals_ok
                if not data_equals_ok:
                    issues.append(
                        {
                            "type": "data_equals_mismatch",
                            "tool_name": tool_name,
                            "expected": spec["data_equals"],
                            "actual": output_data,
                        }
                    )

            if "data_contains" in spec:
                data_contains_ok = self._contains_subset(
                    output_data, spec["data_contains"]
                )
                check_record["assertions"]["data_contains"] = {
                    "ok": data_contains_ok,
                    "expected_subset": spec["data_contains"],
                    "actual": output_data,
                }
                check_ok = check_ok and data_contains_ok
                if not data_contains_ok:
                    issues.append(
                        {
                            "type": "data_contains_mismatch",
                            "tool_name": tool_name,
                            "expected_subset": spec["data_contains"],
                            "actual": output_data,
                        }
                    )

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
                    issues.append(
                        {
                            "type": "data_length_mismatch",
                            "tool_name": tool_name,
                            "expected": spec["data_length"],
                            "actual": actual_length,
                        }
                    )

            check_record["ok"] = check_ok
            checks.append(check_record)

        unresolved = trace.get("unresolved_failed_tool_count")
        if expected.get(
            "require_no_unresolved_tool_failures", True
        ) and unresolved not in {0, None}:
            issues.append(
                {
                    "type": "unresolved_tool_failures",
                    "actual": unresolved,
                    "unresolved_failed_tools": trace.get("unresolved_failed_tools"),
                }
            )

        return {
            "ok": len(issues) == 0,
            "checks": checks,
            "issues": issues,
        }

    def print_openai_audit(self, result: Any, *, trace_mode: str = "compact") -> None:
        print("=== OpenAI Agents SDK result.final_output ===")
        print(result.final_output)

        print("\n=== OpenAI Agents SDK tool outputs parsed ===")
        print(
            json.dumps(
                self.audit_openai_tool_outputs(result), indent=2, ensure_ascii=False
            )
        )

        if trace_mode == "compact":
            print("\n=== OpenAI Agents SDK TRACE (compact) ===")
            print(
                json.dumps(
                    self.openai_compact_trace(result), indent=2, ensure_ascii=False
                )
            )

    # ---------------------------------------------------------------------
    # LangGraph bridge
    # ---------------------------------------------------------------------
