import asyncio
import agentic_systems as toolkit


def run():
    unit = toolkit.Agent("calculator", toolkit.Sequence((
        toolkit.Action("increment", lambda d: {"value": d["value"] + 1}),
        toolkit.Action("double", lambda d: {"value": d["value"] * 2}),
    )))
    prepared = unit.compile()
    direct = unit.run({"value": 3}, limits=toolkit.Limits(max_actions=2, timeout_s=10))
    asynchronous = asyncio.run(prepared.arun({"value": 3}))
    limited = unit.run({"value": 3}, limits=toolkit.Limits(max_actions=1))
    assert direct.ok and direct.data == asynchronous.data == {"value": 8}
    assert not limited.ok
    return {"input": {"value": 3}, "process": prepared.inspect(), "output": direct.to_dict(), "limit_failure": limited.to_dict()}
