import agentic_systems as toolkit


def run():
    rows = []
    for backend in ("native", "langgraph"):
        for owner in (toolkit.Agent, toolkit.System):
            first = toolkit.Action("increment", lambda d: {"value": d["value"] + 1})
            second = toolkit.Action("double", lambda d: {"value": d["value"] * 2})
            if owner is toolkit.System:
                first, second = toolkit.Agent("incrementer", first), toolkit.Agent("doubler", second)
            flows = {
                "sequence": (toolkit.Sequence((first, second)), 8),
                "parallel": (toolkit.Parallel((first, second), join=lambda branches: {"value": sum(d["value"] for d in branches.values())}), 10),
                "decision": (toolkit.Graph((("first", first), ("second", second)),
                    (("first", lambda d: "second" if d["value"] >= 0 else "END"), ("second", "END")), "first"), 8),
            }
            for kind, (flow, expected) in flows.items():
                unit = owner(kind, flow, backend=backend)
                result = unit.run({"value": 3})
                assert result.ok and result.data == {"value": expected}
                assert unit.compile().run({"value": 3}).data == result.data
                rows.append({"owner": owner.__name__, "backend": backend, "flow": kind, "output": result.data})
    return {"input": {"value": 3}, "process": "Agent/System × sequence/parallel/decision × native/LangGraph", "output": rows}
