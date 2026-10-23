"""Stateful implementation of the Bedrock Converse tool loop."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from .models import BedrockRunResult, RuntimeToolCallRecord


class _DirectRunner:
    """Execute one direct Bedrock run while keeping orchestration methods small."""

    _RECOVERABLE_ERROR_TYPES = {"ValidationError", "UnknownToolError"}

    def __init__(
        self,
        runtime: Any,
        prompt: str,
        *,
        instructions: Optional[str],
        model_id: Optional[str],
        tool_choice: Optional[str],
        tool_names: Optional[Sequence[str]],
        max_turns: int,
        max_tool_calls: Optional[int],
        max_tokens: Optional[int],
        temperature: Optional[float],
        retry_tool_errors: bool,
        max_tool_error_repairs: int,
        synthesize_final_on_max_turns: bool,
        required_tools: Optional[Sequence[str]],
        stop_when_required_tools_ok: bool,
    ) -> None:
        self.runtime = runtime
        self.prompt = prompt
        self.tool_choice = tool_choice
        self.max_turns = max_turns
        self.max_tool_calls = max_tool_calls
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.retry_tool_errors = retry_tool_errors
        self.max_tool_error_repairs = max_tool_error_repairs
        self.synthesize_final_on_max_turns = synthesize_final_on_max_turns
        self.stop_when_required_tools_ok = stop_when_required_tools_ok
        self.messages: List[Dict[str, Any]] = [
            {"role": "user", "content": [{"text": prompt}]}
        ]
        self.system = [{"text": instructions}] if instructions else None
        self.model_id = model_id or runtime.model_id
        self.canonical_to_bedrock, self.bedrock_to_canonical = (
            runtime._bedrock_tool_name_maps(tool_names)
        )
        self.bedrock_tools = runtime.as_bedrock_tools(
            tool_names,
            canonical_to_bedrock=self.canonical_to_bedrock,
        )
        self.final_text_parts: List[str] = []
        self.tool_records: List[RuntimeToolCallRecord] = []
        self.raw_responses: List[Dict[str, Any]] = []
        self.repair_attempts = 0
        self.force_tool_retry_next_turn = False
        self.required_tool_names = {
            str(name) for name in (required_tools or []) if str(name).strip()
        }

    def run(self) -> BedrockRunResult:
        for turn_index in range(self.max_turns):
            completed = self._run_turn(turn_index)
            if completed is not None:
                return completed

        final_text = self._joined_final_text()
        if self.synthesize_final_on_max_turns and not final_text and self.messages:
            synthesized = self._synthesize_final_answer(
                "The maximum tool-loop turns were reached."
            )
            if synthesized is not None:
                return synthesized
            final_text = self._joined_final_text()
        return self._result(final_text)

    def _run_turn(self, turn_index: int) -> Optional[BedrockRunResult]:
        response = self.runtime.converse(
            messages=self.messages,
            model_id=self.model_id,
            system=self.system,
            tools=self.bedrock_tools or None,
            tool_choice=self._choice_for_turn(turn_index),
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        self.raw_responses.append(self.runtime._compact_response_metadata(response))
        content = response.get("output", {}).get("message", {}).get("content", [])
        self.final_text_parts.extend(
            str(block["text"]) for block in content if block.get("text")
        )
        safe_content, tool_uses, invalid_records = (
            self.runtime._sanitize_bedrock_assistant_content(content)
        )
        self.tool_records.extend(invalid_records)
        if invalid_records and not tool_uses and not self.final_text_parts:
            self.final_text_parts.append(
                "[BedrockRuntime] El modelo emitió un toolUse inválido "
                "sin nombre de tool. Se detuvo el loop antes de reenviar "
                "historial inválido a Bedrock."
            )
        if not tool_uses:
            return self._result(
                self._joined_final_text(),
                extra_messages=[{"role": "assistant", "content": safe_content}],
            )

        self.messages.append({"role": "assistant", "content": safe_content})
        tool_result_blocks, recoverable_failures = self._execute_tool_uses(tool_uses)
        should_retry = (
            self.retry_tool_errors
            and bool(recoverable_failures)
            and self.repair_attempts < self.max_tool_error_repairs
        )
        if should_retry:
            self.repair_attempts += 1
            self.force_tool_retry_next_turn = True
            tool_result_blocks.append(self._repair_instruction(recoverable_failures))
        else:
            self.force_tool_retry_next_turn = False
        self.messages.append({"role": "user", "content": tool_result_blocks})

        if self.stop_when_required_tools_ok and self._required_tools_are_ok():
            return self._synthesize_final_answer(
                "All caller-declared required tools have successful ToolEnvelope evidence."
            )
        return None

    def _choice_for_turn(self, turn_index: int) -> Optional[Dict[str, Any]]:
        if not self.bedrock_tools:
            return None
        requested = self.tool_choice
        if isinstance(requested, str) and requested not in {"auto", "required", "any"}:
            requested = self.canonical_to_bedrock.get(requested, requested)
        if self.force_tool_retry_next_turn:
            return {"any": {}}
        return self.runtime._tool_choice_for_turn(requested, turn_index=turn_index)

    def _execute_tool_uses(
        self,
        tool_uses: Sequence[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        result_blocks: List[Dict[str, Any]] = []
        failures: List[Dict[str, Any]] = []
        for tool_use in tool_uses:
            result_block, failure = self._execute_tool_use(tool_use)
            result_blocks.append(result_block)
            if failure is not None:
                failures.append(failure)
        return result_blocks, failures

    def _execute_tool_use(
        self,
        tool_use: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        tool_use_id = tool_use["toolUseId"]
        bedrock_tool_name = tool_use["name"]
        tool_name = self.bedrock_to_canonical.get(bedrock_tool_name, bedrock_tool_name)
        tool_input = tool_use.get("input", {}) or {}
        if (
            self.max_tool_calls is not None
            and len(self.tool_records) >= self.max_tool_calls
        ):
            envelope = self.runtime.to_envelope(
                {
                    "error_type": "MaxToolCallsExceeded",
                    "message": f"The run exceeded max_tool_calls={self.max_tool_calls}.",
                    "requested_tool": tool_name,
                },
                tool_name=tool_name,
                ok=False,
                extra_meta={"bedrock_tool_name": bedrock_tool_name},
            )
        else:
            envelope = self.runtime.execute_tool(tool_name, tool_input)
        envelope_dict = envelope.model_dump(mode="json")
        if bedrock_tool_name != tool_name:
            envelope_dict.setdefault("meta", {})["bedrock_tool_name"] = (
                bedrock_tool_name
            )
            envelope_dict.setdefault("meta", {})["canonical_tool_name"] = tool_name

        tool_result: Dict[str, Any] = {
            "toolUseId": tool_use_id,
            "content": [{"json": envelope_dict}],
        }
        if not envelope.ok:
            tool_result["status"] = "error"
        self.tool_records.append(
            RuntimeToolCallRecord(
                tool_use_id=tool_use_id,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=envelope_dict,
                ok=envelope.ok,
                meta={"bedrock_tool_name": bedrock_tool_name}
                if bedrock_tool_name != tool_name
                else {},
            )
        )
        return {"toolResult": tool_result}, self._recoverable_failure(
            tool_use_id, tool_name, tool_input, envelope_dict
        )

    def _recoverable_failure(
        self,
        tool_use_id: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        envelope: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        error_type = self._tool_error_type(envelope)
        if (
            envelope.get("ok") is not False
            or error_type not in self._RECOVERABLE_ERROR_TYPES
        ):
            return None
        data = envelope.get("data")
        return {
            "tool_use_id": tool_use_id,
            "tool_name": tool_name,
            "input": tool_input,
            "error_type": error_type,
            "error_message": data.get("message") if isinstance(data, dict) else None,
        }

    def _synthesize_final_answer(self, reason: str) -> Optional[BedrockRunResult]:
        evidence = [
            {
                "index": index,
                "tool_name": record.tool_name,
                "ok": record.ok,
                "input": self.runtime._make_jsonable(record.tool_input),
                "output": self.runtime._make_jsonable(record.tool_output),
            }
            for index, record in enumerate(self.tool_records)
        ]
        payload = {
            "reason": reason,
            "original_prompt": self.prompt,
            "tool_evidence": evidence,
        }
        synthesis_content = [
            {
                "text": (
                    "BedrockRuntime final synthesis instruction:\n"
                    "Do not call tools. Produce the final user-facing answer requested by "
                    "the original prompt using only this JSON ToolEnvelope evidence. If a "
                    "required value is unavailable, state that explicitly.\n\n"
                    f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
                )
            }
        ]
        try:
            response = self.runtime.converse(
                messages=[{"role": "user", "content": synthesis_content}],
                model_id=self.model_id,
                system=self.system,
                tools=None,
                tool_choice=None,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            self.raw_responses.append(self.runtime._compact_response_metadata(response))
            assistant_content = (
                response.get("output", {}).get("message", {}).get("content", [])
            )
            text = "\n".join(
                str(block.get("text"))
                for block in assistant_content
                if isinstance(block, dict) and block.get("text")
            ).strip()
            if text:
                return self._result(
                    text,
                    extra_messages=[
                        {"role": "user", "content": synthesis_content},
                        {"role": "assistant", "content": assistant_content},
                    ],
                )
        except Exception:
            return None
        return None

    def _result(
        self,
        final_text: str,
        *,
        extra_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> BedrockRunResult:
        return BedrockRunResult(
            final_text=final_text,
            messages=self.messages + (extra_messages or []),
            tool_calls=self.tool_records,
            raw_responses=self.raw_responses,
        )

    def _required_tools_are_ok(self) -> bool:
        if not self.required_tool_names:
            return False
        successful = {record.tool_name for record in self.tool_records if record.ok}
        return self.required_tool_names.issubset(successful)

    @staticmethod
    def _tool_error_type(envelope: Dict[str, Any]) -> Optional[str]:
        data = envelope.get("data")
        if isinstance(data, dict):
            error_type = data.get("error_type")
            return str(error_type) if error_type else None
        return None

    @staticmethod
    def _repair_instruction(failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "text": (
                "BedrockRuntime repair instruction:\n"
                "One or more tool calls failed with recoverable input errors. Do not "
                "produce a final answer yet. Correct the failed tool call(s) using the "
                "provided tool schema and call the appropriate tool again. Failed calls:\n"
                f"{json.dumps(failures, ensure_ascii=False)}"
            )
        }

    def _joined_final_text(self) -> str:
        return "\n".join(part for part in self.final_text_parts if part).strip()
