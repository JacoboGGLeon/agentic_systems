# Actor selection and required tools · 2.1.9

Use Agent(runtime=...) for actor execution. Keep exact computation in Tools.
For an explicit deterministic route use Agent(graph=...), with Tools as nodes.
Do not build a System or Environment merely to wrap one Tool.

Before inference choose the exact provider/model, endpoint or region, actor
framework, root deadline and persistent transport-attempt cap. Construction is
not a service check. No provider substitution or automatic campaign rerun.

When Tool execution is mandatory, combine:

```python
policy={"tool_choice": "required"}
contract={
    "tool_expectation": {"all_of": ["add"], "allowed": ["add"], "min_count": 1},
    "completion": "when_required_tools_satisfied",
    "failure_policy": "no_unresolved",
    "output_schema": {
        "type": "object", "properties": {"value": {"type": "integer"}},
        "required": ["value"], "additionalProperties": False,
    },
}
```

Pass these dictionaries as Agent arguments and declare add in its Skill.
Instruct the actor to call add with the user operands and return the Tool result.
Do not put the expected answer into the instructions. Check result.ok, exact
business data, invariants, and successful Tool events across result.walk().
A JSON answer containing 42 is insufficient without actual add(19,23) evidence.

Public tool_choice values are auto, required and none. Required does not name
one Tool. Completion values are default, when_required_tools_satisfied and
always_finalize; do not copy private adapter vocabulary such as must_call.
After required successful Tool evidence the existing adapter may allow automatic
selection for finalization. That next request still consumes budget.

For the 2026-11-08 Qwen3-4B Thinking/Strands campaign, automatic selection
produced the right answer without the Tool and correctly failed. Required policy
and answer-free instructions together passed. Both changed; do not claim one
variable alone caused the improvement or that a new SDK patch was needed.
The passing setup used vLLM 0.11.0, Transformers 4.57.1, Python 3.12, context8192
and output4096 with Hermes tools and deepseek_r1 reasoning parsing. Named server
presets and other models require their own evidence.

Keep schema validation strict. Missing fields and null are different; never fill
missing business data to turn a failure into PASS. Retain the failed request and
classify configuration, dependency, model behavior and SDK defects separately.
