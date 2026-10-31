import pydantic
from typing import Any
from dataclasses import replace
import agentic_systems as toolkit


class EpisodeState(pydantic.BaseModel):
    amount: int | None = None
    previous: int | None = None
    total: int | None = None


class EpisodeOutput(pydantic.BaseModel):
    total: int


def build_episode():
    graph = toolkit.Graph(EpisodeState, output_schema=EpisodeOutput)
    def sum_step(state):
        return {"total": state.previous + state.amount}
    graph.add_node("sum", sum_step)
    graph.add_edge(toolkit.START, "sum")
    graph.add_edge("sum", toolkit.END)
    return toolkit.Environment(
        "ledger",
        graph=graph,
        records=({"amount": 2}, {"amount": 3}, {"amount": 100}),
        state={"total": 0},
        memory=toolkit.Memory(capacity=3),
        observe=lambda row, state: {
            "amount": row["amount"],
            "previous": state["total"],
        },
        update=lambda state, row, result: result.data,
        stop=lambda state, result: state["total"] >= 5,
    )


class State(pydantic.BaseModel):
    value: Any


class JudgeState(pydantic.BaseModel):
    input: Any
    expected: Any | None = None
    result: Any | None = None
    rubric: Any | None = None
    criteria: Any | None = None
    findings: Any | None = None
    rationale: Any | None = None


def run():

    class Output1(pydantic.BaseModel):
        value: Any

    graph_1 = toolkit.Graph(State, output_schema=Output1)
    def increment_step(d):
        return {"value": d.value + 1}
    graph_1.add_node("increment", increment_step)
    graph_1.add_edge(toolkit.START, "increment")
    graph_1.add_edge("increment", toolkit.END)
    target = toolkit.Agent("calculator", graph=graph_1)

    class Output2(pydantic.BaseModel):
        criteria: Any
        findings: Any
        rationale: Any

    graph_2 = toolkit.Graph(JudgeState, output_schema=Output2)
    def score_step(payload):
        return {
                "criteria": {"correctness": 1.0},
                "findings": [],
                "rationale": "Fixture: deterministic oracle confirmed the supplied case.",
            }
    graph_2.add_node(
        "score",
        score_step,
    )
    graph_2.add_edge(toolkit.START, "score")
    graph_2.add_edge("score", toolkit.END)
    judge = toolkit.Agent("fixture_judge", graph=graph_2)
    evaluation = toolkit.Eval(
        "contract",
        target,
        ({"input": {"value": 3}, "expected": {"data": {"value": 4}}},),
        checks=(lambda result, case: {"ok": result.data["value"] > 0, "issues": []},),
        judge=judge,
        rubric={"criteria": ["correctness"], "threshold": 0.9},
    )
    positive = evaluation.run()
    negative = replace(
        evaluation,
        cases=({"input": {"value": 3}, "expected": {"data": {"value": 999}}},),
    ).run()
    episode = toolkit.Eval(
        "episode_reward",
        build_episode(),
        ({"input": {}, "expected": {"ok": True}},),
        checks=(
            lambda result, case: {
                "ok": result.data["summary"]["state"]["total"] == 5,
                "issues": [],
                "metrics": {"reward": result.data["summary"]["state"]["total"]},
            },
        ),
    ).run()
    assert positive.ok and (not negative.ok) and episode.ok
    assert episode.data["cases"][0]["checks"][1]["metrics"]["reward"] == 5
    return {
        "input": {"value": 3},
        "process": "Exact expected + check + explicit fixture judge; separate episode check",
        "output": positive.to_dict(),
        "negative": negative.to_dict(),
        "episode": episode.to_dict(),
        "judge_validation": "fixture-only; no semantic model inference",
    }
