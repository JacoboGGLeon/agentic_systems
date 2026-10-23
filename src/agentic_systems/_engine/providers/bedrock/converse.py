from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence


from .direct import _DirectRunner
from .models import BedrockRunResult, RuntimeToolCallRecord


class _ConverseMixin:
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
            "temperature": self.temperature_default
            if temperature is None
            else temperature,
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
            response.setdefault("agentic_systems", {})["client_duration_ms"] = (
                client_duration_ms
            )
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
            if (
                candidate in bedrock_to_canonical
                and bedrock_to_canonical[candidate] != spec.name
            ):
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

        return _ConverseMixin._map_tool_choice(requested_tool_choice)

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
                    "input": tool_input
                    if isinstance(tool_input, dict)
                    else {"value": tool_input},
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
                    tool_input=tool_input
                    if isinstance(tool_input, dict)
                    else {"value": tool_input},
                    tool_output=envelope.model_dump(mode="json"),
                    ok=False,
                )
            )

        return safe_content, valid_tool_uses, invalid_records

    # ---------------------------------------------------------------------
    # Bedrock runtime
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
        """Run Bedrock Converse directly with a local, repairable tool loop."""

        return _DirectRunner(
            self,
            prompt,
            instructions=instructions,
            model_id=model_id,
            tool_choice=tool_choice,
            tool_names=tool_names,
            max_turns=max_turns,
            max_tool_calls=max_tool_calls,
            max_tokens=max_tokens,
            temperature=temperature,
            retry_tool_errors=retry_tool_errors,
            max_tool_error_repairs=max_tool_error_repairs,
            synthesize_final_on_max_turns=synthesize_final_on_max_turns,
            required_tools=required_tools,
            stop_when_required_tools_ok=stop_when_required_tools_ok,
        ).run()

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
