"""Provider/framework-agnostic conversational reference system for Studio."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import math
import re
from typing import Any

import agentic_systems as toolkit
from .routes import FRAMEWORK_NAMES, PROVIDER_NAMES
from agentic_systems_studio.environment import load_studio_environment
from agentic_systems_studio.presentation import (
    validate_generated_agentic_systems_code,
)


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
_MAX_HISTORY_MESSAGES = 12
_MAX_USER_HISTORY_CHARS = 2000
_MAX_ASSISTANT_HISTORY_CHARS = 1200
_MAX_CURRENT_MESSAGE_CHARS = 8000
_CALCULATION_OPERATOR_PATTERN = re.compile(
    r"\d(?:[\d.,]*\d)?\s*"
    r"(?:[+\-*/%×]|\b(?:x|times|multiplied\s+by|divided\s+by|por|entre|más|menos)\b)"
    r"\s*\d",
    re.IGNORECASE,
)
_CALCULATOR_REQUEST_PATTERN = re.compile(
    r"\b(?:use|call|run|usa|utiliza|ejecuta)\b.{0,24}"
    r"\b(?:calculator|calculadora)\b",
    re.IGNORECASE,
)
_CALCULATION_COMMAND_PATTERN = re.compile(
    r"\b(?:calculate|compute|multiply|divide|add|subtract|"
    r"calcula|calcule|multiplica|suma|resta)\b",
    re.IGNORECASE,
)
_NUMBER_PATTERN = re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?(?!\w)")
_OMISSION_REQUEST_PATTERN = re.compile(
    r"\b(?:sin\s+repetir(?:lo|la|los|las)?|no\s+(?:lo\s+)?repitas?|"
    r"do\s+not\s+repeat|don't\s+repeat|without\s+repeating)\b",
    re.IGNORECASE,
)
_NAMED_VALUE_PATTERN = re.compile(
    r"\b(?:se\s+llama|is\s+(?:called|named))\s+[\"']?([^\s,.;:!?\"']+)",
    re.IGNORECASE,
)
_QUOTED_VALUE_PATTERN = re.compile(r"[\"']([^\"']+)[\"']")


_CODE_REQUEST_PATTERN = re.compile(
    r"\b(?:code|codigo|código|class|clase|function|funcion|función|"
    r"implementation|implementacion|implementación|snippet|script|"
    r"program|programa|python)\b",
    re.IGNORECASE,
)
_IMPLEMENTATION_REQUEST_PATTERN = re.compile(
    r"\b(?:package|pack|build|create|implement|define|scaffold|"
    r"empaqueta|empaca|construye|crea|implementa|define)\b",
    re.IGNORECASE,
)
_SUMMARY_REQUEST_PATTERN = re.compile(
    r"\b(?:resume|resumir|resumen|sintetiza|síntesis|sintesis|"
    r"summarize|summary|recap)\b",
    re.IGNORECASE,
)
_SINGLE_SENTENCE_REQUEST_PATTERN = re.compile(
    r"\b(?:una\s+sola\s+(?:frase|oración)|en\s+una\s+(?:frase|oración)|"
    r"single\s+sentence|one\s+sentence)\b",
    re.IGNORECASE,
)


def _is_single_sentence(text: str) -> bool:
    """Validate an explicit one-sentence presentation constraint."""

    stripped = text.strip()
    if not stripped or "```" in stripped:
        return False
    if len([line for line in stripped.splitlines() if line.strip()]) != 1:
        return False
    if re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", stripped):
        return False
    sentence_boundaries = re.findall(r"[.!?]+(?=\s|$)", stripped)
    return len(sentence_boundaries) <= 1


def _contains_public_value(text: str, value: str) -> bool:
    """Match a requested omission as a complete public value, not a substring."""

    if not value:
        return False
    prefix = r"(?<!\w)" if value[0].isalnum() else ""
    suffix = r"(?!\w)" if value[-1].isalnum() else ""
    return (
        re.search(prefix + re.escape(value) + suffix, text, re.IGNORECASE) is not None
    )


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
    """Evaluate arithmetic explicitly requested in the current user message.

    Do not call this Tool merely because conversation history or a design question
    references an earlier calculation.
    """

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
    truncated_messages = 0
    for item in messages[-_MAX_HISTORY_MESSAGES:]:
        role = str(item.get("role", "user"))
        raw_content = str(item.get("content", ""))
        limit = (
            _MAX_ASSISTANT_HISTORY_CHARS
            if role == "assistant"
            else _MAX_USER_HISTORY_CHARS
        )
        content = raw_content[:limit]
        truncated_messages += int(len(raw_content) > limit)
        if role in {"user", "assistant"} and content:
            bounded.append({"role": role, "content": content})
    return {
        "history": bounded,
        "history_turns": len(bounded),
        "memory": {
            "kind": "bounded-public-history",
            "maximum_messages": _MAX_HISTORY_MESSAGES,
            "maximum_user_characters": _MAX_USER_HISTORY_CHARS,
            "maximum_assistant_characters": _MAX_ASSISTANT_HISTORY_CHARS,
            "maximum_current_message_characters": _MAX_CURRENT_MESSAGE_CHARS,
            "truncated_messages": truncated_messages,
        },
        "policy": {
            "reasoning_is_private": True,
            "no_silent_fallback": True,
            "tools_are_evidence": True,
        },
        # Keep the current request last so recency-sensitive runtimes do not
        # mistake the final historical assistant message for the active turn.
        "message": message[:_MAX_CURRENT_MESSAGE_CHARS],
    }


@toolkit.tool
def hello_world(message: str) -> dict[str, Any]:
    """Return a deterministic offline Studio response with public evidence."""

    return {
        "message": (
            "Modo Python: mock determinista sin modelo de lenguaje. "
            f"Recibí: {message}"
        ),
        "execution_kind": "deterministic-mock",
    }


def _agentic_systems_grammar_contract(request):
    import inspect
    return {"request": request[:1000], "version": toolkit.__version__,
            "public_symbols": list(toolkit.__all__),
            "signatures": {name: str(inspect.signature(getattr(toolkit, name)))
                           for name in toolkit.__all__ if callable(getattr(toolkit, name))},
            "canonical_example": "import agentic_systems as toolkit\n"
                "worker = toolkit.Agent('worker', toolkit.Action('increment', lambda d: {'value': d['value'] + 1}))\n"
                "app = toolkit.System('app', toolkit.Sequence((worker,)))\n"
                "print(app.run({'value': 3}).to_dict())",
            "rules": ["Agent or System owns Sequence, Parallel or Graph", "Graph decisions are direct functions",
                      "Skills contain Tools and instructions", "run executes; compile prepares without inference",
                      "Environment owns records and memory; Eval owns cases and checks",
                      "Only explicit provider/framework names; no auto or fallback"]}


@toolkit.tool
def inspect_agentic_systems_grammar(request: str) -> dict:
    """Read the installed SDK's exact public signatures before generating SDK code."""
    return _agentic_systems_grammar_contract(request)


