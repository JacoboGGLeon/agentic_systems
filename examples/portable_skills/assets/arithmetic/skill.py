import agentic_systems as toolkit


@toolkit.tool
def increment(value: int) -> dict:
    """Increment an integer using a sibling resource."""
    from .helper import compute
    return compute(value)


def build_skill():
    return toolkit.skill(name="arithmetic", tools=[increment], instructions="Use exact integer arithmetic.",
                         description="Portable local arithmetic", version="1.0.0", metadata={"synthetic": True})
