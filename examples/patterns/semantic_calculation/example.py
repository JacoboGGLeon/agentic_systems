"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def calculate_invoice(input: dict) -> dict:
    total = sum(row["quantity"] * row["unit_price"] for row in input["items"])
    return {"subtotal": total, "tax": total * 16 // 100, "total": total * 116 // 100}


capability = toolkit.skill(name="calculate_invoice", tools=(calculate_invoice,))
worker = toolkit.Agent("worker", toolkit.Action("calculate_invoice", "calculate_invoice"), skills=(capability,))
app = toolkit.System("application", toolkit.Sequence((worker,)))
sample = {'items': [{'quantity': 3, 'unit_price': 100}]}


def run():
    result = app.run({'input': sample})
    assert result.ok and result.data == {'subtotal': 300, 'tax': 48, 'total': 348}, result.to_dict()
    return result
