"""Evaluation helpers for Agentic Systems 1.0.

Evals reuse ``AgenticEnvironment`` so batch evaluation, rewards, memory and
per-step evidence all flow through the same episode abstraction used by table
or graph-based agent runs.
"""

from __future__ import annotations
import json

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import AgentContract, ValidationResult
from .environments import AgenticEnvironment, GraphState
from .lineage import _short
from .providers.base import ToolEnvelope
from .results import RunResult, _contains_subset, is_technical_public_answer
from .usage import merge_usage


DEFAULT_JUDGE_CRITERIA = (
    "request_fulfillment",
    "evidence_correctness",
    "clarity",
    "no_technical_noise",
    "no_unsupported_claims",
)

DEFAULT_JUDGE_INSTRUCTIONS = (
    "Evaluate request_fulfillment against the declared expected contract, not "
    "against an impossible literal interpretation of the user's request. A safe "
    "refusal or useful clarification is full request fulfillment when the expected "
    "contract declares the request out of scope and the candidate performs no "
    "unsupported delegation. Treat deterministic validation and recorded Tool "
    "evidence as authoritative facts; never invent missing evidence or penalize "
    "behavior that the expected contract explicitly requires. Do not invent style, "
    "length, wording, or evidence requirements absent from the expected contract. "
    "When deterministic validation passed and every declared requirement is visibly "
    "satisfied, request_fulfillment must not be reduced for subjective preference. "
    "no_unsupported_claims evaluates only factual assertions that are not backed by "
    "the candidate evidence. Formatting, structure, length, and artistic style belong "
    "only to request_fulfillment and must never reduce no_unsupported_claims. "
    "A parent delegation output may be summarized or empty when the child RunResult "
    "and its Tool evidence are present in lineage; treat that child evidence as "
    "authoritative."
)


class JudgeRubric(BaseModel):
    """Typed semantic rubric shared by deterministic and model judges."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    criteria: tuple[str, ...] = DEFAULT_JUDGE_CRITERIA
    threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    instructions: str = DEFAULT_JUDGE_INSTRUCTIONS
    certification_tool: str | None = None
    deterministic_authority: tuple[str, ...] = (
        "request_fulfillment",
        "evidence_correctness",
    )
    require_failure_findings: bool = True


class JudgeFinding(BaseModel):
    """Evidence-backed reason for one criterion scored below threshold."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion: str
    evidence: str = Field(min_length=1, max_length=1000)