@dataclass(frozen=True)
class ConversationConfig:
    provider: str = "python-runtime"
    framework: str = "native"
    model: str | None = None
    timeout_s: float = 60
    max_turns: int = 5
    max_tool_calls: int = 3
    max_tokens: int = 512
    max_response_repairs: int = 1

    def __post_init__(self):
        if self.provider not in PROVIDER_NAMES or self.framework not in FRAMEWORK_NAMES:
            raise ValueError("Choose an exact provider and framework")
        if self.max_response_repairs < 0:
            raise ValueError("Repairs must be nonnegative")
        self.reasoning_runtime()

    @classmethod
    def from_environment(cls, *, provider=None, framework=None):
        try:
            load_studio_environment()
        except FileNotFoundError:
            pass
        from .routes import values
        selected = provider or "python-runtime"
        return cls(provider=selected, framework=framework or "native", model=values(selected)["model"])

    def reasoning_runtime(self):
        from .routes import make_runtime
        return make_runtime(self.provider, model=self.model, timeout_s=self.timeout_s,
                            max_turns=self.max_turns, max_tool_calls=self.max_tool_calls, max_tokens=self.max_tokens)


def configured_provider_names():
    from .routes import configured
    return tuple(provider for provider in PROVIDER_NAMES if configured(provider))


