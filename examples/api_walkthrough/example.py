"""Shared declarations used by the user notebook and final validation."""
import agentic_systems as toolkit

@toolkit.tool
def increment(value: int) -> dict:
    return {"value": value + 1}

@toolkit.tool
def double(value: int) -> dict:
    return {"value": value * 2}

arithmetic = toolkit.skill(name="arithmetic", tools=(increment, double), instructions="Usa aritmética exacta.")
increase = toolkit.Action("increase", "increment")
multiply = toolkit.Action("multiply", "double")

def combine(branches):
    return {"value": sum(branch["value"] for branch in branches.values())}

def choose_next(data):
    return "multiply" if data["value"] >= 0 else "END"


def grammar_units(backend="native"):
    agent_sequence = toolkit.Agent("agent_sequence", toolkit.Sequence((increase, multiply)), skills=(arithmetic,), backend=backend)
    agent_parallel = toolkit.Agent("agent_parallel", toolkit.Parallel((increase, multiply), join=combine), skills=(arithmetic,), backend=backend)
    agent_decision = toolkit.Agent("agent_decision", toolkit.Graph(
        nodes=(("increase", increase), ("multiply", multiply)),
        edges=(("increase", choose_next), ("multiply", "END")), start="increase",
    ), skills=(arithmetic,), backend=backend)

    increaser = toolkit.Agent("increaser", increase, skills=(arithmetic,))
    doubler = toolkit.Agent("doubler", multiply, skills=(arithmetic,))
    system_sequence = toolkit.System("system_sequence", toolkit.Sequence((increaser, doubler)), backend=backend)
    system_parallel = toolkit.System("system_parallel", toolkit.Parallel((increaser, doubler), join=combine), backend=backend)
    system_decision = toolkit.System("system_decision", toolkit.Graph(
        nodes=(("increase", increaser), ("multiply", doubler)),
        edges=(("increase", choose_next), ("multiply", "END")), start="increase",
    ), backend=backend)
    return (agent_sequence, agent_parallel, agent_decision, system_sequence, system_parallel, system_decision)


@toolkit.tool
def quote(units: int, unit_price: int) -> dict:
    if units <= 0 or unit_price < 0:
        raise ValueError("Cantidad o precio inválidos")
    return {"total": units * unit_price}

@toolkit.tool
def approve(total: int) -> dict:
    return {"total": total, "status": "approved"}

@toolkit.tool
def review(total: int) -> dict:
    return {"total": total, "status": "manual_review"}

pricing = toolkit.skill(name="pricing", tools=(quote,))
decisions = toolkit.skill(name="decisions", tools=(approve, review))

def route_order(data):
    return "approve" if data["total"] <= 1000 else "review"

records = ({"units": 2, "unit_price": 100}, {"units": 3, "unit_price": 500})
expected = [{"total": 200, "status": "approved"}, {"total": 1500, "status": "manual_review"}]


def build_orders(backend="native", *, runtime=None, framework=None):
    quoter = toolkit.Agent("quoter", toolkit.Action("quote", "quote"), skills=(pricing,))
    approver = toolkit.Agent("approver", toolkit.Action("approve", "approve"), skills=(decisions,))
    reviewer = toolkit.Agent("reviewer", toolkit.Action("review", "review"), skills=(decisions,))
    if runtime is not None:
        approver = runtime_step("approver", approve, runtime, framework)
        reviewer = runtime_step("reviewer", review, runtime, framework)
    return toolkit.System("orders", toolkit.Graph(
        nodes=(("quote", quoter), ("approve", approver), ("review", reviewer)),
        edges=(("quote", route_order), ("approve", "END"), ("review", "END")), start="quote",
    ), backend=backend)

def build_day(backend="native", *, runtime=None, framework=None):
    return toolkit.Environment("day", build_orders(backend, runtime=runtime, framework=framework),
        records=records, memory={"approved": 0},
        update=lambda memory, record, result: {
            "approved": memory["approved"] + int(result.data["status"] == "approved")
        })

def check_day(result, case):
    valid = result.data["outputs"] == expected and result.data["summary"]["memory"] == {"approved": 1}
    return {"ok": valid, "issues": [] if valid else ["Resultados o memoria incorrectos"],
            "metrics": {"approved": result.data["summary"]["memory"]["approved"]}}

def evaluate_day(unit):
    return toolkit.Eval("orders_acceptance", unit,
        cases=({"input": {}, "expected": {"ok": True}},), checks=(check_day,))


def observed_tool_data(output, tool_name):
    if isinstance(output, dict) and set(output) == {"data"}:
        return output["data"]
    if (isinstance(output, dict) and {"kind", "tool_name", "ok", "data"}.issubset(output)
            and output["kind"] == "object" and output["tool_name"] == tool_name and output["ok"] is True):
        return output["data"]
    return output

def runtime_step(name, operation, runtime, framework):
    # Pass business data from observed Tool evidence; preserve the original actor.
    from dataclasses import replace
    import json
    actor = toolkit.Agent(name, runtime=runtime, framework=framework,
        skills=(toolkit.skill(name=name + "_capability", tools=(operation,)),),
        instructions="Call " + operation.name + " exactly once. Copy the supplied total unchanged. Only the Tool determines the status.",
        contract={"tool_expectation": {"all_of": [operation.name]}, "completion": "when_required_tools_satisfied"},
        policy={"repair": False})
    def execute(data):
        request = ({"tool": operation.name, "input": data} if runtime.provider == "python-runtime" else
                   "Call exactly " + operation.name + " with these unchanged arguments: " + json.dumps(data))
        result = actor.run(request, limits=toolkit.Limits(timeout_s=180))
        if not result.ok:
            return result
        events = [event for node in result.walk() for event in node.tool_events if event.name == operation.name and event.ok]
        if len(events) != 1 or events[0].input != data:
            return replace(result, ok=False, errors=(*result.errors, {"code": "business_boundary_rejected", "message": "Expected one Tool invocation with unchanged business input"}))
        output = observed_tool_data(events[0].output, operation.name)
        expected_status = "approved" if operation.name == "approve" else "manual_review"
        if output != {"total": data["total"], "status": expected_status}:
            return replace(result, ok=False, errors=(*result.errors, {"code": "business_boundary_rejected", "message": "Observed Tool evidence violates the business contract", "observed": output}))
        return replace(result, data=output)
    return toolkit.Agent(name + "_boundary", toolkit.Action(name, execute))


def run():
    rows = []
    for backend in ("native", "langgraph"):
        for unit, value in zip(grammar_units(backend), (8, 10, 8, 8, 10, 8)):
            direct = unit.run({"value": 3})
            assert direct.ok and direct.data == unit.compile().run({"value": 3}).data == {"value": value}
            rows.append({"backend": backend, "unit": unit.name, "output": direct.data})
        episode = build_day(backend)
        result = episode.run()
        evaluation = evaluate_day(episode).run()
        assert result.ok and result.data["outputs"] == expected and evaluation.ok
    return {"rows": rows, "output": result.data["outputs"], "memory": result.data["summary"]["memory"], "inference_requests": 0}
