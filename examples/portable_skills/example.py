from pathlib import Path
import agentic_systems as toolkit


def run():
    capability = toolkit.load_skill(Path(__file__).parent / "assets/arithmetic")
    worker = toolkit.Agent("portable", toolkit.Action("increment", "increment"), skills=(capability,))
    result = worker.run({"value": 3})
    assert result.ok and result.data == {"value": 4}
    return {"input": {"value": 3}, "process": capability.inspect(), "output": result.to_dict()}
