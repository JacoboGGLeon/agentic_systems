"""Bedrock Converse engine backed by the internal Agentic Systems runtime."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from agentic_systems.contracts import RunPolicy
from agentic_systems.engines.names import BEDROCK_RUNTIME_ENGINE
from agentic_systems.results import RunResult


class BedrockEngine:
    name = BEDROCK_RUNTIME_ENGINE

    def __init__(self, system: Any) -> None:
        self.system = system

    def run(self, agent: Any, input: Any, policy: RunPolicy, *, mode: str = "default") -> RunResult:
        """Run Bedrock Converse through the runtime's native synchronous path."""

        prompt = _input_to_prompt(input)
        contract = agent.contract
        stop_when_required = contract.completion in {
            "when_contract_satisfied",
            "when_required_tools_satisfied",
        }
        runtime_result = self.system._runtime.run_direct(
            prompt,
            instructions=agent.instructions,
            model_id=agent.model or self.system.model,
            tool_choice=policy.tool_choice,
            tool_names=list(agent.tools) or None,
            max_turns=policy.max_turns,
            max_tool_calls=policy.max_tool_calls,
            max_tokens=policy.max_tokens,
            temperature=policy.temperature,
            retry_tool_errors=policy.repair,
            max_tool_error_repairs=policy.max_repairs,
            synthesize_final_on_max_turns=policy.finalize != "never",
            required_tools=list(contract.must_call) or None,
            stop_when_required_tools_ok=stop_when_required,
        )
        return RunResult.from_bedrock_runtime(
            runtime_result,
            engine=self.name,
            model=agent.model or self.system.model,
            mode=mode,
            contract=contract,
        )

    async def arun(self, agent: Any, input: Any, policy: RunPolicy, *, mode: str = "default") -> RunResult:
        """Run Bedrock from async apps without blocking the caller's event loop."""

        return await asyncio.to_thread(self.run, agent, input, policy, mode=mode)


def _input_to_prompt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        return str(value)
