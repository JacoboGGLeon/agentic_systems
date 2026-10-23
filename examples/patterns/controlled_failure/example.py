"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def unavailable(item: str) -> dict:
    raise LookupError("Inventory unavailable for " + item)


app = toolkit.System("failure", toolkit.Sequence((toolkit.Agent("inventory", toolkit.Action("lookup", unavailable)),)))


def run():
    result = app.run({"item": "A17"})
    assert not result.ok and result.errors and any(node.tool_events for node in result.walk())
    assert result.check_invariants().ok
    return result
