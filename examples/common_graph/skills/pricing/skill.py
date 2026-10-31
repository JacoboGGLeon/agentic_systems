import agentic_systems as toolkit
from .tools import quote


def build_skill():
    return toolkit.skill(
        name="pricing",
        tools=(quote,),
        version="1.0.0",
        instructions="Use the currency and tax policy supplied in Context.",
    )
