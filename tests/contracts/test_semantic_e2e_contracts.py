from __future__ import annotations

import concurrent.futures
from typing import Any

from pydantic import BaseModel, ConfigDict

import agentic_systems as toolkit
from agentic_systems.core.scheduler import execute_sync
from agentic_systems.evals import _judge_candidate_view
from agentic_systems.results import RunResult, ToolEvent


class MultiplyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    a: int
    b: int


class StructuredAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str


@toolkit.tool
def multiply(a: int, b: int) -> dict:
    return {"result": a * b}


def test_system_entrypoint_delegation_preserves_skill_agent_hierarchy() -> None:
    runtime = toolkit.runtime(provider="python-runtime", model="python-runtime")
    system = toolkit.system(runtime=runtime, model="python-runtime")
    math_skill = toolkit.Skill(
        name="deterministic_math",
        description="Validated arithmetic evidence.",
        tools=[multiply],
    )
    specialist = system.agent(
        name="calculator_agent",
        instructions="Produce exact multiplication evidence.",
        skills=[math_skill],
        input=MultiplyInput,
        contract=toolkit.AgentContract(must_call=["multiply"]),
    )
    delegate = specialist.as_tool(
        name="delegate_calculator",
        description="Delegate exact multiplication to CalculatorAgent.",
    )
    system.agent(
        name="orchestrator_agent",
        instructions="Choose exactly one specialist.",
        tools=[delegate],
        contract=toolkit.AgentContract(must_call=["delegate_calculator"]),
    )

    result = system.run(
        {
            "tool": "delegate_calculator",
            "input": {"a": 17, "b": 19},
        },
        entrypoint="orchestrator_agent",
        mode="eval",
    )

    assert result.ok is True
    assert result.meta["entrypoint"] == "orchestrator_agent"
    assert len(result.children) == 1
    orchestrator_result = result.children[0]
    assert result.execution_id
    assert orchestrator_result.parent_execution_id == result.execution_id
    assert [event.name for event in orchestrator_result.tool_events] == [
        "delegate_calculator"
    ]
    assert len(orchestrator_result.children) == 1
    specialist_result = orchestrator_result.children[0]
    assert specialist_result.parent_execution_id == orchestrator_result.execution_id
    assert [event.name for event in specialist_result.tool_events] == ["multiply"]
    assert specialist_result.tool_events[0].output["data"] == {"result": 323}
    assert all(node.check_invariants().ok for node in result.walk())

    lineage = result.lineage(name="semantic_delegation")
    execution_steps = [step for step in lineage.steps if step.kind == "execution"]
    assert len(execution_steps) == 3
    assert any(
        step.evidence.get("agent") == "calculator_agent" for step in execution_steps
    )
    assert any(
        step.kind == "tool" and step.source == "multiply" for step in lineage.steps
    )


def test_judge_candidate_view_flattens_complete_lineage_without_duplication() -> None:
    child = RunResult(
        text="Verified product: 323.",
        data={"result": 323},
        engine="python-runtime",
        model="python-runtime",
        mode="eval",
        parent_execution_id="root-execution",
        tool_events=[
            ToolEvent(
                id="multiply-call",
                name="multiply",
                ok=True,
                input={"a": 17, "b": 19},
                output={"result": 323},
            )
        ],
        meta={"agent_name": "calculator_agent", "framework": "native"},
    )
    root = RunResult(
        text="The verified result is 323.",
        data={"answer": "The verified result is 323."},
        engine="openai-runtime",
        model="test-model",
        mode="eval",
        execution_id="root-execution",
        children=[child],
        tool_events=[
            ToolEvent(
                id="delegate-call",
                name="delegate_calculator",
                ok=True,
                input={"a": 17, "b": 19},
                output={"answer": "Verified product: 323."},
            )
        ],
        meta={"agent_name": "orchestrator_agent", "framework": "native"},
    )

    candidate = _judge_candidate_view(root)

    assert "children" not in candidate
    assert "usage" not in candidate
    assert [item["agent"] for item in candidate["executions"]] == [
        "orchestrator_agent",
        "calculator_agent",
    ]
    assert candidate["executions"][0]["tools"][0]["output"] is None
    assert candidate["executions"][1]["tools"][0]["output"] == {"result": 323}


