from dataclasses import replace
import agentic_systems as toolkit
from episode_memory.example import build as build_episode


def run():
    target = toolkit.Agent("calculator", toolkit.Action("increment", lambda d: {"value": d["value"] + 1}))
    # A deterministic fixture tests the judge protocol; it is not a language-model judge.
    judge = toolkit.Agent("fixture_judge", toolkit.Action("score", lambda payload: {
        "criteria": {"correctness": 1.0}, "findings": [], "rationale": "Fixture: deterministic oracle confirmed the supplied case."}))
    evaluation = toolkit.Eval("contract", target, ({"input": {"value": 3}, "expected": {"data": {"value": 4}}},),
        checks=(lambda result, case: {"ok": result.data["value"] > 0, "issues": []},),
        judge=judge, rubric={"criteria": ["correctness"], "threshold": 0.9})
    positive = evaluation.run()
    negative = replace(evaluation, cases=({"input": {"value": 3}, "expected": {"data": {"value": 999}}},)).run()
    episode = toolkit.Eval("episode_reward", build_episode(), ({"input": {}, "expected": {"ok": True}},),
        checks=(lambda result, case: {"ok": result.data["summary"]["memory"]["total"] == 5, "issues": [],
                                     "metrics": {"reward": result.data["summary"]["memory"]["total"]}},)).run()
    assert positive.ok and not negative.ok and episode.ok
    assert episode.data["cases"][0]["checks"][1]["metrics"]["reward"] == 5
    return {"input": {"value": 3}, "process": "Exact expected + check + explicit fixture judge; separate episode check", "output": positive.to_dict(),
            "negative": negative.to_dict(), "episode": episode.to_dict(), "judge_validation": "fixture-only; no semantic model inference"}
