"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def refund_policy(input: dict) -> dict:
    approved = input["amount"] <= 500 and input["currency"] == "MXN" and input["account_days"] >= 7
    return {"order_id": input["order_id"], "decision": "approved" if approved else "manual_review", "amount": input["amount"]}


capability = toolkit.skill(name="refund_policy", tools=(refund_policy,))
worker = toolkit.Agent("worker", toolkit.Action("refund_policy", "refund_policy"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'order_id': 'A17', 'amount': 280, 'currency': 'MXN', 'account_days': 90}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'order_id': 'A17', 'decision': 'approved', 'amount': 280}, result.to_dict()
    return result