def test_agent_as_tool_avoids_cross_thread_single_lane_deadlock() -> None:
    scheduler = toolkit.scheduler(timeout_s=1.0, max_concurrency=1, max_retries=0)
    runtime = toolkit.runtime(
        provider="python-runtime",
        model="python-runtime",
        scheduler=scheduler,
    )
    system = toolkit.system(runtime=runtime, model="python-runtime")
    math_skill = toolkit.Skill(
        name="cross_thread_math",
        description="Exact multiplication evidence.",
        tools=[multiply],
    )
    specialist = system.agent(
        name="cross_thread_specialist",
        instructions="Execute multiply exactly once.",
        skills=[math_skill],
        input=MultiplyInput,
        contract=toolkit.AgentContract(must_call=["multiply"]),
    )
    delegate = specialist.as_tool(name="delegate_cross_thread")

    def framework_call() -> dict:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(delegate, a=17, b=19).result(timeout=0.5)

    value, scheduler_meta = execute_sync(framework_call, scheduler)
    assert value["data"]["result"] == 323
    assert scheduler_meta["timed_out"] is False
    assert scheduler_meta["attempts"] == 1


def test_openai_agents_receives_pydantic_output_contract_natively() -> None:
    __import__("pytest").importorskip("agents")
    runtime = toolkit.runtime(provider="python-runtime", model="python-runtime")
    system = toolkit.system(runtime=runtime, model="python-runtime")
    agent = system.agent(
        name="structured_agent",
        instructions="Return a structured answer.",
        engine="python-runtime",
        framework="openai-agents",
        output=StructuredAnswer,
    )

    agent.prepare()

    assert agent.native_agent is not None
    assert agent.native_agent.output_type is StructuredAnswer


def test_judge_rubric_defines_contract_aware_fulfillment() -> None:
    rubric = toolkit.JudgeRubric()

    assert "expected contract" in rubric.instructions
    assert "out of scope" in rubric.instructions
    assert "useful clarification" in rubric.instructions
    assert "Do not invent style" in rubric.instructions
    assert "subjective preference" in rubric.instructions
    assert "factual assertions" in rubric.instructions
    assert "must never reduce no_unsupported_claims" in rubric.instructions
    assert "child RunResult" in rubric.instructions
    assert rubric.threshold == 0.80
    assert rubric.deterministic_authority == (
        "request_fulfillment",
        "evidence_correctness",
    )


class Candidate:
    def __init__(self, text: str) -> None:
        self.text = text

    def run(self, input: Any, *, mode: str, config: Any = None) -> toolkit.RunResult:
        return toolkit.RunResult(
            text=self.text,
            data={"result": 323},
            ok=True,
            engine="python-runtime",
            model="python-runtime",
            mode=mode,
            usage={"requests": 1},
            meta={"input": input, "framework": "native"},
        )


class Judge:
    def run(self, input: Any, *, mode: str) -> toolkit.RunResult:
        scores = {name: 0.9 for name in toolkit.JudgeRubric().criteria}
        return toolkit.RunResult(
            text="Semantic verdict recorded.",
            data={
                "score": 0.9,
                "criteria": scores,
                "rationale": "Correct, clear, and supported by evidence.",
            },
            ok=True,
            engine="python-runtime",
            model="python-runtime",
            mode=mode,
            usage={"requests": 1},
            meta={"framework": "native", "input": input},
        )


