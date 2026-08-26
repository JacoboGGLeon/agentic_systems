from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

import agentic_systems as toolkit


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
    orchestrator = system.agent(
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
    assert rubric.threshold == 0.80


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
