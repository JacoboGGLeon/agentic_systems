"""Input -> typed Tool -> JSON output, including a controlled invalid input."""

import pydantic
import asyncio
import agentic_systems as toolkit


class Quantity(pydantic.BaseModel):
    value: pydantic.StrictInt


@toolkit.tool(
    input_schema=Quantity,
    output_schema=Quantity,
    metadata={"example": "tool_contracts"},
)
def increment(data: Quantity) -> Quantity:
    """Increment an explicitly typed integer."""
    return Quantity(value=data.value + 1)


def run():
    result = increment.run({"value": 3})
    asynchronous = asyncio.run(increment.arun({"value": 3}))
    negative = increment.run({"value": "invalid"})
    assert result.ok and result.data == asynchronous.data == {"value": 4}
    assert not negative.ok and negative.tool_events[0].error
    return {
        "input": {"value": 3},
        "process": increment.inspect(),
        "output": result.to_dict(),
        "negative_detected": not negative.ok,
    }
