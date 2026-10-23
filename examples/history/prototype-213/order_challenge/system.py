"""Single declaration used by the notebook, CLI, tests and generated project."""
from unified_grammar import Action, Agent, Graph, Parallel, Sequence, System
from . import skills


def as_state(data):
    return {"state": data}


def after_intake(data):
    return "checks" if data["validation"]["valid"] else "reject"


def after_policy(data):
    return {"approved": "approve", "review": "review", "rejected": "reject"}[data["policy"]["decision"]]


def merge_checks(branches):
    price, stock = branches["pricing"], branches["inventory"]
    if price["order"] != stock["order"] or price["validation"] != stock["validation"]:
        raise ValueError("Parallel branches disagree on the input order")
    return {**price, "inventory": stock["inventory"]}


def build_system(backend="native"):
    intake = Agent("intake", Sequence((
        Action("normalize", "normalize_order", input=as_state),
        Action("validate", "validate_order", input=as_state),
    )), skills=(skills.intake,), backend=backend)
    pricing = Agent("pricing", Action("price", "price_order", input=as_state),
                    skills=(skills.pricing,), backend=backend)
    inventory = Agent("inventory", Action("stock", "check_inventory", input=as_state),
                      skills=(skills.inventory,), backend=backend)
    policy = Agent("policy", Action("assess", "assess_policy", input=as_state),
                   skills=(skills.policy,), backend=backend)
    approve = Agent("approve", Action("approve", "approve_order", input=as_state),
                    skills=(skills.approval,), backend=backend)
    review = Agent("review", Action("review", "review_order", input=as_state),
                   skills=(skills.review,), backend=backend)
    reject = Agent("reject", Action("reject", "reject_order", input=as_state),
                   skills=(skills.rejection,), backend=backend)
    return System("order_fulfillment", Graph(
        start="intake",
        nodes=(("intake", intake),
               ("checks", Parallel((pricing, inventory), join=merge_checks)),
               ("policy", policy), ("approve", approve),
               ("review", review), ("reject", reject)),
        edges=(("intake", after_intake), ("checks", "policy"),
               ("policy", after_policy), ("approve", "END"),
               ("review", "END"), ("reject", "END")),
    ), backend=backend)