class DriftedJudge:
    def run(self, input: Any, *, mode: str) -> toolkit.RunResult:
        scores = {name: 0.9 for name in toolkit.JudgeRubric().criteria}
        scores["request_fulfillment"] = 0.1
        scores["evidence_correctness"] = 0.2
        return toolkit.RunResult(
            text="Semantic verdict recorded with contract drift.",
            data={
                "score": sum(scores.values()) / len(scores),
                "criteria": scores,
                "findings": [
                    {
                        "criterion": "request_fulfillment",
                        "evidence": "The model imposed an undeclared requirement.",
                    },
                    {
                        "criterion": "evidence_correctness",
                        "evidence": "The model ignored deterministic Tool evidence.",
                    },
                ],
                "rationale": "Model judge imposed undeclared requirements.",
            },
            ok=True,
            engine="python-runtime",
            model="python-runtime",
            mode=mode,
            usage={"requests": 1},
            meta={"framework": "native", "input": input},
        )


def test_eval_v2_requires_deterministic_validation_and_judge() -> None:
    evaluator = toolkit.Evaluator()
    passing = evaluator.evaluate(
        Candidate("17 multiplied by 19 is 323."),
        [
            {
                "name": "calculation",
                "input": "17 x 19",
                "expected": {"text_contains": "323"},
            }
        ],
        judge=Judge(),
        rubric=toolkit.JudgeRubric(),
        determinism="deterministic",
    )

    assert passing.schema_version == "agentic_systems.eval-report.v2"
    assert passing.ok is True
    assert passing.cases[0].deterministic_validation["ok"] is True
    assert passing.cases[0].judge is not None
    assert passing.cases[0].judge.ok is True
    assert passing.cases[0].candidate_usage == {"requests": 1}
    assert passing.cases[0].judge_usage == {"requests": 1}
    assert passing.cases[0].usage["requests"] == 2

    failing = evaluator.evaluate(
        Candidate("No arithmetic answer."),
        [
            {
                "name": "calculation",
                "input": "17 x 19",
                "expected": {"text_contains": "323"},
            }
        ],
        judge=Judge(),
        rubric=toolkit.JudgeRubric(),
        determinism="deterministic",
    )
    assert failing.ok is False
    assert failing.cases[0].deterministic_validation["ok"] is False
    assert failing.cases[0].judge is not None
    assert failing.cases[0].judge.ok is False


def test_deterministic_contract_authority_is_explicit_and_auditable() -> None:
    report = toolkit.Evaluator().evaluate(
        Candidate("17 multiplied by 19 is 323."),
        [
            {
                "name": "calculation",
                "input": "17 x 19",
                "expected": {"text_contains": "323"},
            }
        ],
        judge=DriftedJudge(),
        rubric=toolkit.JudgeRubric(),
        determinism="deterministic",
    )

    verdict = report.cases[0].judge
    assert verdict is not None
    assert verdict.ok is True
    assert verdict.raw_criteria["request_fulfillment"] == 0.1
    assert verdict.raw_criteria["evidence_correctness"] == 0.2
    assert verdict.criteria["request_fulfillment"] == 1.0
    assert verdict.criteria["evidence_correctness"] == 1.0
    assert verdict.raw_score is not None and verdict.raw_score < verdict.score


class InconsistentJudge:
    def run(self, input: Any, *, mode: str) -> toolkit.RunResult:
        scores = {name: 1.0 for name in toolkit.JudgeRubric().criteria}
        scores["no_unsupported_claims"] = 0.0
        return toolkit.RunResult(
            text="Semantic verdict recorded.",
            data={
                "score": sum(scores.values()) / len(scores),
                "criteria": scores,
                "rationale": "No unsupported claims were found.",
            },
            ok=True,
            engine="vllm-runtime",
            model="test-model",
            mode=mode,
            meta={"framework": "native", "input": input},
        )


