"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def evidence_accountability(input: dict) -> dict:
    claims = input["claims"]
    return {"unowned": [claim["id"] for claim in claims if not claim["owner"]],
            "unsupported": [claim["id"] for claim in claims if not claim["evidence"]], "data": "public synthetic fixture"}


capability = toolkit.skill(name="evidence_accountability", tools=(evidence_accountability,))
worker = toolkit.Agent("worker", toolkit.Action("evidence_accountability", "evidence_accountability"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'claims': [{'id': 'C1', 'owner': 'team-A', 'evidence': ['E1']}, {'id': 'C2', 'owner': '', 'evidence': []}]}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'unowned': ['C2'], 'unsupported': ['C2'], 'data': 'public synthetic fixture'}, result.to_dict()
    return result
