"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

app = toolkit.Agent("candidate", toolkit.Action("exact", lambda data: {"answer": data["answer"]}))
fixture_judge = toolkit.Agent("judge_fixture", toolkit.Action("score", lambda data: {
    "criteria": {"correctness": 1.0}, "findings": [], "rationale": "Intentionally optimistic fixture"}))
evaluation = toolkit.Eval("negative_control", app, cases=(
    {"input": {"answer": "WRONG"}, "expected": {"data": {"answer": "VALID"}}},
), judge=fixture_judge, rubric={"criteria": ["correctness"], "threshold": 0.9})


def run():
    result = evaluation.run()
    assert not result.ok
    return {"evaluation": result.to_dict(), "scope": "optimistic judge cannot overrule a failed exact expectation; fixture, not live judge"}
