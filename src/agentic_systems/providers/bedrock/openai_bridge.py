from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence


class _OpenAIBridgeMixin:
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

    def _openai_unresolved_failed_tools_from_input(
        self, input_data: Any
    ) -> List[Dict[str, Any]]:
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
                        "tool_name": prior.get("tool_name")
                        or parsed_output.get("tool_name")
                        or "unknown",
                        "ok": bool(parsed_output.get("ok")),
                        "input": prior.get("input", {}),
                        "output_kind": parsed_output.get("kind"),
                        "output_data": output_data,
                        "error_type": output_data.get("error_type")
                        if isinstance(output_data, dict)
                        else None,
                    }
                )

        return self._failure_semantics_from_tool_summaries(ordered_events)[
            "unresolved_failed_tools"
        ]

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

            if (
                role in {"system", "developer", "user", "assistant"}
                and "content" in item
            ):
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
                    if (
                        not isinstance(current, dict)
                        or current.get("type") != "function_call"
                    ):
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
                    if (
                        not isinstance(current, dict)
                        or current.get("type") != "function_call_output"
                    ):
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
                pending_call_ids = [
                    cid for cid in pending_call_ids if cid not in emitted_call_ids
                ]
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
                        "description": getattr(tool, "description", None)
                        or f"Tool {name}",
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
