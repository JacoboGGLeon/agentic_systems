"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def scope(input: dict) -> dict:
    supported = {"sum", "count"}
    return {"accepted": input["operation"] in supported, "supported": sorted(supported),
            "reason": "outside declared capabilities" if input["operation"] not in supported else "declared operation"}


capability = toolkit.skill(name="scope", tools=(scope,))
worker = toolkit.Agent("worker", toolkit.Action("scope", "scope"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'operation': 'transfer_money'}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'accepted': False, 'supported': ['count', 'sum'], 'reason': 'outside declared capabilities'}, result.to_dict()
    return result