def test_judge_rejects_failed_score_without_evidence_backed_finding() -> None:
    report = toolkit.Evaluator().evaluate(
        Candidate("17 multiplied by 19 is 323."),
        [
            {
                "name": "calculation",
                "input": "17 x 19",
                "expected": {"text_contains": "323"},
            }
        ],
        judge=InconsistentJudge(),
        rubric=toolkit.JudgeRubric(),
        determinism="deterministic",
    )

    verdict = report.cases[0].judge
    assert verdict is not None
    assert verdict.ok is False
    assert verdict.consistent is False
    assert verdict.consistency_issues == (
        "failed criterion 'no_unsupported_claims' has no evidence-backed finding",
    )


class ToolCertifiedJudge:
    def __init__(self, *, tool_name: str | None, ok: bool = True) -> None:
        self.tool_name = tool_name
        self.ok = ok

    def run(self, input: Any, *, mode: str) -> toolkit.RunResult:
        scores = {name: 0.9 for name in toolkit.JudgeRubric().criteria}
        events = []
        if self.tool_name is not None:
            events.append(
                ToolEvent(
                    id="judge-certification",
                    name=self.tool_name,
                    ok=True,
                    output={
                        "score": 0.9,
                        "criteria": scores,
                        "rationale": "Certified from evidence.",
                    },
                )
            )
        return RunResult(
            text="Semantic verdict recorded.",
            data={
                "score": 0.9,
                "criteria": scores,
                "rationale": "Certified from evidence.",
            },
            ok=self.ok,
            engine="openai-runtime",
            model="test-model",
            mode=mode,
            tool_events=events,
            meta={"framework": "native", "input": input},
        )


def test_eval_requires_one_successful_judge_certification_tool() -> None:
    rubric = toolkit.JudgeRubric(certification_tool="record_semantic_judgment")
    case = [
        {
            "name": "calculation",
            "input": "17 x 19",
            "expected": {"text_contains": "323"},
        }
    ]

    missing = toolkit.Evaluator().evaluate(
        Candidate("17 multiplied by 19 is 323."),
        case,
        judge=ToolCertifiedJudge(tool_name=None),
        rubric=rubric,
    )
    assert missing.ok is False
    assert missing.cases[0].judge is not None
    assert missing.cases[0].judge.certification_recorded is False

    invalid_run = toolkit.Evaluator().evaluate(
        Candidate("17 multiplied by 19 is 323."),
        case,
        judge=ToolCertifiedJudge(
            tool_name="record_semantic_judgment",
            ok=False,
        ),
        rubric=rubric,
    )
    assert invalid_run.ok is False
    assert invalid_run.cases[0].judge is not None
    assert invalid_run.cases[0].judge.execution_ok is False

    certified = toolkit.Evaluator().evaluate(
        Candidate("17 multiplied by 19 is 323."),
        case,
        judge=ToolCertifiedJudge(tool_name="record_semantic_judgment"),
        rubric=rubric,
    )
    assert certified.ok is True
    assert certified.cases[0].judge is not None
    assert certified.cases[0].judge.certification_recorded is True


def test_eval_accepts_only_explicitly_allowed_tool_paths() -> None:
    report = toolkit.Evaluator().evaluate(
        Candidate("Please choose exact multiplication or text analysis."),
        [
            {
                "name": "out_of_scope",
                "input": "weather",
                "expected": {
                    "text_contains": "choose",
                    "allowed_tool_paths": [[], ["clarify_scope"]],
                },
            }
        ],
        judge=Judge(),
        rubric=toolkit.JudgeRubric(),
        determinism="deterministic",
    )

    assert report.ok is True
    assert report.cases[0].deterministic_validation["ok"] is True


def test_eval_report_v1_payload_remains_loadable() -> None:
    payload = {
        "schema_version": "agentic_systems.eval-report.v1",
        "ok": True,
        "total": 0,
        "passed": 0,
        "failed": 0,
        "pass_rate": 1.0,
        "cases": [],
    }
    report = toolkit.EvalReport.model_validate(payload)
    assert report.schema_version == "agentic_systems.eval-report.v1"
