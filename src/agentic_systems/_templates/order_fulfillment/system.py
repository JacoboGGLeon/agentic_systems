"""Single declaration used by the notebook, CLI, tests and generated project."""
import agentic_systems as toolkit
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
    intake = toolkit.Agent("intake", toolkit.Sequence((
        toolkit.Action("normalize", "normalize_order", input=as_state),
        toolkit.Action("validate", "validate_order", input=as_state),
    )), skills=(skills.intake,), backend=backend)
    pricing = toolkit.Agent("pricing", toolkit.Action("price", "price_order", input=as_state),
                    skills=(skills.pricing,), backend=backend)
    inventory = toolkit.Agent("inventory", toolkit.Action("stock", "check_inventory", input=as_state),
                      skills=(skills.inventory,), backend=backend)
    policy = toolkit.Agent("policy", toolkit.Action("assess", "assess_policy", input=as_state),
                   skills=(skills.policy,), backend=backend)
    approve = toolkit.Agent("approve", toolkit.Action("approve", "approve_order", input=as_state),
                    skills=(skills.approval,), backend=backend)
    review = toolkit.Agent("review", toolkit.Action("review", "review_order", input=as_state),
                   skills=(skills.review,), backend=backend)
    reject = toolkit.Agent("reject", toolkit.Action("reject", "reject_order", input=as_state),
                   skills=(skills.rejection,), backend=backend)
    return toolkit.System("order_fulfillment", toolkit.Graph(
        start="intake",
        nodes=(("intake", intake),
               ("checks", toolkit.Parallel((pricing, inventory), join=merge_checks)),
               ("policy", policy), ("approve", approve),
               ("review", review), ("reject", reject)),
        edges=(("intake", after_intake), ("checks", "policy"),
               ("policy", after_policy), ("approve", "END"),
               ("review", "END"), ("reject", "END")),
    ), backend=backend)
