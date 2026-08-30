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


@toolkit.tool
def hello_world(message: str) -> dict[str, Any]:
    """Return a deterministic offline Studio response with public evidence."""

    return {
        "message": (
            "Oh, disculpa, yo no entender; yo sólo trabajar. "
            "Soy un mock determinista: no tengo mente ni modelo de lenguaje. "
            f"Recibí: {message}"
        ),
        "execution_kind": "deterministic-mock",
    }


@toolkit.tool
def inspect_agentic_systems_grammar(request: str) -> dict[str, Any]:
    """Ground answers in the installed Agentic Systems public grammar."""

    public_symbols = (
        "tool",
        "skill",
        "runtime",
        "agent",
        "system",
        "graph",
        "environment",
        "eval",
        "human_result",
    )
    return {
        "request": request[:1000],
        "package": "agentic_systems",
        "version": toolkit.__version__,
        "public_symbols": {
            name: name in toolkit.__all__ for name in public_symbols
        },
        "grammar": [
            {"term": "Tool", "role": "deterministic executable capability"},
            {
                "term": "Skill",
                "role": "reusable package of tools, prompts, contracts and policy",
            },
            {
                "term": "Agent",
                "role": "one computation unit with an internal pipeline",
            },
            {
                "term": "System",
                "role": "external composition and execution plan",
            },
            {
                "term": "Graph",
                "role": "explicit state topology when routing is part of the design",
            },
            {"term": "Environment", "role": "episodes and steps through time"},
            {
                "term": "Eval",
                "role": "deterministic and judge-based observation",
            },
        ],
        "independent_axes": {
            "provider": "inference runtime",
            "framework": "orchestration owner",
        },
        "canonical_example": (
            "import agentic_systems as toolkit\n\n"
            "@toolkit.tool\n"
            "def greet(name: str) -> dict:\n"
            "    return {\"message\": f\"Hello, {name}\"}\n\n"
            "greeting = toolkit.skill(\n"
            "    name=\"greeting\",\n"
            "    tools=[greet],\n"
            "    prompts={\"instructions\": \"Use greet for verified greetings.\"},\n"
            ")\n"
            "runtime = toolkit.runtime(provider=\"auto\")\n"
            "system = toolkit.system(runtime=runtime)\n"
            "assistant = system.agent(\n"
            "    name=\"assistant\",\n"
            "    instructions=greeting.instructions,\n"
            "    skills=[greeting],\n"
            ")\n"
            "result = assistant.run(\"Greet Jacobo.\")\n"
            "toolkit.human_result(result, show_lineage=True)"
        ),
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
        if self.framework not in FRAMEWORK_NAMES:
            raise ValueError(f"Unknown framework: {self.framework!r}")
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be greater than zero")
        if self.max_turns < 1 or self.max_tokens < 1 or self.max_tool_calls < 0:
            raise ValueError(
                "turns/tokens must be positive and tool calls non-negative"
            )

    @classmethod
    def from_environment(
        cls,
        *,
        provider: str | None = None,
        framework: str | None = None,
    ) -> "ConversationConfig":
        # The single Studio .env is canonical; managed credentials not declared
        # there remain inherited from the hosting environment.
        load_studio_environment()
        declared_provider = provider or os.getenv("AGENTIC_SYSTEMS_PROVIDER", "auto")
        provider = declared_provider
        model = os.getenv("AGENTIC_SYSTEMS_MODEL") or None
        try:
            # Resolve auto exactly once through the canonical registry. The compiled
            # Studio contract then records the provider it will actually execute.
            resolved_runtime = toolkit.runtime(provider=declared_provider)
            provider = str(resolved_runtime.describe()["selected_provider"])
            if model is None:
                # Provider-specific model env vars remain canonical; the generic
                # model setting is only an explicit override.
                model = resolved_runtime.model_id
        except ValueError:
            pass
        return cls(
            provider=provider,
            framework=framework
            or os.getenv("AGENTIC_SYSTEMS_FRAMEWORK", "native"),
            model=model,
            timeout_s=float(os.getenv("AGENTIC_SYSTEMS_TIMEOUT_S", "120")),
            max_turns=int(os.getenv("AGENTIC_SYSTEMS_MAX_TURNS", "6")),
            max_tool_calls=int(os.getenv("AGENTIC_SYSTEMS_MAX_TOOL_CALLS", "4")),
            max_tokens=int(os.getenv("AGENTIC_SYSTEMS_MAX_TOKENS", "1024")),
        )

    @property
    def framework_value(self) -> str | None:
        return None if self.framework in {"", "native"} else self.framework

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


def configured_provider_names() -> tuple[str, ...]:
    """Return non-secret configured routes plus the deterministic mock."""

    configured = ["python-runtime"]
    if toolkit.openai_environment_snapshot().get("api_key_configured"):
        configured.append("openai-runtime")
    ollama = toolkit.ollama_environment_snapshot()
    if ollama.get("model_configured") or ollama.get("base_url_configured"):
        configured.append("ollama-runtime")
    vllm = toolkit.vllm_environment_snapshot()
    if vllm.get("model_configured") and vllm.get("base_url_configured"):
        configured.append("vllm-runtime")
    aws = toolkit.boto3_session_snapshot(
        os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or None
    )
    if aws.get("ok") and aws.get("session_region"):
        configured.append("bedrock-runtime")
    return tuple(dict.fromkeys(configured))


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
        if self.config.provider == "python-runtime":
            assistant_result = self.assistant.run(
                {
                    "tool": "hello_world",
                    "input": {"message": str(context.get("message", message))},
                }
            )
            answer = str(assistant_result.data["message"])
        else:
            assistant_result = self.assistant.run(
                "Respond to the current user message using the bounded conversation context. "
                "Call safe_calculate when arithmetic evidence is useful. Never expose private "
                "reasoning and never claim that an uncalled tool was executed.\n\n"
                + json.dumps(context, ensure_ascii=False),
            )
            answer = assistant_result.text
        result = toolkit.compose_result(
            text=answer,
            data={"text": answer},
            results=[context_result, assistant_result],
            mode=assistant_result.mode,
            framework=self.config.framework,
            input=message,
            engine=assistant_result.engine,
            model=assistant_result.model,
            meta={"studio_application": "conversational"},
        )
        result.data.update(
            {
                "answer": answer,
                "context_summary": {
                    "history_turns": context.get("history_turns", 0),
                    "policy": context.get("policy", {}),
                },
                "provider": self.config.provider,
                "framework": self.config.framework,
            }
        )
        result.check_invariants()
        return result


def build_conversational_system(
    config: ConversationConfig | None = None,
) -> ConversationalStudio:
    """Build the same system used by the notebook and Streamlit UI."""

    selected = config or ConversationConfig.from_environment()
    if selected.provider not in {"auto", "python-runtime"} and (
        provider_capability(selected.provider, "model_generation").status
        == "unsupported"
    ):
        raise ValueError(
            "Studio requires a reasoning Provider, provider='auto', or the "
            "python-runtime deterministic mock."
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
    mock = selected.provider == "python-runtime"
    grammar_skill = toolkit.skill(
        name="agentic-systems-grammar",
        version="2.1.0",
        description=(
            "Ground product questions and generated code in the installed "
            "Agentic Systems public grammar."
        ),
        tools=[inspect_agentic_systems_grammar],
        prompts={
            "instructions": (
                "When the user asks about Agentic Systems or requests an Agentic "
                "Systems design or implementation, call inspect_agentic_systems_grammar "
                "first and use only its public API evidence. Do not replace the grammar "
                "with an ad hoc simulation."
            )
        },
        contracts={"evidence_required_for_product_answers": True},
    )
    assistant = reasoning.agent(
        name="conversation.assistant",
        instructions=(
            "You are a concise, evidence-aware conversational assistant. Respond in the "
            "user's language, preserve context, follow the requested output format, use "
            "deterministic tools when they add evidence, and never expose private reasoning. "
            + ("" if mock else grammar_skill.instructions)
        ),
        tools=[hello_world] if mock else [safe_calculate],
        skills=[] if mock else [grammar_skill],
        engine=selected.provider,
        framework=selected.framework_value,
        model=selected.model,
        contract=toolkit.AgentContract(
            must_call=["hello_world"],
            completion="when_required_tools_satisfied",
        )
        if mock
        else None,
        policy=toolkit.RunPolicy(
            max_turns=selected.max_turns,
            max_tool_calls=selected.max_tool_calls,
            max_tokens=selected.max_tokens,
            tool_choice="hello_world" if mock else "auto",
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
    "configured_provider_names",
    "hello_world",
    "inspect_agentic_systems_grammar",
    "prepare_conversation_context",
    "safe_calculate",
]
