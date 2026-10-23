"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

app = toolkit.Agent("saved_answer", toolkit.Action("read", lambda data: data))
evaluation = toolkit.Eval("literal_gate", app, cases=tuple(
    {"input": {"answer": answer}, "expected": {"data": {"answer": "VALID"}}}
    for answer in ("VALID", "VALID.", "invalid", "")
))


def run():
    result = evaluation.run()
    decisions = [case["ok"] for case in result.data["cases"]]
    assert decisions == [True, False, False, False]
    return {"decisions": decisions, "scope": "literal saved-answer gate; no claim of natural-language entailment", "evaluation": result.to_dict()}
