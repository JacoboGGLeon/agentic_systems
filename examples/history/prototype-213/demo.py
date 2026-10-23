"""One source of application logic for CLI, notebook and tests."""

import agentic_systems as toolkit

from . import Action, Agent, Environment, Eval, Graph, Parallel, Sequence, System


@toolkit.tool
def increment(value: int) -> dict:
    """Increment an integer."""
    return {"value": value + 1}


@toolkit.tool
def double(value: int) -> dict:
    """Double an integer."""
    return {"value": value * 2}


@toolkit.tool
def approve(value: int) -> dict:
    """Record a positive deterministic decision."""
    return {"value": value, "approved": True}


@toolkit.tool
def reject(value: int) -> dict:
    """Record a negative deterministic decision."""
    return {"value": value, "approved": False}


CAPABILITIES = toolkit.skill(
    name="arithmetic", tools=[increment, double, approve, reject]
)
EXPECTED = {"sequential": 8, "parallel": 10, "graph": 8}


def add_branches(outputs):
    return {"value": sum(child["value"] for child in outputs.values())}


def choose_next(data):
    if data["value"] >= 0:
        return "multiply"
    return "END"


def choose_approval(data):
    return "approve" if data["value"] >= 0 else "reject"


def flow_for(kind, first=None, second=None):
    first = first if first is not None else Action("increase", "increment")
    second = second if second is not None else Action("multiply", "double")
    if kind == "sequential":
        return Sequence((first, second))
    if kind == "parallel":
        return Parallel((first, second), join=add_branches)
    if kind == "graph":
        return Graph(
            nodes=(
                ("increase", first),
                ("multiply", second),
            ),
            edges=(
                ("increase", choose_next),
                ("multiply", "END"),
            ),
            start="increase",
        )
    raise ValueError(kind)


def build(owner="Agent", kind="sequential", backend="native"):
    constructor = {"Agent": Agent, "System": System}[owner]
    first, second = None, None
    if owner == "System":
        first = Agent(
            "incrementer", Action("increase", "increment"),
            backend=backend, skills=(CAPABILITIES,),
        )
        second = Agent(
            "doubler", Action("multiply", "double"),
            backend=backend, skills=(CAPABILITIES,),
        )
    return constructor(
        name=f"{owner.lower()}_{kind}",
        flow=flow_for(kind, first, second),
        backend=backend,
        skills=(CAPABILITIES,) if owner == "Agent" else (),
    )


def nested_application():
    worker = build("Agent", "sequential", "langgraph")
    decision = Agent(
        name="decision",
        skills=(CAPABILITIES,),
        flow=Graph(
            nodes=(
                ("classify", Action("observe", lambda value: value)),
                ("approve", Action("approve", "approve")),
                ("reject", Action("reject", "reject")),
            ),
            edges=(
                (
                    "classify",
                    choose_approval,
                ),
                ("approve", "END"),
                ("reject", "END"),
            ),
            start="classify",
        ),
    )
    return System("purchase_fixture", Sequence((worker, decision)), backend="native")


def episode():
    return Environment("two_steps", nested_application(), ({"value": 3}, {"value": -3}))


def evaluation():
    return Eval(
        "fixture_checks",
        nested_application(),
        (
            {
                "name": "positive",
                "input": {"value": 3},
                "expected": {"ok": True, "data": {"value": 8, "approved": True}},
            },
            {
                "name": "negative",
                "input": {"value": -3},
                "expected": {"ok": True, "data": {"value": -4, "approved": False}},
            },
        ),
    )
