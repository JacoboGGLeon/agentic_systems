"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def review_claims(input: dict) -> dict:
    findings = []
    for claim in input["claims"]:
        if claim["source"] not in input["sources"]:
            findings.append({"claim": claim["id"], "issue": "missing source"})
        if claim.get("causal") and not claim.get("causal_evidence"):
            findings.append({"claim": claim["id"], "issue": "unsupported causality"})
    return {"accepted": not findings, "findings": findings}


capability = toolkit.skill(name="review_claims", tools=(review_claims,))
worker = toolkit.Agent("worker", toolkit.Action("review_claims", "review_claims"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'claims': [{'id': 'C1', 'source': 'missing', 'causal': True}], 'sources': ['report']}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'accepted': False, 'findings': [{'claim': 'C1', 'issue': 'missing source'}, {'claim': 'C1', 'issue': 'unsupported causality'}]}, result.to_dict()
    return result
