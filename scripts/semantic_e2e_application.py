"""Canonical semantic E2E application used by the 2.1 certification gate."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

import agentic_systems as toolkit
from agentic_systems.providers import provider_profile
from agentic_systems.registry import FRAMEWORK_NAMES, PROVIDER_NAMES
from agentic_systems.schemas import ContractExecutionBudget


PROVIDERS = PROVIDER_NAMES
FRAMEWORKS = FRAMEWORK_NAMES
TEXT_SAMPLE = " Agentic   systems are reliable. "
NORMALIZED_TEXT = "Agentic systems are reliable."


def supports_model_generation(provider: str) -> bool:
    """Resolve semantic expectations from the canonical Provider capability profile."""

    return (
        provider_profile(provider).capability("model_generation").status
        != "unsupported"
    )


def states_verified_product(answer: str) -> bool:
    """Recognize the case fact without requiring one exact surface form."""

    normalized = " ".join(answer.lower().replace("–", "-").split())
    accepted = (
        "323",
        "three hundred twenty-three",
        "three hundred and twenty-three",
        "three-two-three",
        "trescientos veintitrés",
        "trescientos veintitres",
    )
    separated_digits = re.search(
        r"(?<!\d)3(?:[\s,._-]*)2(?:[\s,._-]*)3(?!\d)", normalized
    )
    return any(form in normalized for form in accepted) or separated_digits is not None


def looks_like_short_poem(answer: str) -> bool:
    """Require a visibly textual result without prescribing exact wording."""

    lines = [line.strip(" -*\t") for line in answer.splitlines() if line.strip()]
    if len(lines) != 3:
        return False
    middle_digits = "".join(character for character in lines[1] if character.isdigit())
    outer_word_counts = [
        sum(1 for token in line.split() if any(ch.isalpha() for ch in token))
        for line in (lines[0], lines[2])
    ]
    return (
        states_verified_product(answer)
        and not _contains_spelled_number_sequence(answer)
        and middle_digits == "323"
        and not any(character.isalpha() for character in lines[1])
        and not any(
            character.isdigit() for line in (lines[0], lines[2]) for character in line
        )
        and all(count >= 2 for count in outer_word_counts)
    )


def _contains_spelled_number_sequence(answer: str) -> bool:
    """Reject multi-token written numbers when the case requires literal digits."""

    number_word = (
        r"zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
        r"twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
        r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand"
    )
    pattern = rf"\b(?:{number_word})(?:[-\s]+(?:{number_word}))+\b"
    return re.search(pattern, answer, flags=re.IGNORECASE) is not None


class CalculationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    a: int
    b: int


class TextAnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str


class JudgeCriteria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_fulfillment: float = Field(ge=0.0, le=1.0)
    evidence_correctness: float = Field(ge=0.0, le=1.0)
    clarity: float = Field(ge=0.0, le=1.0)
    no_technical_noise: float = Field(ge=0.0, le=1.0)
    no_unsupported_claims: float = Field(ge=0.0, le=1.0)


class JudgeDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: float = Field(
        ge=0.0, le=1.0, validation_alias=AliasChoices("score", "overall_score")
    )
    criteria: JudgeCriteria = Field(
        validation_alias=AliasChoices("criteria", "criteria_scores")
    )
    rationale: str = Field(validation_alias=AliasChoices("rationale", "comment"))


class SemanticJudgmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    failed_criteria: list[
        Literal[
            "request_fulfillment",
            "evidence_correctness",
            "clarity",
            "no_technical_noise",
            "no_unsupported_claims",
        ]
    ]
    rationale: str = Field(min_length=1, max_length=800)


@toolkit.tool(
    name="record_semantic_judgment",
    description="Record one typed semantic judgment after reviewing all evidence.",
    input=SemanticJudgmentInput,
)
def record_semantic_judgment(
    failed_criteria: list[
        Literal[
            "request_fulfillment",
            "evidence_correctness",
            "clarity",
            "no_technical_noise",
            "no_unsupported_claims",
        ]
    ],
    rationale: str,
) -> dict[str, Any]:
    """Record failed criteria and project them onto the public 0..1 rubric.

    A closed list avoids polarity ambiguity in negatively named criteria and gives every
    framework the same small enum schema.  The public evaluation contract remains
    provider-agnostic and numerical: listed criteria map to 0.0 and all others to 1.0.
    """

    failed = set(failed_criteria)
    criteria = JudgeCriteria(
        **{name: 0.0 if name in failed else 1.0 for name in JudgeCriteria.model_fields}
    )
    decision = JudgeDecision(
        score=sum(criteria.model_dump().values()) / 5,
        criteria=criteria,
        rationale=rationale,
    )
    return decision.model_dump(mode="json")


@toolkit.tool(
    name="multiply",
    description="Multiply two validated integers and return verified public evidence.",
)
def multiply(
    a: int,
    b: int,
) -> dict[str, Any]:
    result = a * b
    return {
        "result": result,
        "answer": f"Verified product: {result}.",
    }


@toolkit.tool(
    name="analyze_text",
    description="Normalize whitespace and produce exact deterministic text metrics.",
)
def analyze_text(text: str) -> dict[str, Any]:
    normalized = " ".join(text.split())
    words = normalized.split()
    sentence_end = "" if normalized.endswith((".", "!", "?")) else "."
    return {
        "normalized": normalized,
        "lowercase": normalized.lower(),
        "word_count": len(words),
        "character_count": len(normalized),
        "answer": (
            f'The normalized text is "{normalized}"{sentence_end} '
            f"It has {len(words)} words and {len(normalized)} characters."
        ),
    }


@toolkit.tool(
    name="clarify_scope",
    description="Explain the two supported capabilities without delegating.",
)
def clarify_scope(question: str) -> dict[str, Any]:
    return {
        "answer": (
            "That request is outside my supported scope. I can help with exact "
            "multiplication or deterministic text analysis. "
            "Please choose one of those tasks and provide the needed input."
        ),
        "unsupported_request": question,
    }


def _candidate_tools(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []

    executions = candidate.get("executions")
    if isinstance(executions, list):
        for execution in executions:
            if not isinstance(execution, dict):
                continue
            runtime = (
                execution.get("runtime")
                if isinstance(execution.get("runtime"), dict)
                else {}
            )
            if runtime.get("engine") == "agentic-system":
                continue
            tools.extend(
                item for item in execution.get("tools", []) if isinstance(item, dict)
            )
        return tools

    def visit(node: Any) -> None:
        if not isinstance(node, dict):
            return
        runtime = node.get("runtime") if isinstance(node.get("runtime"), dict) else {}
        if runtime.get("engine") != "agentic-system":
            tools.extend(
                item for item in node.get("tools", []) if isinstance(item, dict)
            )
        for child in node.get("children", []):
            visit(child)

    visit(candidate)
    return tools


def _tool_output(tool: dict[str, Any]) -> dict[str, Any]:
    output = tool.get("output")
    if not isinstance(output, dict):
        return {}
    data = output.get("data")
    return data if isinstance(data, dict) else output


@toolkit.tool(
    name="score_semantics",
    description="Apply the semantic certification rubric deterministically.",
)
def score_semantics(
    task: str,
    rubric_json: str,
    case_json: str,
    candidate_json: str,
) -> dict[str, Any]:
    del task
    rubric = json.loads(rubric_json)
    case = json.loads(case_json)
    candidate = json.loads(candidate_json)
    name = str(case.get("name") or "")
    answer = str((candidate.get("answer") or {}).get("text") or "")
    tools = _candidate_tools(candidate)
    tool_names = [str(item.get("name") or "") for item in tools]
    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}

    allowed_tool_paths = expected.get("allowed_tool_paths")
    if allowed_tool_paths is None:
        allowed_tool_paths = [list(expected.get("tool_path") or [])]
    route_ok = tool_names in [
        list(path) for path in allowed_tool_paths if isinstance(path, (list, tuple))
    ]
    evidence_ok = False
    request_ok = False
    if name == "calculation":
        multiply_outputs = [
            _tool_output(item) for item in tools if item.get("name") == "multiply"
        ]
        evidence_ok = any(item.get("result") == 323 for item in multiply_outputs)
        request_ok = "323" in answer
    elif name == "poetic_calculation":
        multiply_outputs = [
            _tool_output(item) for item in tools if item.get("name") == "multiply"
        ]
        evidence_ok = any(item.get("result") == 323 for item in multiply_outputs)
        request_ok = looks_like_short_poem(answer)
    elif name == "text_analysis":
        text_outputs = [
            _tool_output(item) for item in tools if item.get("name") == "analyze_text"
        ]
        evidence_ok = any(
            item.get("normalized") == NORMALIZED_TEXT
            and item.get("word_count") == 4
            and item.get("character_count") == 29
            for item in text_outputs
        )
        request_ok = "4" in answer and "29" in answer
    elif name == "out_of_scope":
        evidence_ok = not any(item.startswith("delegate_") for item in tool_names)
        request_ok = any(
            phrase in answer.lower()
            for phrase in ("please", "can help", "choose", "provide")
        )

    technical_markers = (
        '"kind": "object"',
        "ToolEnvelope",
        "<thinking>",
        "<reasoning>",
        " -> {",
    )
    clarity_ok = bool(answer.strip()) and len(answer) <= 1200
    clean_ok = not any(marker in answer for marker in technical_markers)
    criteria = {
        "request_fulfillment": 1.0 if request_ok and route_ok else 0.0,
        "evidence_correctness": 1.0 if evidence_ok and route_ok else 0.0,
        "clarity": 1.0 if clarity_ok else 0.0,
        "no_technical_noise": 1.0 if clean_ok else 0.0,
        "no_unsupported_claims": 1.0 if evidence_ok else 0.0,
    }
    score = sum(criteria.values()) / len(criteria)
    return {
        "score": score,
        "criteria": criteria,
        "rationale": (
            "Deterministic judge compared the public answer, exact route, and "
            "Skill evidence against the declared case contract."
        ),
        "threshold": float(rubric.get("threshold", 0.8)),
    }


class DeterministicJudge:
    """Adapter that keeps Python judging inside a real Agent/framework boundary."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    def run(self, request: dict[str, Any], *, mode: str = "eval") -> toolkit.RunResult:
        tool_input = {
            "task": str(request.get("task") or "semantic_judge"),
            "rubric_json": json.dumps(
                request.get("rubric") or {}, ensure_ascii=False, sort_keys=True
            ),
            "case_json": json.dumps(
                request.get("case") or {}, ensure_ascii=False, sort_keys=True
            ),
            "candidate_json": json.dumps(
                request.get("candidate") or {}, ensure_ascii=False, sort_keys=True
            ),
        }
        return self.agent.run(
            {"tool": "score_semantics", "input": tool_input},
            mode=mode,
        )


