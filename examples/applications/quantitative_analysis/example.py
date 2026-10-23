"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def profit(input: dict) -> dict:
    from decimal import Decimal
    revenue = sum(Decimal(row["revenue"]) for row in input["rows"])
    cost = sum(Decimal(row["cost"]) for row in input["rows"])
    return {"revenue": str(revenue), "cost": str(cost), "profit": str(revenue - cost)}


capability = toolkit.skill(name="profit", tools=(profit,))
worker = toolkit.Agent("worker", toolkit.Action("profit", "profit"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'rows': [{'revenue': '100.10', 'cost': '60.05'}, {'revenue': '20.20', 'cost': '10.00'}]}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'revenue': '120.30', 'cost': '70.05', 'profit': '50.25'}, result.to_dict()
    return result
