"""Six canonical forms, one Skill, an episode and deterministic evaluation."""
import agentic_systems as toolkit


@toolkit.tool
def increment(value: int) -> dict:
    return {"value": value + 1}


@toolkit.tool
def double(value: int) -> dict:
    return {"value": value * 2}


arithmetic = toolkit.skill(name="arithmetic", tools=(increment, double),
                           instructions="Use exact arithmetic and retain the result.")


def combine(branches):
    return {"value": sum(branch["value"] for branch in branches.values())}


def choose_next(data):
    return "double" if data["value"] >= 0 else "END"


def build(backend="native"):
    agent_sequence = toolkit.Agent("agent_sequence", toolkit.Sequence((
        toolkit.Action("increment", "increment"),
        toolkit.Action("double", "double"),
    )), skills=(arithmetic,), backend=backend)

    agent_parallel = toolkit.Agent("agent_parallel", toolkit.Parallel((
        toolkit.Action("increment", "increment"),
        toolkit.Action("double", "double"),
    ), join=combine), skills=(arithmetic,), backend=backend)

    agent_decision = toolkit.Agent("agent_decision", toolkit.Graph(
        nodes=(("increment", toolkit.Action("increment", "increment")),
               ("double", toolkit.Action("double", "double"))),
        edges=(("increment", choose_next), ("double", "END")),
        start="increment",
    ), skills=(arithmetic,), backend=backend)

    increaser = toolkit.Agent("increaser", toolkit.Action("increment", "increment"), skills=(arithmetic,))
    doubler = toolkit.Agent("doubler", toolkit.Action("double", "double"), skills=(arithmetic,))

    system_sequence = toolkit.System("system_sequence", toolkit.Sequence((increaser, doubler)), backend=backend)
    system_parallel = toolkit.System("system_parallel", toolkit.Parallel((increaser, doubler), join=combine), backend=backend)
    system_decision = toolkit.System("system_decision", toolkit.Graph(
        nodes=(("increment", increaser), ("double", doubler)),
        edges=(("increment", choose_next), ("double", "END")), start="increment",
    ), backend=backend)
    return (agent_sequence, agent_parallel, agent_decision,
            system_sequence, system_parallel, system_decision)


def run():
    rows = []
    for backend in ("native", "langgraph"):
        units = build(backend)
        for unit, expected in zip(units, (8, 10, 8, 8, 10, 8)):
            direct = unit.run({"value": 3})
            compiled = unit.compile().run({"value": 3})
            assert direct.ok and compiled.ok and direct.data == compiled.data == {"value": expected}
            evaluation = toolkit.Eval("exact", unit, cases=(
                {"input": {"value": 3}, "expected": {"data": {"value": expected}}},
            )).run()
            assert evaluation.ok
            rows.append({"backend": backend, "unit": unit.name, "input": {"value": 3},
                         "output": direct.data, "eval_ok": evaluation.ok})
        application = units[-1]
        episode = toolkit.Environment("requests", application,
            records=({"value": 3}, {"value": -3}), memory={"processed": 0},
            update=lambda memory, record, result: {"processed": memory["processed"] + 1})
        episode_result = episode.run()
        assert episode_result.ok and episode_result.data["outputs"] == [{"value": 8}, {"value": -2}]
        checked = toolkit.Eval("episode", episode, cases=({"input": {}, "expected": {"ok": True}},),
            checks=(lambda result, case: {"ok": result.data["outputs"] == [{"value": 8}, {"value": -2}],
                                          "issues": []},)).run()
        assert checked.ok
        rows.append({"backend": backend, "unit": "Environment + Eval", "input": [{"value": 3}, {"value": -3}],
                     "output": episode_result.data["outputs"], "memory": episode_result.data["summary"]["memory"],
                     "eval_ok": checked.ok})
    return {"input": {"value": 3}, "process": "Tools -> Skill -> Agent/System -> Environment -> Eval",
            "rows": rows, "inference_requests": 0}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), ensure_ascii=False, indent=2))