@dataclass
class ConversationalStudio:
    config: ConversationConfig
    context_agent: object
    assistant: object
    calculation_agent: object

    def inspect(self):
        return {"version": toolkit.__version__, "provider": self.config.provider,
                "framework": self.config.framework, "runtime": self.config.reasoning_runtime().inspect(),
                "context": self.context_agent.inspect(), "assistant": self.assistant.inspect(),
                "grammar": _agentic_systems_grammar_contract("")}

    def run(self, message, *, history=()):
        from dataclasses import replace
        if not isinstance(message, str) or not message.strip():
            raise ValueError("A nonempty message is required")
        if self.config.provider != "python-runtime":
            from .budget import ensure_budget
            ensure_budget()
        selected = self.config

        def ground(context):
            if re.search(r"agentic|\b(?:agent|system|skill|environment|eval)\b", message, re.I):
                context["sdk_contract"] = _agentic_systems_grammar_contract(message)
            if selected.provider != "python-runtime" and _CALCULATION_OPERATOR_PATTERN.search(message):
                raw = self.calculation_agent.run("Call safe_calculate for this current request: " + message,
                    limits=toolkit.Limits(timeout_s=selected.timeout_s * selected.max_turns))
                evidence = [event.output for node in raw.walk() for event in node.tool_events if event.name == "safe_calculate" and event.ok]
                return replace(raw, data={**context, "calculation_evidence": evidence})
            return context

        def respond(context):
            request = ({"tool": "hello_world", "input": {"message": context["message"]}}
                       if selected.provider == "python-runtime" else
                       "Answer only the current message using this bounded public history and verified evidence. "
                       "Use the user's language; never reveal private reasoning or invent tool calls. "
                       "If code is requested, use the supplied SDK signatures exactly.\n" + json.dumps(context, ensure_ascii=False))
            raw = self.assistant.run(request, limits=toolkit.Limits(timeout_s=selected.timeout_s * selected.max_turns))
            if selected.provider == "python-runtime":
                raw = replace(raw, text=str(raw.data.get("message", raw.text)))
            attempts = [raw]
            validation_error = None
            for attempt in range(selected.max_response_repairs + 1):
                answer = raw.text
                try:
                    if not raw.ok or not answer.strip():
                        raise ValueError("The actor did not return a successful public answer")
                    if selected.provider != "python-runtime":
                        validate_generated_agentic_systems_code(answer)
                        if _SINGLE_SENTENCE_REQUEST_PATTERN.search(message) and not _is_single_sentence(answer):
                            raise ValueError("Exactly one sentence was requested")
                    validation_error = None
                    break
                except (SyntaxError, ValueError) as exc:
                    validation_error = str(exc)
                    if attempt == selected.max_response_repairs or not raw.ok:
                        break
                    raw = self.assistant.run("Correct this answer according to the current request and exact SDK contract. "
                        + json.dumps({"message": message, "answer": answer, "error": validation_error,
                                      "context": context}, ensure_ascii=False),
                        limits=toolkit.Limits(timeout_s=selected.timeout_s * selected.max_turns))
                    attempts.append(raw)
            # Keep all attempts as recorded children of a public System result.
            collected = toolkit.System("answer_attempts", toolkit.Sequence(tuple(
                toolkit.Action("attempt_" + str(i), lambda value, captured=child: captured)
                for i, child in enumerate(attempts)))).run({})
            errors = collected.errors
            if validation_error:
                errors = (*errors, {"code": "studio_response_validation_failed", "message": validation_error})
            return replace(collected, text=raw.text, ok=collected.ok and validation_error is None, errors=errors,
                data={"answer": raw.text, "provider": selected.provider, "framework": selected.framework,
                      "history_turns": context["history_turns"],
                      "response_validation": {"ok": validation_error is None, "repairs": len(attempts) - 1}})

        pipeline = toolkit.System("studio_conversation", toolkit.Sequence((
            self.context_agent,
            toolkit.Agent("grounding", toolkit.Action("ground", ground)),
            toolkit.Agent("responding", toolkit.Action("respond", respond)),
        )))
        raw = pipeline.run({"messages": list(history), "message": message},
                           limits=toolkit.Limits(max_actions=100, timeout_s=selected.timeout_s * selected.max_turns * 3))
        return replace(raw, meta={**raw.meta, "provider": selected.provider, "framework": selected.framework,
                                  "studio_version": toolkit.__version__})


def build_conversational_system(config=None):
    selected = config or ConversationConfig.from_environment()
    capabilities = toolkit.skill(name="studio", tools=(safe_calculate, inspect_agentic_systems_grammar),
        instructions="Only call the calculator for a newly requested calculation; inspect the SDK before writing SDK code.")
    context = toolkit.Agent("context", toolkit.Action("prepare", prepare_conversation_context))
    if selected.provider == "python-runtime":
        assistant = toolkit.Agent("deterministic_mock", runtime=selected.reasoning_runtime(),
            framework=toolkit.framework(selected.framework),
            skills=(toolkit.skill(name="mock", tools=(hello_world,)),))
    else:
        assistant = toolkit.Agent("assistant", runtime=selected.reasoning_runtime(),
            framework=toolkit.framework(selected.framework), skills=(capabilities,),
            instructions="Answer the current user clearly using bounded context. Use only observed evidence. Never expose private reasoning.",
            policy={"repair": False})
    calculator = None if selected.provider == "python-runtime" else toolkit.Agent("calculator",
        runtime=selected.reasoning_runtime(), framework=toolkit.framework(selected.framework),
        skills=(toolkit.skill(name="calculator", tools=(safe_calculate,)),),
        instructions="Call safe_calculate once with the requested arithmetic expression.",
        contract={"tool_expectation": {"all_of": ["safe_calculate"]}, "completion": "when_required_tools_satisfied"},
        policy={"repair": False})
    return ConversationalStudio(selected, context, assistant, calculator)
