"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def exact_total(quantity: int, unit_price: int) -> dict:
    return {"total": quantity * unit_price}


arithmetic = toolkit.Agent("evidence", toolkit.Action("total", exact_total))
compose = toolkit.Agent("saved_verse", toolkit.Action("format", lambda data: {
    "total": data["total"], "poem": f"Evidence counts {data['total']}\nThe amount stays exact\nThis verse is a supplied fixture"}))
app = toolkit.System("two_phases", toolkit.Sequence((arithmetic, compose)))


def run():
    result = app.run({"quantity": 3, "unit_price": 116})
    assert result.ok and result.data["total"] == 348 and len(result.data["poem"].splitlines()) == 3
    assert any(event.name == "exact_total" for node in result.walk() for event in node.tool_events)
    return {"result": result.to_dict(), "scope": "exact evidence then formatting fixture; no language-model generation"}
