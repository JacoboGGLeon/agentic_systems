from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional, Sequence


class _LangGraphMixin:
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
        tracing shape as the Bedrock runtime.

        Keep this bridge thin: LangGraph owns orchestration/state transitions;
        BedrockRuntime owns Bedrock Converse and tool execution.
        """

        def _node(state: Dict[str, Any]) -> Dict[str, Any]:
            prompt = (
                state.get(input_key) or state.get("user_request") or state.get("input")
            )
            if prompt is None:
                prompt = json.dumps(state, ensure_ascii=False)

            result = self.run_direct(
                str(prompt),
                instructions=instructions,
                tool_choice=tool_choice,
                max_tool_calls=max_tool_calls,
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
