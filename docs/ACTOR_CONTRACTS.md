# Actor contracts · Agentic Systems 2.1.8

Use an actor-backed Agent when a model needs to choose or explain actions.
Keep exact arithmetic, parsing and business rules in Tools. A graph-backed
Agent instead runs the explicit route you declared. Neither choice requires
adding every composition layer.

## Selection and acceptance

Tool selection asks the model for an action. A contract checks observed behavior.
They are separate controls: valid JSON containing 42 does not prove add ran.

```python
@toolkit.tool
def add(a: int, b: int) -> dict:
    return {"value": a + b}

capability = toolkit.skill(name="arithmetic", tools=(add,))
actor = toolkit.Agent(
    "calculator", runtime=execution,
    framework=toolkit.framework("strands"), skills=(capability,),
    instructions="Call add with the user operands. Return its value as JSON.",
    policy={"tool_choice": "required"},
    contract={
        "tool_expectation": {
            "all_of": ["add"], "allowed": ["add"], "min_count": 1,
        },
        "completion": "when_required_tools_satisfied",
        "failure_policy": "no_unresolved",
        "output_schema": {
            "type": "object", "properties": {"value": {"type": "integer"}},
            "required": ["value"], "additionalProperties": False,
        },
    },
)
```

This is a declaration fragment: first import `agentic_systems as toolkit` and
configure `execution` with your explicit model/provider and limits. It does not
start inference. To run, authorize a metered campaign using the provider's
requirements. Inspect successful Tool events and `check_invariants()` as well as
`result.ok` and the business output. Do not reveal the expected answer in the
instructions when testing actual computation.

## Public options

| Field | Accepted values / meaning |
|---|---|
| `policy.tool_choice` | `auto` (default), `required`, `none` |
| `policy.temperature` | Finite number from 0 to 2; default 0 |
| `policy.repair`, `max_repairs` | Strict boolean, nonnegative integer; defaults false / 0 |
| `policy.finalize` | `never`, `on_max_turns` (default), `after_required_tools` |
| `policy.trace`, `strict` | `compact` (default) or `full`; strict boolean defaults false |
| `contract.tool_expectation` | `all_of`, `any_of`, `allowed`, `forbidden`: lists of declared Tool names; `min_count`: nonnegative integer |
| `contract.completion` | `default`, `when_required_tools_satisfied`, `always_finalize` |
| `contract.failure_policy` | `allow`, `no_unresolved` (default), `fail_fast` |
| `contract.input_schema`, `output_schema` | JSON Schema dictionaries; remote references are rejected |
| `contract.expected_output`, `expected_tool_outputs` | Expected dictionaries; Tool-output keys name declared Tools |

Omitted policy options retain established adapter defaults. Unknown keys and
unknown completion modes are rejected before effects. Contradictory required,
allowed and forbidden lists are rejected. Required names must exist and fit the
actor's Tool budget. `required` does not select a named Tool; use expectations
and an appropriate capability set. It does not authorize external side effects.

After required successful Tool evidence, continuation can permit a final answer;
that model request consumes budget too. The policy and instructions above were
used together in the [vLLM campaign](VALIDATION_215_20261108.md). This is not a
proof of every provider's schema support. `repair` is not permission to invent
missing business fields.

## Runtime and failures

`runtime` configures timeout, retries, backoff, concurrency, model turns, Tool
calls and tokens. `run(timeout_s=...)` supplies the shared root deadline. A
timeout does not forcibly stop a thread or roll back external work.

Constructor errors identify invalid declarations. Runtime failures return
unsuccessful RunResults with errors and evidence. A business decision such as
`review` can still be a successful execution. Use independent negative cases
to verify rejection; Eval stops at the first failing case.

[Signatures](API_214_SURFACE.md) · [Runtime controls](RUNTIME_SCHEDULER_214.md).
