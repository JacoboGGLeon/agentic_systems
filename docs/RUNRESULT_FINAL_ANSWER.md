# RunResult And Final Answer

`RunResult` separates execution evidence from the user-facing answer.

## Contract

```text
RunResult.final  answer shaped for the user request
RunResult.data   reusable evidence and payload
RunResult.text   textual fallback
```

The envelope also carries:

```text
tool_events
usage
validation
errors
trace
metadata
```

## Example

```python
import agentic_systems as toolkit

schema = toolkit.output_schema(["procedure", "final_result"])

result = toolkit.RunResult(
    text="The final result is 5.",
    data={"steps": ["2 + 3 = 5"], "value": 5},
    final=toolkit.final_answer(
        {"procedure": ["2 + 3 = 5"], "final_result": 5},
        schema=schema,
    ),
    engine="python-runtime",
    model="local-python",
    mode="eval",
)

toolkit.human_result(result)
```

## Normalization

```python
toolkit.normalize_output({"a": 1})      # {"a": 1}
toolkit.normalize_output([{"a": 1}])    # {"rows": [{"a": 1}]}
toolkit.normalize_output([1, 2])        # {"items": [1, 2]}
toolkit.normalize_output("hello")       # {"value": "hello"}
toolkit.normalize_output(None)          # {}
```

`final_answer(text="hello")` uses `{"text": "hello"}` because it represents a
natural-language fallback. `normalize_output("hello")` uses `{"value": "hello"}`
because it normalizes a scalar payload.

## Rendering

`toolkit.human_result(...)` renders the final answer first, then runtime, actions,
lineage and validation when present. Rendering is not the source of truth; the
source of truth is the `RunResult` object.

```python
toolkit.human_result(result, pretty=False, render_mode="compact")
toolkit.human_result(result, pretty=False, render_mode="debug")
toolkit.human_result(result, pretty=False, render_mode="lineage")
```

Use this contract for tools, agents, graphs, environments and evals.
