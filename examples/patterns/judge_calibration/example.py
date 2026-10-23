"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

app = toolkit.Agent("candidate", toolkit.Action("answer", lambda data: data))
judge = toolkit.Agent("optimistic_fixture", toolkit.Action("score", lambda data: {
    "criteria": {"correctness": 1.0}, "findings": [], "rationale": "Calibration fixture always approves"}))
evaluation = toolkit.Eval("calibration", app, cases=(
    {"input": {"answer": "VALID"}, "expected": {"data": {"answer": "VALID"}}},
    {"input": {"answer": "WRONG"}, "expected": {"data": {"answer": "VALID"}}},
), judge=judge, rubric={"criteria": ["correctness"], "threshold": 0.9})


def run():
    result = evaluation.run()
    decisions = [case["ok"] for case in result.data["cases"]]
    assert decisions == [True, False]
    return {"calibration": decisions, "false_approvals": 0, "scope": "fixture protocol; no empirical model judge calibration", "evaluation": result.to_dict()}
