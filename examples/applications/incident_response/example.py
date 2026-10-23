"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def triage(input: dict) -> dict:
    failures = sum(event["status"] == "error" for event in input["events"])
    return {"failures": failures, "severity": "high" if failures >= 2 else "low",
            "action": "isolate and investigate" if failures >= 2 else "monitor"}


capability = toolkit.skill(name="triage", tools=(triage,))
worker = toolkit.Agent("worker", toolkit.Action("triage", "triage"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'events': [{'status': 'error'}, {'status': 'ok'}, {'status': 'error'}]}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'failures': 2, 'severity': 'high', 'action': 'isolate and investigate'}, result.to_dict()
    return result
