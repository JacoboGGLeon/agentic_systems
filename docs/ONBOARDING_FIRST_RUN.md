# Your first result · Agentic Systems 2.1.8

Use Python 3.10–3.14. Install the SDK in a clean virtual environment using
[installation instructions](../INSTALL.md). No model account is needed here.

Save this as `first_result.py`:

```python
import agentic_systems as toolkit
assert toolkit.__version__ == "2.1.8"

@toolkit.tool
def increment(value: int) -> dict:
    return {"value": value + 1}

result = increment.run({"value": 3})
assert result.ok and result.data == {"value": 4}
print(result.data)
```

Run `python first_result.py`. Expected output: `{'value': 4}`. You have executed
one named operation and received a RunResult. Inspect `result.errors` if `ok`
is false; a plausible text answer alone does not prove an operation ran.

Choose your next step:

| Need | Next lesson |
|---|---|
| Sequence, branches or decisions | [Your first graph-backed Agent](../tutorials/core/00_start.md) |
| Group tools and instructions | [Tools and Skills](../tutorials/core/01_tools_skills.md) |
| Coordinate capabilities | [System](../tutorials/core/03_system_flows.md) |
| Process records with evolving state | [Environment](../tutorials/core/04_environment.md) |
| Check expected behavior | [Eval](../tutorials/core/05_eval.md) |
| Inspect the SDK or install its authoring skill | [CLI](CLI.md) |
| Let a model select actions | [Actor contracts](ACTOR_CONTRACTS.md), then a provider tutorial |

State carries the current work. Context supplies domain information. Memory
retains bounded episodes in this process. Add them when your task needs them;
you do not need all library concepts for every program.
