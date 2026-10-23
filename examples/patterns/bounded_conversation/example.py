"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

@toolkit.tool
def bound_history(messages: list[str]) -> dict:
    return {"history": [message[:80] for message in messages[-3:]]}


app = toolkit.Agent("memory", toolkit.Action("bound", bound_history))


def run():
    result = app.run({"messages": ["old", "first", "second", "current"]})
    assert result.ok and result.data == {"history": ["first", "second", "current"]}
    return result