class JudgeResult(BaseModel):
    """Normalized, auditable semantic verdict."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    score: float = Field(ge=0.0, le=1.0)
    criteria: dict[str, float] = Field(default_factory=dict)
    raw_score: float | None = Field(default=None, ge=0.0, le=1.0)
    raw_criteria: dict[str, float] = Field(default_factory=dict)
    deterministic_authority: tuple[str, ...] = ()
    threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    deterministic_validation_ok: bool = True
    execution_ok: bool = True
    certification_tool: str | None = None
    certification_recorded: bool = True
    findings: tuple[JudgeFinding, ...] = ()
    consistent: bool = True
    consistency_issues: tuple[str, ...] = ()
    rationale: str = ""
    provider: str | None = None
    framework: str | None = None
    model: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_verdict(self) -> "JudgeResult":
        if any(score < 0.0 or score > 1.0 for score in self.criteria.values()):
            raise ValueError("Judge criterion scores must be between 0 and 1")
        if any(score < 0.0 or score > 1.0 for score in self.raw_criteria.values()):
            raise ValueError("Raw judge criterion scores must be between 0 and 1")
        criteria_ok = (
            self.deterministic_validation_ok
            and self.execution_ok
            and self.certification_recorded
            and self.consistent
            and bool(self.criteria)
            and all(score >= self.threshold for score in self.criteria.values())
        )
        if self.consistent != (not self.consistency_issues):
            raise ValueError(
                "JudgeResult.consistent must reflect consistency_issues"
            )
        if self.ok != criteria_ok:
            raise ValueError(
                "JudgeResult.ok must equal the threshold verdict for every criterion"
            )
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class EvalCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    ok: bool
    input: Any
    expected: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any]
    validation: dict[str, Any]
    deterministic_validation: dict[str, Any] | None = None
    judge: JudgeResult | None = None
    candidate_usage: dict[str, Any] = Field(default_factory=dict)
    judge_usage: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class EvalReproducibility(BaseModel):
    """Describe which sources of variation an eval run controls."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "agentic_systems.eval-reproducibility.v1"
    classification: Literal["deterministic", "seeded", "non_deterministic"] = (
        "non_deterministic"
    )
    seed: int | None = 0
    replayable: bool = False
    conditions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_classification(self) -> "EvalReproducibility":
        if self.classification == "seeded" and self.seed is None:
            raise ValueError("seeded eval reproducibility requires a non-null seed")
        if self.classification == "non_deterministic" and self.replayable:
            raise ValueError(
                "non_deterministic eval reproducibility cannot promise replayable=True"
            )
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "agentic_systems.eval-report.v2"
    ok: bool
    total: int
    passed: int
    failed: int
    pass_rate: float
    cases: list[EvalCaseResult]
    reproducibility: EvalReproducibility = Field(default_factory=EvalReproducibility)

    @model_validator(mode="after")
    def validate_aggregates(self) -> "EvalReport":
        actual_total = len(self.cases)
        actual_passed = sum(1 for case in self.cases if case.ok)
        actual_failed = actual_total - actual_passed
        actual_rate = (actual_passed / actual_total) if actual_total else 1.0
        problems = []
        if self.total != actual_total:
            problems.append(f"total={self.total}, expected {actual_total}")
        if self.passed != actual_passed:
            problems.append(f"passed={self.passed}, expected {actual_passed}")
        if self.failed != actual_failed:
            problems.append(f"failed={self.failed}, expected {actual_failed}")
        if abs(self.pass_rate - actual_rate) > 1e-12:
            problems.append(f"pass_rate={self.pass_rate}, expected {actual_rate}")
        if self.ok != (actual_failed == 0):
            problems.append(f"ok={self.ok}, expected {actual_failed == 0}")
        if problems:
            raise ValueError(
                "EvalReport aggregates are inconsistent: " + "; ".join(problems)
            )
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def normalized(self) -> dict[str, Any]:
        """Return a RunResult-shaped view for ``lab.human_result``.

        ``EvalReport`` is not a model call, but notebooks should still be able
        to render it with the same human-output API used for agents, tools and
        environments.  The runtime block therefore describes the evaluation
        runner, while the answer block keeps the batch summary first.
        """

        return {
            "schema_version": "agentic_systems.run.v1",
            "ok": self.ok,
            "runtime": {
                "engine": "environment",
                "framework": "agentic-eval",
                "mode": "eval",
            },
            "input": {
                "total_cases": self.total,
                "reproducibility": self.reproducibility.to_dict(),
            },
            "answer": {
                "text": self.summary_text(),
                "final": {
                    "summary": self.summary_text(),
                    "total": self.total,
                    "passed": self.passed,
                    "failed": self.failed,
                    "pass_rate": self.pass_rate,
                    "reproducibility": self.reproducibility.to_dict(),
                },
                "data": self.to_dict(),
            },
            "tools": [],
            "usage": {},
            "validation": {
                "ok": self.ok,
                "passed": self.passed,
                "failed": self.failed,
            },
            "errors": [
                {"code": "eval_case_failed", "message": case.name}
                for case in self.cases
                if not case.ok
            ],
        }

    def summary_text(self) -> str:
        return (
            f"Eval processed {self.total} case(s); "
            f"passed={self.passed}, failed={self.failed}, "
            f"pass_rate={self.pass_rate:.2%}."
        )

    def raise_if_failed(self) -> "EvalReport":
        if not self.ok:
            failed = [case.name for case in self.cases if not case.ok]
            raise AssertionError(f"Eval failed for cases: {failed}")
        return self

    def lineage(
        self,
        *,
        name: str = "eval_report.lineage",
        question: str = "",
        goal: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Project an eval report into Lineage Memory."""

        from .lineage import LINEAGE_SCHEMA_VERSION, LineageMemory, LineageStep, _short

        answer = self.summary_text()
        steps = [
            LineageStep(
                step_id="eval_report",
                kind="input",
                title="Eval batch",
                summary=answer,
                source="EvalReport",
                why="Evals usan el mismo patrón batch/episodio que environments.",
                evidence={
                    "total": self.total,
                    "passed": self.passed,
                    "failed": self.failed,
                    "pass_rate": self.pass_rate,
                },
            )
        ]
        for index, case in enumerate(self.cases, start=1):
            actual = _case_actual_summary(case)
            expected = _case_expected_summary(case.expected)
            status = "OK" if case.ok else "REVISAR"
            steps.append(
                LineageStep(
                    step_id=f"case_{index}",
                    kind="decision",
                    title=f"Eval case: {case.name}",
                    summary=_short(
                        f"{status}; input={_short(case.input, max_chars=120)}; expected={expected}; actual={actual}.",
                        max_chars=420,
                    ),
                    source="EvalCaseResult",
                    why="El eval ejecutó el caso y comparó la salida real contra contrato/expectativa declarativa.",
                    evidence={
                        "name": case.name,
                        "ok": case.ok,
                        "input": case.input,
                        "expected": case.expected,
                        "actual": _case_actual_evidence(case),
                        "validation": case.validation,
                    },
                )
            )
        steps.append(
            LineageStep(
                step_id="eval_scoring",
                kind="validation",
                title="Eval scoring",
                summary=answer,
                source="EvalReport",
                why="El score agregado se calcula desde los casos ejecutados, no desde una respuesta inventada.",
                evidence={
                    "total": self.total,
                    "passed": self.passed,
                    "failed": self.failed,
                    "pass_rate": self.pass_rate,
                },
            )
        )
        return LineageMemory(
            schema_version=LINEAGE_SCHEMA_VERSION,
            name=name,
            question=question,
            goal=goal,
            answer=answer,
            ok=self.ok,
            steps=steps,
            tags=["eval", *(tags or [])],
            metadata=metadata or {},
        )


def _case_expected_summary(expected: dict[str, Any]) -> str:
    if not expected:
        return "sin expectativa explícita"
    if "data_contains" in expected:
        data = expected.get("data_contains") or {}
        tool = data.get("tool") if isinstance(data, dict) else None
        value = data.get("value") if isinstance(data, dict) else None
        if tool is not None and value is not None:
            return f"tool={tool}, value={value}"
    if "must_call" in expected:
        return f"must_call={expected['must_call']}"
    return _short(expected, max_chars=160)


def _case_actual_evidence(case: EvalCaseResult) -> dict[str, Any]:
    result = case.result or {}
    answer = result.get("answer") if isinstance(result.get("answer"), dict) else {}
    data = (
        answer.get("data")
        if isinstance(answer.get("data"), dict)
        else result.get("data") or {}
    )
    final = (
        answer.get("final")
        if isinstance(answer.get("final"), dict)
        else result.get("final") or {}
    )
    tools = result.get("tools") if isinstance(result.get("tools"), list) else []
    return {
        "ok": result.get("ok"),
        "text": answer.get("text") or result.get("text"),
        "final": final,
        "data": data,
        "tools": [
            {
                "name": tool.get("name"),
                "ok": tool.get("ok"),
                "summary": tool.get("summary"),
            }
            for tool in tools
            if isinstance(tool, dict)
        ],
    }


def _case_actual_summary(case: EvalCaseResult) -> str:
    evidence = _case_actual_evidence(case)
    final = evidence.get("final") if isinstance(evidence.get("final"), dict) else {}
    data = evidence.get("data") if isinstance(evidence.get("data"), dict) else {}
    if final.get("summary"):
        return str(final["summary"])
    pieces = []
    for payload in (data, final):
        if payload.get("tool") is not None:
            pieces.append(f"tool={payload.get('tool')}")
        if payload.get("value") is not None:
            pieces.append(f"value={payload.get('value')}")
        elif payload.get("result") is not None:
            pieces.append(f"result={payload.get('result')}")
        if payload.get("ok") is not None:
            pieces.append(f"ok={payload.get('ok')}")
        if pieces:
            return ", ".join(pieces)
    tools = evidence.get("tools") or []
    if tools:
        return ", ".join(str(tool.get("name") or "tool") for tool in tools)
    return "sin salida estructurada"


class Evaluator:
    """Small public evaluation facade."""

    def evaluate(
        self,
        executable: Any,
        cases: list[dict[str, Any]],
        *,
        mode: str = "eval",
        environment_kwargs: dict[str, Any] | None = None,
        judge: Any | None = None,
        rubric: JudgeRubric | dict[str, Any] | None = None,
        determinism: Literal[
            "deterministic", "seeded", "non_deterministic"
        ] = "non_deterministic",
        seed: int | None = 0,
        reproducibility_conditions: list[str] | None = None,
    ) -> EvalReport:
        """Evaluate any Executable over cases and return an EvalReport."""

        if not callable(getattr(executable, "run", None)):
            raise TypeError(
                "Evaluator.evaluate(...) expects an object with run(input, **kwargs)."
            )
        return run_eval(
            executable,
            cases,
            mode=mode,
            environment_kwargs=environment_kwargs,
            judge=judge,
            rubric=rubric,
            determinism=determinism,
            seed=seed,
            reproducibility_conditions=reproducibility_conditions,
        )

    def evaluate_agent(
        self,
        agent: Any,
        cases: list[dict[str, Any]],
        *,
        mode: str = "eval",
        environment_kwargs: dict[str, Any] | None = None,
        judge: Any | None = None,
        rubric: JudgeRubric | dict[str, Any] | None = None,
        determinism: Literal[
            "deterministic", "seeded", "non_deterministic"
        ] = "non_deterministic",
        seed: int | None = 0,
        reproducibility_conditions: list[str] | None = None,
    ) -> EvalReport:
        """Evaluate an agent over cases and return an EvalReport."""

        return run_eval(
            agent,
            cases,
            mode=mode,
            environment_kwargs=environment_kwargs,
            judge=judge,
            rubric=rubric,
            determinism=determinism,
            seed=seed,
            reproducibility_conditions=reproducibility_conditions,
        )

    def run(
        self,
        agent: Any,
        cases: list[dict[str, Any]],
        *,
        mode: str = "eval",
        environment_kwargs: dict[str, Any] | None = None,
        judge: Any | None = None,
        rubric: JudgeRubric | dict[str, Any] | None = None,
        determinism: Literal[
            "deterministic", "seeded", "non_deterministic"
        ] = "non_deterministic",
        seed: int | None = 0,
        reproducibility_conditions: list[str] | None = None,
    ) -> EvalReport:
        """Notebook-friendly alias for evaluate_agent."""

        return self.evaluate_agent(
            agent,
            cases,
            mode=mode,
            environment_kwargs=environment_kwargs,
            judge=judge,
            rubric=rubric,
            determinism=determinism,
            seed=seed,
            reproducibility_conditions=reproducibility_conditions,
        )


class _EvalStepGraph:
    """Graph-shaped adapter that evaluates one case per environment step."""

    def __init__(
        self, agent: Any, *, mode: str, judge: Any | None, rubric: JudgeRubric
    ) -> None:
        self.agent = agent
        self.mode = mode
        self.judge = judge
        self.rubric = rubric

    def invoke(self, state: GraphState) -> GraphState:
        case = state["row"]
        index = state.get("episode", {}).get("step_index", 0)
        name = str(case.get("name") or f"case_{index + 1}")
        expected = dict(case.get("expected") or {})
        contract = _contract_from_case(case, expected)
        result: RunResult = _run_agent_case(
            self.agent, case.get("input"), mode=self.mode, config=case.get("config")
        )
        validation = result.validate(contract)
        _apply_expected_assertions(validation, result, expected)
        deterministic_ok = result.ok and validation.ok
        judge_result = _run_judge(
            self.judge,
            case=case,
            result=result,
            rubric=self.rubric,
            deterministic_ok=deterministic_ok,
        )
        candidate_usage = _candidate_usage(result)
        judge_usage = dict(judge_result.usage) if judge_result is not None else {}
        aggregate_usage = merge_usage(candidate_usage, judge_usage)
        ok = deterministic_ok and (judge_result is None or judge_result.ok)
        return {
            **state,
            "eval": {
                "name": name,
                "ok": ok,
                "input": case.get("input"),
                "expected": expected,
                "result": result.to_dict(),
                "validation": validation.to_dict(),
                "deterministic_validation": validation.to_dict(),
                "judge": judge_result.to_dict() if judge_result is not None else None,
                "candidate_usage": candidate_usage,
                "judge_usage": judge_usage,
                "usage": aggregate_usage,
            },
            "memory": {
                **(state.get("memory") or {}),
                "evaluated": [*(state.get("memory") or {}).get("evaluated", []), name],
                "passed": [*(state.get("memory") or {}).get("passed", []), name]
                if ok
                else (state.get("memory") or {}).get("passed", []),
            },
        }


def run_eval(
    agent: Any,
    cases: list[dict[str, Any]],
    *,
    mode: str = "eval",
    environment_kwargs: dict[str, Any] | None = None,
    judge: Any | None = None,
    rubric: JudgeRubric | dict[str, Any] | None = None,
    determinism: Literal[
        "deterministic", "seeded", "non_deterministic"
    ] = "non_deterministic",
    seed: int | None = 0,
    reproducibility_conditions: list[str] | None = None,
) -> EvalReport:
    """Run a classified batch eval through ``AgenticEnvironment``.

    Each case is one environment step. The graph invokes the agent, validates
    contracts and expected outputs, and writes the evidence into the step state.
    This keeps evals aligned with episodic memory, rewards and renderable
    histories instead of maintaining a separate batch runner.
    """

    resolved_rubric = JudgeRubric.model_validate(rubric or {})
    kwargs = dict(environment_kwargs or {})
    kwargs.setdefault("name", "agent_eval")
    env = AgenticEnvironment(
        records=cases,
        graph=_EvalStepGraph(agent, mode=mode, judge=judge, rubric=resolved_rubric),
        reward_fn=_eval_reward,
        **kwargs,
    )
    observation, _info = env.reset(seed=seed)
    while observation is not None:
        observation, _reward, terminated, truncated, _info = env.step()
        if terminated or truncated:
            break

    results = [
        EvalCaseResult(**transition.graph_state["eval"])
        for transition in env.history
        if "eval" in transition.graph_state
    ]
    passed = len([case for case in results if case.ok])
    total = len(results)
    return EvalReport(
        ok=passed == total,
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=(passed / total) if total else 1.0,
        cases=results,
        reproducibility=_eval_reproducibility(
            determinism,
            seed=seed,
            conditions=reproducibility_conditions,
        ),
    )


def _eval_reproducibility(
    classification: Literal["deterministic", "seeded", "non_deterministic"],
    *,
    seed: int | None,
    conditions: list[str] | None,
) -> EvalReproducibility:
    default_conditions = [
        "same ordered cases and inputs",
        "same Agentic Systems, dependency, runtime, and provider configuration",
        "all tools and external side effects deterministic or replayed",
    ]
    if classification == "seeded":
        default_conditions.append("all stochastic components consume the declared seed")
    elif classification == "deterministic":
        default_conditions.append(
            "agent, graph, scorer, and provider contain no uncontrolled randomness"
        )
    else:
        default_conditions.append(
            "uncontrolled model, provider, tool, or external randomness may vary results"
        )
    return EvalReproducibility(
        classification=classification,
        seed=seed,
        replayable=classification != "non_deterministic",
        conditions=[*default_conditions, *(conditions or [])],
    )


def _candidate_usage(result: RunResult) -> dict[str, Any]:
    """Aggregate actual agent executions without double-counting plan projections."""

    nodes = list(result.walk())
    agent_nodes = [node for node in nodes if node.meta.get("agent_name")]
    if not agent_nodes:
        return dict(result.usage or {})
    return merge_usage(*(dict(node.usage or {}) for node in agent_nodes))


def _run_judge(
    judge: Any | None,
    *,
    case: dict[str, Any],
    result: RunResult,
    rubric: JudgeRubric,
    deterministic_ok: bool,
) -> JudgeResult | None:
    if judge is None:
        return None
    request = {
        "task": "semantic_judge",
        "rubric": rubric.model_dump(mode="json"),
        "case": {
            "name": case.get("name"),
            "input": case.get("input"),
            "expected": case.get("expected") or {},
        },
        "candidate": _judge_candidate_view(result),
    }
    try:
        judged = judge.run(request, mode="eval")
    except TypeError:
        judged = judge.run(request)
    payload, certification_recorded, certification_issues = (
        _certification_payload(judged, rubric.certification_tool)
    )
    consistency_issues = list(certification_issues)
    payload_criteria = payload.get("criteria")
    payload_criteria = payload_criteria if isinstance(payload_criteria, dict) else {}
    missing_criteria = [name for name in rubric.criteria if name not in payload_criteria]
    unknown_criteria = [name for name in payload_criteria if name not in rubric.criteria]
    if missing_criteria:
        consistency_issues.append(
            "missing judge criteria: " + ", ".join(sorted(missing_criteria))
        )
    if unknown_criteria:
        consistency_issues.append(
            "unknown judge criteria: " + ", ".join(sorted(unknown_criteria))
        )
    raw_criteria: dict[str, float] = {}
    for name in rubric.criteria:
        try:
            raw_criteria[name] = float(payload_criteria.get(name, 0.0))
        except (TypeError, ValueError):
            raw_criteria[name] = 0.0
            consistency_issues.append(f"criterion {name!r} is not numeric")
    criteria = dict(raw_criteria)
    expected_raw_score = (
        sum(raw_criteria.values()) / len(raw_criteria) if raw_criteria else 0.0
    )
    try:
        raw_score = float(payload.get("score", expected_raw_score))
    except (TypeError, ValueError):
        raw_score = expected_raw_score
        consistency_issues.append("judge score is not numeric")
    if abs(raw_score - expected_raw_score) > 1e-9:
        consistency_issues.append(
            "judge score does not equal the mean of criterion scores"
        )
    findings: list[JudgeFinding] = []
    raw_findings = payload.get("findings", [])
    if not isinstance(raw_findings, list):
        consistency_issues.append("judge findings must be a list")
        raw_findings = []
    for index, item in enumerate(raw_findings):
        try:
            findings.append(JudgeFinding.model_validate(item))
        except (TypeError, ValueError) as exc:
            consistency_issues.append(
                f"judge finding {index} is invalid: {str(exc).splitlines()[0]}"
            )
    finding_names = [finding.criterion for finding in findings]
    if len(set(finding_names)) != len(finding_names):
        consistency_issues.append("judge findings contain duplicate criteria")
    failed_criteria = {
        name for name, value in raw_criteria.items() if value < rubric.threshold
    }
    finding_criteria = set(finding_names)
    if rubric.require_failure_findings:
        for name in sorted(failed_criteria - finding_criteria):
            consistency_issues.append(
                f"failed criterion {name!r} has no evidence-backed finding"
            )
        for name in sorted(finding_criteria - failed_criteria):
            consistency_issues.append(
                f"finding for passing or unknown criterion {name!r} is inconsistent"
            )
    if deterministic_ok:
        for name in rubric.deterministic_authority:
            if name in criteria:
                criteria[name] = 1.0
    score = sum(criteria.values()) / len(criteria) if criteria else 0.0
    provider = payload.get("provider")
    framework = payload.get("framework")
    model = payload.get("model")
    usage: dict[str, Any] = {}
    execution_ok = True
    if isinstance(judged, RunResult):
        execution_ok = judged.ok
        provider = judged.engine
        framework = judged.meta.get("framework_adapter") or judged.meta.get("framework")
        model = judged.model
        usage = dict(judged.usage or {})
    consistent = not consistency_issues
    threshold_ok = bool(criteria) and all(
        value >= rubric.threshold for value in criteria.values()
    )
    return JudgeResult(
        ok=(
            deterministic_ok
            and execution_ok
            and certification_recorded
            and consistent
            and threshold_ok
        ),
        score=score,
        criteria=criteria,
        raw_score=raw_score,
        raw_criteria=raw_criteria,
        deterministic_authority=rubric.deterministic_authority,
        threshold=rubric.threshold,
        deterministic_validation_ok=deterministic_ok,
        execution_ok=execution_ok,
        certification_tool=rubric.certification_tool,
        certification_recorded=certification_recorded,
        findings=tuple(findings),
        consistent=consistent,
        consistency_issues=tuple(consistency_issues),
        rationale=str(payload.get("rationale") or ""),
        provider=str(provider) if provider else None,
        framework=str(framework) if framework else None,
        model=str(model) if model else None,
        usage=usage,
    )


def _certification_payload(
    judged: Any,
    certification_tool: str | None,
) -> tuple[dict[str, Any], bool, tuple[str, ...]]:
    """Select the structured certification event as the verdict authority.

    A framework may synthesize or reshape the Tool result in its final assistant
    message. When a rubric requires a certification Tool, only that successful,
    uniquely named Tool event is authoritative; final model text remains presentation.
    """

    fallback = _judge_payload(judged)
    if certification_tool is None:
        return fallback, True, ()
    if not isinstance(judged, RunResult):
        return fallback, False, ()
    matching_events = [
        event
        for event in judged.tool_events
        if event.name == certification_tool and event.ok
    ]
    if len(matching_events) != 1:
        return fallback, False, ()
    output = matching_events[0].output
    if not isinstance(output, dict):
        return (
            fallback,
            True,
            ("judge certification Tool output must be a structured object",),
        )
    try:
        envelope = ToolEnvelope.model_validate(output)
    except (TypeError, ValueError):
        return dict(output), True, ()
    return dict(envelope.data), True, ()


def _judge_candidate_view(result: RunResult) -> dict[str, Any]:
    """Project complete lineage once, without presentation or recursive duplication."""

    executions: list[dict[str, Any]] = []
    for node in result.walk():
        normalized = node.normalized()
        has_children = bool(node.children)
        tools = [
            {
                "name": tool.get("name"),
                "ok": tool.get("ok"),
                "input": tool.get("input"),
                "output": None if has_children else tool.get("output"),
                "error": tool.get("error"),
            }
            for tool in normalized.get("tools", [])
            if isinstance(tool, dict)
        ]
        executions.append(
            {
                "execution": normalized.get("execution"),
                "agent": node.meta.get("agent_name"),
                "runtime": normalized.get("runtime"),
                "answer": {"text": (normalized.get("answer") or {}).get("text")},
                "tools": tools,
                "validation": normalized.get("validation"),
                "errors": normalized.get("errors"),
            }
        )

    root = executions[0] if executions else {}
    return {
        "ok": result.ok,
        "runtime": root.get("runtime"),
        "answer": root.get("answer"),
        "executions": executions,
    }


def _judge_payload(judged: Any) -> dict[str, Any]:
    if isinstance(judged, dict):
        sources = [judged]
    elif isinstance(judged, RunResult):
        sources = [
            judged.data,
            judged.final,
            *(event.output for event in judged.tool_events),
        ]
        try:
            sources.append(json.loads(judged.text))
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    else:
        sources = []

    def _find(value: Any, *, depth: int = 0) -> dict[str, Any] | None:
        if depth > 6:
            return None
        if isinstance(value, dict):
            if isinstance(value.get("criteria"), dict):
                return value
            priority = ("judge", "data", "output", "result", "final_output")
            ordered = [value.get(key) for key in priority if key in value]
            ordered.extend(item for key, item in value.items() if key not in priority)
            for item in ordered:
                found = _find(item, depth=depth + 1)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = _find(item, depth=depth + 1)
                if found is not None:
                    return found
        elif isinstance(value, str):
            try:
                decoded = json.loads(value)
            except (TypeError, ValueError, json.JSONDecodeError):
                return None
            if decoded != value:
                return _find(decoded, depth=depth + 1)
            for item in value:
                found = _find(item, depth=depth + 1)
                if found is not None:
                    return found
        return None

    for source in sources:
        found = _find(source)
        if found is not None:
            return found
    return {}


def _run_agent_case(
    agent: Any, input_value: Any, *, mode: str, config: Any
) -> RunResult:
    if hasattr(agent, "run"):
        return agent.run(input_value, mode=mode, config=config)
    return agent.run_sync(input_value, mode=mode, config=config)


def _contract_from_case(
    case: dict[str, Any], expected: dict[str, Any]
) -> AgentContract:
    contract = AgentContract.coerce(case.get("contract") or {})
    if "must_call" in expected:
        contract.must_call = list(expected["must_call"])
    if "expected_tool_outputs" in expected:
        contract.expected_tool_outputs = dict(expected["expected_tool_outputs"])
    return contract


def _eval_reward(
    graph_state: GraphState, row: dict[str, Any], action: Any, env: AgenticEnvironment
) -> float:
    return 1.0 if graph_state.get("eval", {}).get("ok") else 0.0


def _apply_expected_assertions(
    validation: ValidationResult, result: RunResult, expected: dict[str, Any]
) -> None:
    if "text_contains" in expected:
        raw_fragments = expected["text_contains"]
        fragments = (
            [raw_fragments] if isinstance(raw_fragments, str) else list(raw_fragments)
        )
        missing = [
            str(fragment) for fragment in fragments if str(fragment) not in result.text
        ]
        if missing:
            validation.add(
                "expected_text_missing",
                f"Expected text to contain every declared fragment; missing {missing!r}.",
                path="text",
            )
    if "data_contains" in expected and not _contains_subset(
        result.data, expected["data_contains"]
    ):
        validation.add(
            "expected_data_mismatch",
            "Expected data subset not found.",
            path="data",
            meta={"expected": expected["data_contains"], "actual": result.data},
        )
    if expected.get("human_answer") and (
        not result.text.strip() or is_technical_public_answer(result.text)
    ):
        validation.add(
            "non_human_public_answer",
            "Expected a natural public answer, not an internal envelope or repr.",
            path="text",
        )
    nodes = list(result.walk())
    identity_node = next(
        (node for node in nodes if node.meta.get("agent_name")), result
    )
    expected_provider = expected.get("provider")
    actual_provider = identity_node.engine
    if expected_provider and actual_provider != expected_provider:
        validation.add(
            "provider_identity_mismatch",
            f"Expected provider {expected_provider!r}, observed {actual_provider!r}.",
            path="runtime.provider",
        )
    expected_framework = expected.get("framework")
    actual_framework = identity_node.meta.get(
        "framework_adapter"
    ) or identity_node.meta.get("framework")
    if expected_framework and actual_framework != expected_framework:
        validation.add(
            "framework_identity_mismatch",
            f"Expected framework {expected_framework!r}, observed {actual_framework!r}.",
            path="runtime.framework",
        )
    execution_nodes = [node for node in nodes if node.meta.get("agent_name")]
    tool_nodes = execution_nodes or nodes
    tool_path = [
        event.name for node in tool_nodes for event in (node.tool_events or [])
    ]
    agent_path = [str(node.meta["agent_name"]) for node in execution_nodes]
    execution_path = [
        {
            "provider": node.engine,
            "framework": node.meta.get("framework_adapter")
            or node.meta.get("framework"),
        }
        for node in nodes
    ]
    if "allowed_tool_paths" in expected:
        allowed_tool_paths = [
            list(path)
            for path in expected["allowed_tool_paths"]
            if isinstance(path, (list, tuple))
        ]
        if tool_path not in allowed_tool_paths:
            validation.add(
                "tool_path_not_allowed",
                "Observed Tool path is not one of the declared semantic routes.",
                path="lineage.tools",
                meta={"allowed": allowed_tool_paths, "actual": tool_path},
            )
    if "tool_path" in expected and tool_path != list(expected["tool_path"]):
        validation.add(
            "tool_path_mismatch",
            "Observed Tool path differs from the declared semantic route.",
            path="lineage.tools",
            meta={"expected": expected["tool_path"], "actual": tool_path},
        )
    if "agent_path" in expected and agent_path != list(expected["agent_path"]):
        validation.add(
            "agent_path_mismatch",
            "Observed Agent path differs from the declared semantic route.",
            path="lineage.agents",
            meta={"expected": expected["agent_path"], "actual": agent_path},
        )
    if "execution_path" in expected and not _contains_subset(
        execution_path, expected["execution_path"]
    ):
        validation.add(
            "execution_path_mismatch",
            "Observed provider/framework lineage differs from the declared route.",
            path="lineage.executions",
            meta={"expected": expected["execution_path"], "actual": execution_path},
        )
    if expected.get("no_fallback") and any(
        node.meta.get("fallback_provider") for node in nodes
    ):
        validation.add(
            "unexpected_provider_fallback",
            "Semantic certification forbids provider fallback.",
            path="runtime.fallback_provider",
        )
    for tool_name, subset in (expected.get("tool_output_contains") or {}).items():
        matching = [
            event
            for node in nodes
            for event in (node.tool_events or [])
            if event.name == tool_name
        ]
        if not matching or not any(
            _contains_subset(event.output, subset)
            or _contains_subset(event.output.get("data", {}), subset)
            for event in matching
        ):
            validation.add(
                "expected_tool_evidence_missing",
                f"Expected evidence from Tool {tool_name!r} was not observed.",
                path=f"lineage.tools.{tool_name}",
                meta={"expected": subset},
            )
