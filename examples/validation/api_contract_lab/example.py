"""Current API adaptation; see README for its measured scope."""
import agentic_systems as toolkit

from inspect import signature


def run():
    worker = toolkit.Agent("identity", toolkit.Action("identity", lambda data: data))
    direct = worker.run({"value": 3})
    prepared = worker.compile().run({"value": 3})
    assert direct.ok and prepared.ok and direct.data == prepared.data
    return {"version": toolkit.__version__, "exports": list(toolkit.__all__),
            "Agent": str(signature(toolkit.Agent)), "System": str(signature(toolkit.System)), "output": direct.data}
