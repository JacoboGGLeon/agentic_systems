"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

sample = 'Three items cost 300\nTax adds 48\nVerified total 348'
app = toolkit.Agent("saved_candidate", toolkit.Action("read", lambda data: {"poem": data["poem"]}))
evaluation = toolkit.Eval("poem_contract", app, cases=(
    {"input": {"poem": sample}, "expected": {"ok": True}},
    {"input": {"poem": 'The moon computes forever'}, "expected": {"ok": True}},
), checks=(lambda result, case: {"ok": len(result.data["poem"].splitlines()) == 3 and "348" in result.data["poem"], "issues": []},))


def run():
    result = evaluation.run()
    assert not result.ok and result.data["cases"][0]["ok"] and not result.data["cases"][1]["ok"]
    return {"evaluation": result.to_dict(), "scope": "saved creative candidates; no generation or semantic judge inferred"}
