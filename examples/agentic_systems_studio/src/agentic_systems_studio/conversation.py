"""Provider/framework-agnostic conversational reference system for Studio."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import math
import os
import re
from typing import Any, Mapping, Sequence

import agentic_systems as toolkit
from agentic_systems.registry import (
    FRAMEWORK_NAMES,
    PROVIDER_NAMES,
    provider_capability,
)
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
            "Oh, disculpa, yo no entender; yo sólo trabajar. "
            "Soy un mock determinista: no tengo mente ni modelo de lenguaje. "
            f"Recibí: {message}"
        ),
        "execution_kind": "deterministic-mock",
    }


def _agentic_systems_grammar_contract(request: str) -> dict[str, Any]:
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
        "public_symbols": {name: name in toolkit.__all__ for name in public_symbols},
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
        "contracts": {
            "tool_output": "Every @toolkit.tool returns a dictionary.",
            "canonical_import": "import agentic_systems as toolkit",
            "result_boundary": "Every execution returns a normalized RunResult.",
        },
        "canonical_factories": {
            "Tool": "tool",
            "Skill": "skill",
            "Agent": "agent",
            "System": "system",
            "Graph": "graph",
            "Environment": "environment",
            "Eval": "eval",
        },
        "canonical_example": (
            "import agentic_systems as toolkit\n\n"
            "@toolkit.tool\n"
            "def greet(name: str) -> dict:\n"
            '    return {"message": f"Hello, {name}"}\n\n'
            "greeting = toolkit.skill(\n"
            '    name="greeting",\n'
            "    tools=[greet],\n"
            '    prompts={"instructions": "Use greet for verified greetings."},\n'
            ")\n"
            'runtime = toolkit.runtime(provider="auto")\n'
            "system = toolkit.system(runtime=runtime)\n"
            "assistant = system.agent(\n"
            '    name="assistant",\n'
            "    instructions=greeting.instructions,\n"
            "    skills=[greeting],\n"
            ")\n"
            'result = assistant.run("Greet Jacobo.")\n'
            "toolkit.human_result(result, show_lineage=True)"
        ),
    }


@toolkit.tool
def inspect_agentic_systems_grammar(request: str) -> dict[str, Any]:
    """Ground answers in the installed Agentic Systems public grammar."""

    return _agentic_systems_grammar_contract(request)


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
    max_response_repairs: int = 2

    def __post_init__(self) -> None:
        if self.provider not in {"auto", *PROVIDER_NAMES}:
            raise ValueError(f"Unknown provider: {self.provider!r}")
        if self.framework not in FRAMEWORK_NAMES:
            raise ValueError(f"Unknown framework: {self.framework!r}")
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be greater than zero")
        if (
            self.max_turns < 1
            or self.max_tokens < 1
            or self.max_tool_calls < 0
            or self.max_response_repairs < 0
        ):
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
            framework=framework or os.getenv("AGENTIC_SYSTEMS_FRAMEWORK", "native"),
            model=model,
            timeout_s=float(os.getenv("AGENTIC_SYSTEMS_TIMEOUT_S", "120")),
            max_turns=int(os.getenv("AGENTIC_SYSTEMS_MAX_TURNS", "6")),
            max_tool_calls=int(os.getenv("AGENTIC_SYSTEMS_MAX_TOOL_CALLS", "4")),
            max_tokens=int(os.getenv("AGENTIC_SYSTEMS_MAX_TOKENS", "1024")),
            max_response_repairs=int(
                os.getenv("AGENTIC_SYSTEMS_MAX_RESPONSE_REPAIRS", "2")
            ),
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
    calculation_agent: Any | None = None
    grammar_contract: Mapping[str, Any] | None = None
    grounded_assistant: Any | None = None

    def _required_factory_calls(self, message: str) -> tuple[str, ...]:
        """Project explicitly requested grammar terms onto public factories."""

        factories = dict((self.grammar_contract or {}).get("canonical_factories") or {})
        requested: list[str] = []
        for concept, factory in factories.items():
            if re.search(rf"\b{re.escape(str(concept))}\b", message, re.IGNORECASE):
                requested.append(str(factory))
        return tuple(dict.fromkeys(requested))

    def _requests_new_calculation_evidence(self, message: str) -> bool:
        """Detect an explicit request for new deterministic arithmetic evidence."""

        if _CALCULATOR_REQUEST_PATTERN.search(message):
            return True
        if _CALCULATION_OPERATOR_PATTERN.search(message):
            return True
        return bool(
            _CALCULATION_COMMAND_PATTERN.search(message)
            and len(_NUMBER_PATTERN.findall(message)) >= 2
        )

    def _requested_public_omissions(self, message: str) -> tuple[str, ...]:
        """Return values the current message explicitly asks not to repeat."""

        if not _OMISSION_REQUEST_PATTERN.search(message):
            return ()
        values = [match.group(1) for match in _QUOTED_VALUE_PATTERN.finditer(message)]
        values.extend(
            match.group(1) for match in _NAMED_VALUE_PATTERN.finditer(message)
        )
        values.extend(_NUMBER_PATTERN.findall(message))
        normalized = [value.strip() for value in values if value.strip()]
        return tuple(dict.fromkeys(normalized))

    def _public_omissions_for_turn(
        self,
        *,
        message: str,
        context: Mapping[str, Any],
    ) -> tuple[str, ...]:
        """Carry explicit non-repetition constraints through bounded public history."""

        values = list(self._requested_public_omissions(message))
        history = context.get("history")
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, Mapping) or item.get("role") != "user":
                    continue
                historical_values = self._requested_public_omissions(
                    str(item.get("content", ""))
                )
                values.extend(
                    value
                    for value in historical_values
                    if _NUMBER_PATTERN.fullmatch(value) is None
                )
        return tuple(dict.fromkeys(values))

    def _requests_grammar_evidence(self, message: str) -> bool:
        contract = dict(self.grammar_contract or {})
        terms = [
            *dict(contract.get("canonical_factories") or {}).keys(),
            *dict(contract.get("independent_axes") or {}).keys(),
            str(contract.get("package") or "").replace("_", " "),
            "Agentic Systems",
        ]
        return any(
            re.search(rf"\b{re.escape(str(term))}\b", message, re.IGNORECASE)
            for term in terms
        )

    def _validate_or_repair_response(
        self,
        *,
        message: str,
        context: Mapping[str, Any],
        assistant_result: toolkit.RunResult,
        evidence_results: Sequence[toolkit.RunResult] = (),
        execution_agent: Any | None = None,
    ) -> tuple[str, list[toolkit.RunResult], dict[str, Any]]:
        """Validate generated public API examples and perform one bounded repair."""

        results = [assistant_result]
        answer = assistant_result.text
        required_calls = self._required_factory_calls(message)
        omitted_values = self._public_omissions_for_turn(
            message=message,
            context=context,
        )
        tool_evidence: list[dict[str, Any]] = []
        for evidence_result in (*evidence_results, assistant_result):
            for event in evidence_result.tool_events:
                output = event.output if isinstance(event.output, dict) else {}
                sources = [output]
                if isinstance(output.get("data"), dict):
                    sources.append(output["data"])
                for source in sources:
                    value = source.get("result")
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        tool_evidence.append({"tool": event.name, "result": value})

        def validate_response(
            response: str,
            *,
            source_result: toolkit.RunResult,
        ) -> None:
            code_requested = bool(_CODE_REQUEST_PATTERN.search(message))
            validate_generated_agentic_systems_code(
                response,
                required_calls=required_calls,
                allow_code=bool(required_calls) or not tool_evidence or code_requested,
            )
            public_issue_codes = {
                "reasoning_exposed_in_public_answer",
                "technical_answer_exposed_in_public_answer",
            }
            public_issues = [
                issue
                for issue in source_result.check_invariants().issues
                if issue.code in public_issue_codes
            ]
            if public_issues:
                raise ValueError(
                    "The public answer violates its presentation boundary: "
                    + "; ".join(issue.message for issue in public_issues)
                )
            leaked_values = [
                value
                for value in omitted_values
                if _contains_public_value(response, value)
            ]
            if leaked_values:
                raise ValueError(
                    "The current request explicitly forbids repeating these values: "
                    f"{leaked_values}."
                )
            missing = [
                item for item in tool_evidence if str(item["result"]) not in response
            ]
            if missing:
                raise ValueError(
                    f"The public answer omitted scalar Tool evidence: {missing}."
                )

        validation = {
            "ok": True,
            "repairs": 0,
            "required_factories": list(required_calls),
            "initial_error": None,
            "final_error": None,
        }
        try:
            validate_response(answer, source_result=assistant_result)
            return answer, results, validation
        except (SyntaxError, ValueError) as exc:
            validation["ok"] = False
            validation["initial_error"] = str(exc)
            if self.config.max_response_repairs < 1:
                validation["final_error"] = str(exc)
                return answer, results, validation

        contract = dict(self.grammar_contract or {})
        canonical_example = str(contract.get("canonical_example") or "")
        last_error = str(validation["initial_error"])
        for attempt in range(1, self.config.max_response_repairs + 1):
            repair_result = (execution_agent or self.assistant).run(
                "Correct the previous answer so it satisfies the public response boundary. "
                "Return a natural, human-readable answer, never a raw JSON object, Python "
                "repr, ToolEnvelope, validation report or private reasoning. Obey explicit "
                "omissions and output constraints from the current request. When code is "
                "requested, use only the canonical Agentic Systems public grammar. Preserve "
                "the user's requested language and intent.\n\n"
                f"Current user request:\n{message}\n\n"
                f"Validation failure:\n{last_error}\n\n"
                f"Canonical public example:\n```python\n{canonical_example}\n```\n\n"
                f"Previous answer:\n{answer[:5000]}\n\n"
                f"Observed public Tool evidence:\n{json.dumps(tool_evidence)}\n\n"
                "Bounded conversation context:\n"
                + json.dumps(context, ensure_ascii=False),
            )
            results.append(repair_result)
            answer = repair_result.text
            validation["repairs"] = attempt
            try:
                validate_response(answer, source_result=repair_result)
            except (SyntaxError, ValueError) as exc:
                last_error = str(exc)
                validation["final_error"] = last_error
            else:
                validation["ok"] = True
                validation["final_error"] = None
                return answer, results, validation
        return answer, results, validation

    def inspect(self) -> dict[str, Any]:
        return {
            "configuration": {
                "provider": self.config.provider,
                "framework": self.config.framework,
                "model": self.config.model,
                "max_response_repairs": self.config.max_response_repairs,
            },
            "deterministic_system": self.deterministic_system.inspect().to_dict(),
            "reasoning_system": self.reasoning_system.inspect().to_dict(),
            "agents": [
                self.context_agent.info(),
                self.assistant.info(),
                *(
                    [self.calculation_agent.info()]
                    if self.calculation_agent is not None
                    else []
                ),
                *(
                    [self.grounded_assistant.info()]
                    if self.grounded_assistant is not None
                    else []
                ),
            ],
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
        grammar_results: list[toolkit.RunResult] = []
        if self.config.provider != "python-runtime" and self._requests_grammar_evidence(
            message
        ):
            grammar_result = inspect_agentic_systems_grammar.run({"request": message})
            grammar_results.append(grammar_result)
            current_message = context.pop("message", message)
            context["agentic_systems_grammar"] = dict(grammar_result.data)
            # Keep the current request last for recency-sensitive small models.
            context["message"] = current_message
        calculation_results: list[toolkit.RunResult] = []
        if (
            self.config.provider != "python-runtime"
            and self.calculation_agent is not None
            and self._requests_new_calculation_evidence(message)
        ):
            calculation_result = self.calculation_agent.run(
                "Interpret only the current request and call safe_calculate exactly "
                "once with the arithmetic expression that requires verification. "
                "Do not answer from memory and do not perform any other task.\n\n"
                + json.dumps(context, ensure_ascii=False)
            )
            calculation_results.append(calculation_result)
            verified_events = [
                event
                for event in calculation_result.tool_events
                if event.name == "safe_calculate" and event.ok
            ]
            if verified_events:
                output = verified_events[-1].output
                if isinstance(output, dict):
                    public_output = output.get("data", output)
                    if isinstance(public_output, dict):
                        current_message = context.pop("message", message)
                        context["calculation_evidence"] = dict(public_output)
                        context["message"] = current_message
        if self.config.provider == "python-runtime":
            assistant_result = self.assistant.run(
                {
                    "tool": "hello_world",
                    "input": {"message": str(context.get("message", message))},
                }
            )
            answer = str(assistant_result.data["message"])
            assistant_results = [assistant_result]
            response_validation = {
                "ok": True,
                "repairs": 0,
                "required_factories": [],
                "initial_error": None,
                "final_error": None,
            }
        else:
            execution_agent = (
                self.grounded_assistant
                if (grammar_results or calculation_results)
                and self.grounded_assistant is not None
                else self.assistant
            )
            assistant_result = execution_agent.run(
                "Respond to the current user message using the bounded conversation context. "
                "Call safe_calculate only when the current message explicitly requests a new "
                "arithmetic calculation. A reference to an earlier calculation in a design, "
                "explanation or memory request is not permission to call it again. Never expose private "
                "reasoning and never claim that an uncalled tool was executed.\n\n"
                "Answer only the current message; use history as context, never as text "
                "to repeat or continue mechanically. Do not append unrelated prior "
                "answers.\n\n" + json.dumps(context, ensure_ascii=False),
            )
            answer, assistant_results, response_validation = (
                self._validate_or_repair_response(
                    message=message,
                    context=context,
                    assistant_result=assistant_result,
                    evidence_results=calculation_results,
                    execution_agent=execution_agent,
                )
            )
        result = toolkit.compose_result(
            text=answer,
            data={"text": answer},
            results=[
                context_result,
                *grammar_results,
                *calculation_results,
                *assistant_results,
            ],
            mode=assistant_results[-1].mode,
            framework=self.config.framework,
            input=message,
            engine=assistant_results[-1].engine,
            model=assistant_results[-1].model,
            meta={"studio_application": "conversational"},
        )
        result.data.update(
            {
                "answer": answer,
                "context_summary": {
                    "history_turns": context.get("history_turns", 0),
                    "memory": context.get("memory", {}),
                    "policy": context.get("policy", {}),
                },
                "provider": self.config.provider,
                "framework": self.config.framework,
                "response_validation": response_validation,
            }
        )
        if not response_validation["ok"]:
            result.ok = False
            result.errors.append(
                {
                    "code": "studio_response_validation_failed",
                    "message": str(
                        response_validation.get("final_error")
                        or response_validation.get("initial_error")
                    ),
                    "meta": {
                        "repairs": response_validation["repairs"],
                        "required_factories": response_validation["required_factories"],
                    },
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
        version="2.1.1",
        description=(
            "Ground product questions and generated code in the installed "
            "Agentic Systems public grammar."
        ),
        # The Studio executes the grounding Tool deterministically before the
        # LM turn. Keeping it out of the model-owned loop prevents duplicate
        # calls while the Skill still owns prompts and contracts.
        tools=[],
        prompts={
            "instructions": (
                "When the user asks about Agentic Systems or requests an Agentic "
                "Systems design or implementation, use the agentic_systems_grammar "
                "evidence supplied deterministically in the bounded context. Use only "
                "that public API evidence. Do not replace the grammar "
                "with an ad hoc simulation. When generating code, preserve the canonical "
                "imports, signatures and contracts exactly; every @toolkit.tool example "
                "must return a dictionary. Apply this rule to the current turn even when "
                "history already contains an earlier Agentic Systems answer; never invent "
                "classes or APIs absent from the Tool evidence."
            )
        },
        contracts={"evidence_required_for_product_answers": True},
    )
    assistant_instructions = (
        "You are a concise, evidence-aware conversational assistant. Respond in the "
        "user's language, preserve context, follow the requested output format, use "
        "deterministic tools when they add evidence, and never expose private reasoning. "
        "When a Tool runs, explicitly incorporate its relevant returned evidence into "
        "the final answer. Follow negative wording literally: when asked not to "
        "repeat a value, acknowledge it without restating it. Do not call a Tool "
        "when the current request only asks for acknowledgement, memory, explanation "
        "or software design based on evidence already present in history. "
        + ("" if mock else grammar_skill.instructions)
    )
    assistant = reasoning.agent(
        name="conversation.assistant",
        instructions=assistant_instructions,
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
    calculation_agent = None
    grounded_assistant = None
    if not mock:
        calculation_agent = reasoning.agent(
            name="conversation.calculation_evidence",
            instructions=(
                "Interpret the current conversational request only to obtain deterministic "
                "arithmetic evidence. Call safe_calculate exactly once with a normalized "
                "Python arithmetic expression. Never answer from memory."
            ),
            tools=[safe_calculate],
            engine=selected.provider,
            framework=selected.framework_value,
            model=selected.model,
            contract=toolkit.AgentContract(
                must_call=["safe_calculate"],
                completion="when_required_tools_satisfied",
            ),
            policy=toolkit.RunPolicy(
                max_turns=min(selected.max_turns, 3),
                max_tool_calls=1,
                max_tokens=selected.max_tokens,
                tool_choice="safe_calculate",
            ),
        )
        grounded_assistant = reasoning.agent(
            name="conversation.grounded_assistant",
            instructions=assistant_instructions,
            tools=[],
            skills=[grammar_skill],
            engine=selected.provider,
            framework=selected.framework_value,
            model=selected.model,
            policy=toolkit.RunPolicy(
                max_turns=selected.max_turns,
                max_tool_calls=0,
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
        calculation_agent=calculation_agent,
        grounded_assistant=grounded_assistant,
        grammar_contract=_agentic_systems_grammar_contract(
            "Studio canonical response validation"
        ),
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
