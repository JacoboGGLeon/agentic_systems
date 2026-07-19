"""Evaluation helpers for Agentic Systems 1.0.

Evals reuse ``AgenticEnvironment`` so batch evaluation, rewards, memory and
per-step evidence all flow through the same episode abstraction used by table
or graph-based agent runs.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import AgentContract, ValidationResult
from .environments import AgenticEnvironment, GraphState
from .lineage import _short
from .results import RunResult, _contains_subset


class EvalCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    ok: bool
    input: Any
    expected: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any]
    validation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class EvalReproducibility(BaseModel):
    """Describe which sources of variation an eval run controls."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "agentic_systems.eval-reproducibility.v1"
    classification: Literal["deterministic", "seeded", "non_deterministic"] = "non_deterministic"
    seed: int | None = 0
    replayable: bool = False
    conditions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_classification(self) -> "EvalReproducibility":
        if self.classification == "seeded" and self.seed is None:
            raise ValueError("seeded eval reproducibility requires a non-null seed")
        if self.classification == "non_deterministic" and self.replayable:
            raise ValueError("non_deterministic eval reproducibility cannot promise replayable=True")
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "agentic_systems.eval-report.v1"
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
            raise ValueError("EvalReport aggregates are inconsistent: " + "; ".join(problems))
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
                evidence={"total": self.total, "passed": self.passed, "failed": self.failed, "pass_rate": self.pass_rate},
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
                    summary=_short(f"{status}; input={_short(case.input, max_chars=120)}; expected={expected}; actual={actual}.", max_chars=420),
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
                evidence={"total": self.total, "passed": self.passed, "failed": self.failed, "pass_rate": self.pass_rate},
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
    data = answer.get("data") if isinstance(answer.get("data"), dict) else result.get("data") or {}
    final = answer.get("final") if isinstance(answer.get("final"), dict) else result.get("final") or {}
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

    def evaluate_agent(
        self,
        agent: Any,
        cases: list[dict[str, Any]],
        *,
        mode: str = "eval",
        environment_kwargs: dict[str, Any] | None = None,
        determinism: Literal["deterministic", "seeded", "non_deterministic"] = "non_deterministic",
        seed: int | None = 0,
        reproducibility_conditions: list[str] | None = None,
    ) -> EvalReport:
        """Evaluate an agent over cases and return an EvalReport."""

        return run_eval(
            agent,
            cases,
            mode=mode,
            environment_kwargs=environment_kwargs,
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
        determinism: Literal["deterministic", "seeded", "non_deterministic"] = "non_deterministic",
        seed: int | None = 0,
        reproducibility_conditions: list[str] | None = None,
    ) -> EvalReport:
        """Notebook-friendly alias for evaluate_agent."""

        return self.evaluate_agent(
            agent,
            cases,
            mode=mode,
            environment_kwargs=environment_kwargs,
            determinism=determinism,
            seed=seed,
            reproducibility_conditions=reproducibility_conditions,
        )


class _EvalStepGraph:
    """Graph-shaped adapter that evaluates one case per environment step."""

    def __init__(self, agent: Any, *, mode: str) -> None:
        self.agent = agent
        self.mode = mode

    def invoke(self, state: GraphState) -> GraphState:
        case = state["row"]
        index = state.get("episode", {}).get("step_index", 0)
        name = str(case.get("name") or f"case_{index + 1}")
        expected = dict(case.get("expected") or {})
        contract = _contract_from_case(case, expected)
        result: RunResult = _run_agent_case(self.agent, case.get("input"), mode=self.mode, config=case.get("config"))
        validation = result.validate(contract)
        _apply_expected_assertions(validation, result, expected)
        ok = result.ok and validation.ok
        return {
            **state,
            "eval": {
                "name": name,
                "ok": ok,
                "input": case.get("input"),
                "expected": expected,
                "result": result.to_dict(),
                "validation": validation.to_dict(),
            },
            "memory": {
                **(state.get("memory") or {}),
                "evaluated": [*(state.get("memory") or {}).get("evaluated", []), name],
                "passed": [*(state.get("memory") or {}).get("passed", []), name] if ok else (state.get("memory") or {}).get("passed", []),
            },
        }


def run_eval(
    agent: Any,
    cases: list[dict[str, Any]],
    *,
    mode: str = "eval",
    environment_kwargs: dict[str, Any] | None = None,
    determinism: Literal["deterministic", "seeded", "non_deterministic"] = "non_deterministic",
    seed: int | None = 0,
    reproducibility_conditions: list[str] | None = None,
) -> EvalReport:
    """Run a classified batch eval through ``AgenticEnvironment``.

    Each case is one environment step. The graph invokes the agent, validates
    contracts and expected outputs, and writes the evidence into the step state.
    This keeps evals aligned with episodic memory, rewards and renderable
    histories instead of maintaining a separate batch runner.
    """

    kwargs = dict(environment_kwargs or {})
    kwargs.setdefault("name", "agent_eval")
    env = AgenticEnvironment(
        records=cases,
        graph=_EvalStepGraph(agent, mode=mode),
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
        default_conditions.append("agent, graph, scorer, and provider contain no uncontrolled randomness")
    else:
        default_conditions.append("uncontrolled model, provider, tool, or external randomness may vary results")
    return EvalReproducibility(
        classification=classification,
        seed=seed,
        replayable=classification != "non_deterministic",
        conditions=[*default_conditions, *(conditions or [])],
    )


def _run_agent_case(agent: Any, input_value: Any, *, mode: str, config: Any) -> RunResult:
    if hasattr(agent, "run"):
        return agent.run(input_value, mode=mode, config=config)
    return agent.run_sync(input_value, mode=mode, config=config)


def _contract_from_case(case: dict[str, Any], expected: dict[str, Any]) -> AgentContract:
    contract = AgentContract.coerce(case.get("contract") or {})
    if "must_call" in expected:
        contract.must_call = list(expected["must_call"])
    if "expected_tool_outputs" in expected:
        contract.expected_tool_outputs = dict(expected["expected_tool_outputs"])
    return contract


def _eval_reward(graph_state: GraphState, row: dict[str, Any], action: Any, env: AgenticEnvironment) -> float:
    return 1.0 if graph_state.get("eval", {}).get("ok") else 0.0


def _apply_expected_assertions(validation: ValidationResult, result: RunResult, expected: dict[str, Any]) -> None:
    if "text_contains" in expected and str(expected["text_contains"]) not in result.text:
        validation.add(
            "expected_text_missing",
            f"Expected text to contain {expected['text_contains']!r}.",
            path="text",
        )
    if "data_contains" in expected and not _contains_subset(result.data, expected["data_contains"]):
        validation.add(
            "expected_data_mismatch",
            "Expected data subset not found.",
            path="data",
            meta={"expected": expected["data_contains"], "actual": result.data},
        )