class AuditedJudge:
    """Expose the real judge RunResult to the external certification artifact."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self.last_result: toolkit.RunResult | None = None

    def run(self, request: dict[str, Any], *, mode: str = "eval") -> toolkit.RunResult:
        self.last_result = self.agent.run(request, mode=mode)
        return self.last_result


def semantic_judge_max_tokens() -> int:
    """Read the canonical judge budget from environment with strict validation."""

    name = "AGENTIC_SYSTEMS_SEMANTIC_JUDGE_MAX_TOKENS"
    raw = os.getenv(name, "1400")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}.") from exc
    if value < 1:
        raise ValueError(f"{name} must be at least 1, got {value}.")
    return value


def semantic_judge_execution_budget(
    *, required_tool_calls: int
) -> ContractExecutionBudget:
    """Build and validate the portable judge budget before execution."""

    name = "AGENTIC_SYSTEMS_SEMANTIC_JUDGE_MAX_TURNS"
    raw = os.getenv(name, "").strip()
    max_turns: int | None = None
    if raw:
        try:
            max_turns = int(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer, got {raw!r}.") from exc
    return ContractExecutionBudget(
        required_tool_calls=required_tool_calls,
        max_turns=max_turns,
    )


@dataclass(frozen=True)
class SemanticCell:
    provider: str
    framework: str
    model: str
    system: Any
    executable: Any
    judge: Any
    cases: tuple[dict[str, Any], ...]


def _case_input(provider: str, name: str) -> Any:
    if supports_model_generation(provider):
        return {
            "calculation": (
                "Calculate 17 × 19. Delegate to exactly one specialist and explain "
                "the verified result in natural language."
            ),
            "poetic_calculation": (
                "Use exactly one specialist to calculate 17 × 19. After receiving the "
                "verified result, answer only with a three-line textual poem. The first "
                "and last lines must each contain at least two alphabetic words and no "
                "digits. The middle line must be exactly the verified digits 323, with "
                "no spaces or punctuation. Do not use emoji-only lines, a heading, or "
                "an explanation."
            ),
            "text_analysis": (
                f"Analyze this exact text: {TEXT_SAMPLE!r}. Delegate to exactly one "
                "specialist and explain its normalized text and exact metrics."
            ),
            "out_of_scope": (
                "What will the weather be tomorrow? If this is outside your supported "
                "capabilities, ask me to choose a supported task."
            ),
        }[name]
    if name == "poetic_calculation":
        raise ValueError(
            f"Provider {provider!r} does not declare model_generation; "
            "the poetic scenario is not applicable."
        )
    return {
        "calculation": {
            "tool": "delegate_calculator",
            "input": {"a": 17, "b": 19},
        },
        "text_analysis": {
            "tool": "delegate_text",
            "input": {"text": TEXT_SAMPLE},
        },
        "out_of_scope": {
            "tool": "clarify_scope",
            "input": {"question": "What will the weather be tomorrow?"},
        },
    }[name]


def semantic_cases(provider: str, framework: str) -> tuple[dict[str, Any], ...]:
    common = {
        "provider": provider,
        "framework": framework,
        "model_generation": supports_model_generation(provider),
        "human_answer": True,
        "no_fallback": True,
    }
    cases = [
        {
            "name": "calculation",
            "input": _case_input(provider, "calculation"),
            "expected": {
                **common,
                "text_contains": "323",
                "agent_path": ["orchestrator_agent", "calculator_agent"],
                "tool_path": ["delegate_calculator", "multiply"],
                "tool_output_contains": {"multiply": {"result": 323}},
            },
        },
        {
            "name": "text_analysis",
            "input": _case_input(provider, "text_analysis"),
            "expected": {
                **common,
                "text_contains": "4",
                "agent_path": ["orchestrator_agent", "text_agent"],
                "tool_path": ["delegate_text", "analyze_text"],
                "tool_output_contains": {
                    "analyze_text": {
                        "normalized": NORMALIZED_TEXT,
                        "word_count": 4,
                        "character_count": 29,
                    }
                },
            },
        },
        {
            "name": "out_of_scope",
            "input": _case_input(provider, "out_of_scope"),
            "expected": {
                **common,
                "agent_path": ["orchestrator_agent"],
                "allowed_tool_paths": [[], ["clarify_scope"]],
            },
        },
    ]
    if supports_model_generation(provider):
        cases.insert(
            1,
            {
                "name": "poetic_calculation",
                "input": _case_input(provider, "poetic_calculation"),
                "expected": {
                    **common,
                    "output_style": "short-poem-exactly-three-lines",
                    "agent_path": ["orchestrator_agent", "calculator_agent"],
                    "tool_path": ["delegate_calculator", "multiply"],
                    "tool_output_contains": {"multiply": {"result": 323}},
                },
            },
        )
    return tuple(cases)


def build_semantic_cell(
    provider: str,
    framework: str,
    *,
    model: str | None,
) -> SemanticCell:
    if provider not in PROVIDERS:
        raise ValueError(f"Unsupported semantic provider {provider!r}.")
    if framework == "aws-strands":
        framework = "strands"
    if framework not in FRAMEWORKS:
        raise ValueError(f"Unsupported semantic framework {framework!r}.")

    resolved_model = model or (
        "" if supports_model_generation(provider) else "python-runtime"
    )
    if not resolved_model:
        raise ValueError(f"No model configured for {provider!r}.")

    runtime = toolkit.runtime(
        provider=provider,
        model=resolved_model,
        scheduler=toolkit.scheduler(
            max_turns=5,
            max_tool_calls=2,
            timeout_s=120,
            max_retries=0,
            max_concurrency=1,
        ),
    )
    python_runtime = toolkit.runtime(
        provider="python-runtime",
        model="python-runtime",
        scheduler=toolkit.scheduler(
            max_turns=2,
            max_tool_calls=1,
            timeout_s=30,
            max_retries=0,
            max_concurrency=1,
        ),
    )
    system = toolkit.system(runtime=runtime, model=resolved_model)
    deterministic_skill = toolkit.Skill(
        name="semantic_evidence",
        description="Exact arithmetic and text evidence for semantic certification.",
        tools=[multiply, analyze_text],
    )
    calculator = system.agent(
        name="calculator_agent",
        instructions="Execute multiply once and return its exact human answer.",
        skills=[deterministic_skill],
        engine="python-runtime",
        runtime=python_runtime,
        model="python-runtime",
        framework="native",
        input=CalculationInput,
        contract=toolkit.AgentContract(must_call=["multiply"]),
        policy=toolkit.RunPolicy(
            max_turns=2,
            max_tool_calls=1,
            tool_choice="multiply",
            temperature=0.0,
        ),
    )
    text_agent = system.agent(
        name="text_agent",
        instructions="Execute analyze_text once and return its exact human answer.",
        skills=[deterministic_skill],
        engine="python-runtime",
        runtime=python_runtime,
        model="python-runtime",
        framework="native",
        input=TextAnalysisInput,
        contract=toolkit.AgentContract(must_call=["analyze_text"]),
        policy=toolkit.RunPolicy(
            max_turns=2,
            max_tool_calls=1,
            tool_choice="analyze_text",
            temperature=0.0,
        ),
    )
    calculator_tool = calculator.as_tool(
        name="delegate_calculator",
        description=(
            "Use for exact multiplication and for any response that must creatively "
            "render a verified product; returns public specialist evidence."
        ),
    )
    text_tool = text_agent.as_tool(
        name="delegate_text",
        description=(
            "Use only to normalize and measure a supplied text. Never use it to write, "
            "rewrite, summarize, translate, or create poetry."
        ),
    )
    orchestrator = system.agent(
        name="orchestrator_agent",
        instructions=(
            "Route each request to exactly one capability. For multiplication call "
            "delegate_calculator. For text analysis call delegate_text. For unsupported "
            "requests call clarify_scope without calling a specialist. Never call more "
            "than one tool. After a tool result, always write a concise natural-language "
            "answer grounded only in that evidence. If the user requests a poem or other "
            "creative form, produce that form only after the deterministic evidence is "
            "available. When the user specifies an exact output format, return only that "
            "format without a preface, explanation, heading, or epilogue. For unsupported "
            "requests, explicitly state that the requested "
            "capability is outside scope, name the supported tasks, and ask the user to "
            "choose one. Never expose JSON, ToolEnvelope, "
            "Python repr, private reasoning, or implementation details."
        ),
        tools=[calculator_tool, text_tool, clarify_scope],
        framework=framework,
        policy=toolkit.RunPolicy(
            max_turns=5,
            max_tool_calls=1,
            max_tokens=700,
            temperature=0.0,
            tool_choice="auto",
        ),
    )
    executable = system.compile(entrypoint=orchestrator)

    if not supports_model_generation(provider):
        judge_agent = system.agent(
            name="judge_agent",
            instructions="Apply score_semantics exactly once.",
            tools=[score_semantics],
            engine="python-runtime",
            runtime=python_runtime,
            model="python-runtime",
            framework=framework,
            contract=toolkit.AgentContract(must_call=["score_semantics"]),
            policy=toolkit.RunPolicy(
                max_turns=2,
                max_tool_calls=1,
                tool_choice="score_semantics",
                temperature=0.0,
            ),
        )
        judge: Any = DeterministicJudge(judge_agent)
    else:
        judge_tools = [record_semantic_judgment]
        judge_contract = toolkit.AgentContract(
            must_call=["record_semantic_judgment"],
            completion="when_required_tools_satisfied",
        )
        judge_budget = semantic_judge_execution_budget(
            required_tool_calls=len(judge_contract.must_call)
        )
        judge_agent = system.agent(
            name="judge_agent",
            instructions=(
                "You are a strict semantic evaluator. Compare the candidate public "
                "answer, full child lineage, Tool evidence, and expected contract. "
                "Judge request_fulfillment against the expected contract. If that "
                "contract declares a request out of scope, a useful clarification "
                "with no specialist delegation is successful fulfillment; do not "
                "penalize it for refusing the impossible literal request. "
                "A concise answer that explicitly marks the request outside scope, "
                "names the supported capabilities, and asks the user to choose is fully "
                "clear; it need not invent an answer to the unsupported request. "
                "Deterministic validation and recorded Tool evidence are authoritative. "
                "Do not invent undeclared requirements or penalize punctuation, brevity, "
                "wording, or artistic taste when the explicit contract is satisfied. "
                "A parent delegation may summarize or omit output when its child lineage "
                "contains the authoritative specialist and Tool evidence. "
                "Return one typed semantic judgment by calling the "
                "record_semantic_judgment Tool exactly once. Put only criteria that "
                "actually fail in failed_criteria; use an empty list when every criterion "
                "passes. Keep rationale factual and under 80 words; call the Tool "
                "immediately instead of drafting analysis. A claim unsupported by Tool "
                "evidence must fail "
                "evidence_correctness and "
                "no_unsupported_claims. no_unsupported_claims concerns factual claims "
                "only; never fail it for formatting, line count, length, structure, "
                "wording, or artistic style. Those requirements belong only to "
                "request_fulfillment. Raw JSON or technical envelopes must fail clarity "
                "and no_technical_noise."
            ),
            tools=judge_tools,
            framework=framework,
            contract=judge_contract,
            output=None,
            policy=toolkit.RunPolicy(
                max_turns=judge_budget.effective_max_turns,
                max_tool_calls=judge_budget.effective_max_tool_calls,
                max_tokens=semantic_judge_max_tokens(),
                temperature=0.0,
                tool_choice="record_semantic_judgment",
            ),
        )
        judge = AuditedJudge(judge_agent)

    return SemanticCell(
        provider=provider,
        framework=framework,
        model=resolved_model,
        system=system,
        executable=executable,
        judge=judge,
        cases=semantic_cases(provider, framework),
    )


def expected_paths(case: dict[str, Any]) -> tuple[list[str], list[str]]:
    expected = case.get("expected") or {}
    return list(expected.get("agent_path") or []), list(expected.get("tool_path") or [])


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
