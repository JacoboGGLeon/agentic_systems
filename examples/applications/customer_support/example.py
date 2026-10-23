"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def classify_ticket(input: dict) -> dict:
    text = input["message"].lower()
    category = "refund" if "refund" in text else "shipping" if "delivery" in text else "general"
    return {"category": category, "owner": {"refund": "billing", "shipping": "logistics", "general": "support"}[category]}


capability = toolkit.skill(name="classify_ticket", tools=(classify_ticket,))
worker = toolkit.Agent("worker", toolkit.Action("classify_ticket", "classify_ticket"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'message': 'Please refund order A17'}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'category': 'refund', 'owner': 'billing'}, result.to_dict()
    return result
