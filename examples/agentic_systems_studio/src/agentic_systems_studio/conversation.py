"""Provider/framework-agnostic conversational reference system for Studio."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import math
import os
from typing import Any, Mapping, Sequence

import agentic_systems as toolkit
from agentic_systems.registry import (
    FRAMEWORK_NAMES,
    PROVIDER_NAMES,
    provider_capability,
)
from agentic_systems_studio.environment import load_studio_environment


_BINARY_OPERATORS = {
    ast.Add: lambda left, right: left + right,
    ast.Sub: lambda left, right: left - right,
    ast.Mult: lambda left, right: left * right,
    ast.Div: lambda left, right: left / right,
    ast.Mod: lambda left, right: left % right,
    ast.Pow: lambda left, right: left**right,
}
_UNARY_OPERATORS = {
    ast.UAdd: lambda value: +value,
    ast.USub: lambda value: -value,
}
_MAX_ABSOLUTE_VALUE = 1_000_000_000_000
_MAX_AST_NODES = 32


def _bounded_number(value: int | float) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Only finite integer and floating-point values are supported")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Only finite values are supported")
    if abs(value) > _MAX_ABSOLUTE_VALUE:
        raise ValueError("Arithmetic value exceeds the supported safety bound")
    return value


def _evaluate_expression(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _evaluate_expression(node.body)
    if isinstance(node, ast.Constant):
        return _bounded_number(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_expression(node.left)
        right = _evaluate_expression(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 12 or abs(left) > 1_000_000):
            raise ValueError("Exponentiation exceeds the supported safety bound")
        operation = _BINARY_OPERATORS[type(node.op)]
        return _bounded_number(operation(left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _bounded_number(
            _UNARY_OPERATORS[type(node.op)](_evaluate_expression(node.operand))
        )
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


@toolkit.tool
def safe_calculate(expression: str) -> dict[str, Any]:
    """Evaluate arithmetic without eval, imports, names or attribute access."""

    normalized = expression.strip().replace("^", "**")
    if not normalized or len(normalized) > 256:
        raise ValueError("expression must contain between 1 and 256 characters")
    parsed = ast.parse(normalized, mode="eval")
    if sum(1 for _ in ast.walk(parsed)) > _MAX_AST_NODES:
        raise ValueError("expression exceeds the supported structural complexity")
    value = _evaluate_expression(parsed)
    return {
        "expression": expression,
        "normalized_expression": normalized,
        "result": value,
        "verified_by": "python-runtime::safe_calculate",
    }


@toolkit.tool
def prepare_conversation_context(
    messages: list[dict[str, str]],
    message: str,
) -> dict[str, Any]:
    """Produce a bounded, deterministic context envelope for one chat turn."""

    bounded = []
    for item in messages[-12:]:
        role = str(item.get("role", "user"))
        content = str(item.get("content", ""))[:4000]
        if role in {"user", "assistant"} and content:
            bounded.append({"role": role, "content": content})
    return {
        "message": message[:8000],
        "history": bounded,
        "history_turns": len(bounded),
        "policy": {
            "reasoning_is_private": True,
            "no_silent_fallback": True,
            "tools_are_evidence": True,
        },
    }


@dataclass(frozen=True)
class ConversationConfig:
    """Environment-first configuration shared by the UI and notebook."""

    provider: str = "auto"
    framework: str = "native"
    model: str | None = None
    timeout_s: float = 120.0
    max_turns: int = 6
    max_tool_calls: int = 4
    max_tokens: int = 1024

    def __post_init__(self) -> None:
        if self.provider not in {"auto", *PROVIDER_NAMES}:
            raise ValueError(f"Unknown provider: {self.provider!r}")
        if self.framework not in {"agentic-systems", *FRAMEWORK_NAMES}:
            raise ValueError(f"Unknown framework: {self.framework!r}")
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be greater than zero")
        if self.max_turns < 1 or self.max_tokens < 1 or self.max_tool_calls < 0:
            raise ValueError(
                "turns/tokens must be positive and tool calls non-negative"
            )

    @classmethod
    def from_environment(cls) -> "ConversationConfig":
        # The single Studio .env is canonical; managed credentials not declared
        # there remain inherited from the hosting environment.
        load_studio_environment()
        return cls(
            provider=os.getenv("AGENTIC_SYSTEMS_PROVIDER", "auto"),
            framework=os.getenv("AGENTIC_SYSTEMS_FRAMEWORK", "native"),
            model=os.getenv("AGENTIC_SYSTEMS_MODEL") or None,
            timeout_s=float(os.getenv("AGENTIC_SYSTEMS_TIMEOUT_S", "120")),
            max_turns=int(os.getenv("AGENTIC_SYSTEMS_MAX_TURNS", "6")),
            max_tool_calls=int(os.getenv("AGENTIC_SYSTEMS_MAX_TOOL_CALLS", "4")),
            max_tokens=int(os.getenv("AGENTIC_SYSTEMS_MAX_TOKENS", "1024")),
        )

    @property
    def framework_value(self) -> str | None:
        return (
            None
            if self.framework in {"", "agentic-systems", "native"}
            else self.framework
        )

    def reasoning_runtime(self):
        return toolkit.runtime(
            provider=self.provider,
            model=self.model,
            scheduler=toolkit.scheduler(
                timeout_s=self.timeout_s,
                max_turns=self.max_turns,
                max_tool_calls=self.max_tool_calls,
            ),
        )

    def deterministic_runtime(self):
        return toolkit.runtime(
            provider="python-runtime",
            scheduler=toolkit.scheduler(
                timeout_s=min(self.timeout_s, 30.0),
                max_turns=2,
                max_tool_calls=1,
            ),
        )


@dataclass
class ConversationalStudio:
    """One portable conversational system with deterministic evidence boundaries."""

    config: ConversationConfig
    reasoning_system: Any
    deterministic_system: Any
    assistant: Any
    context_agent: Any

    def inspect(self) -> dict[str, Any]:
        return {
            "configuration": {
                "provider": self.config.provider,
                "framework": self.config.framework,
                "model": self.config.model,
            },
            "deterministic_system": self.deterministic_system.inspect().to_dict(),
            "reasoning_system": self.reasoning_system.inspect().to_dict(),
            "agents": [self.context_agent.info(), self.assistant.info()],
        }

    def run(
        self,
        message: str,
        *,
        history: Sequence[Mapping[str, Any]] = (),
    ) -> toolkit.RunResult:
        public_history = [
            {
                "role": str(item.get("role", "user")),
                "content": str(item.get("content", "")),
            }
            for item in history
        ]
        context_result = self.context_agent.run(
            {
                "tool": "prepare_conversation_context",
                "input": {"messages": public_history, "message": message},
            },
        )
        context = dict(context_result.data)
        assistant_result = self.assistant.run(
            "Respond to the current user message using the bounded conversation context. "
            "Call safe_calculate when arithmetic evidence is useful. Never expose private "
            "reasoning and never claim that an uncalled tool was executed.\n\n"
            + json.dumps(context, ensure_ascii=False),
        )
        result = toolkit.compose_result(
            text=assistant_result.text,
            data={
                "answer": assistant_result.text,
                "context_summary": {
                    "history_turns": context.get("history_turns", 0),
                    "policy": context.get("policy", {}),
                },
                "provider": self.config.provider,
                "framework": self.config.framework,
            },
            results=[context_result, assistant_result],
            mode=assistant_result.mode,
            framework=self.config.framework,
            input=message,
            engine=assistant_result.engine,
            model=assistant_result.model,
            meta={"studio_application": "conversational"},
        )
        result.check_invariants()
        return result


def build_conversational_system(
    config: ConversationConfig | None = None,
) -> ConversationalStudio:
    """Build the same system used by the notebook and Streamlit UI."""

    selected = config or ConversationConfig.from_environment()
    if selected.provider != "auto" and (
        provider_capability(selected.provider, "model_generation").status
        == "unsupported"
    ):
        raise ValueError(
            "The conversational Studio requires a reasoning provider or provider='auto'."
        )

    deterministic = toolkit.system(runtime=selected.deterministic_runtime())
    context_agent = deterministic.agent(
        name="conversation.context",
        instructions="Create the deterministic context envelope for this turn.",
        tools=[prepare_conversation_context],
        contract=toolkit.AgentContract(
            must_call=["prepare_conversation_context"],
            completion="when_required_tools_satisfied",
        ),
        policy=toolkit.RunPolicy(
            max_turns=2, max_tool_calls=1, tool_choice="prepare_conversation_context"
        ),
    )

    reasoning = toolkit.system(
        runtime=selected.reasoning_runtime(), model=selected.model
    )
    assistant = reasoning.agent(
        name="conversation.assistant",
        instructions=(
            "You are a concise, evidence-aware conversational assistant. Preserve context, "
            "use deterministic tools when they add evidence, and never expose private reasoning."
        ),
        tools=[safe_calculate],
        engine=selected.provider,
        framework=selected.framework_value,
        model=selected.model,
        policy=toolkit.RunPolicy(
            max_turns=selected.max_turns,
            max_tool_calls=selected.max_tool_calls,
            max_tokens=selected.max_tokens,
            tool_choice="auto",
        ),
    )

    for system in (deterministic, reasoning):
        system.inspect().raise_if_errors()

    return ConversationalStudio(
        config=selected,
        reasoning_system=reasoning,
        deterministic_system=deterministic,
        assistant=assistant,
        context_agent=context_agent,
    )


__all__ = [
    "ConversationConfig",
    "ConversationalStudio",
    "build_conversational_system",
    "prepare_conversation_context",
    "safe_calculate",
]
