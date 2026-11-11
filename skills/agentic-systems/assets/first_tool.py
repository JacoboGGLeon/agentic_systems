"""First result: one deterministic operation, no model or credentials."""
import agentic_systems as toolkit
assert toolkit.__version__ == "2.1.8"

@toolkit.tool
def increment(value: int) -> dict:
    return {"value": value + 1}

result = increment.run({"value": 3})
assert result.ok and result.data == {"value": 4}
assert result.check_invariants().ok
print(result.data)
