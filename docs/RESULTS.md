# RunResult · 2.1.8

Agent, System, Environment and Eval executions return RunResult. Tools also return it through run/arun. A graph node call instead participates in the graph-update protocol.

| Method | Return type | Purpose |
|---|---|---|
| evidence() | dict | Primary JSON-compatible export including children |
| to_dict() | dict | Compatibility alias with the same content |
| trace(mode='compact', max_steps=20) | dict | Bounded execution projection; 'full' requests detailed inspection |
| human_results(max_steps=8, max_chars=4000) | str | Bounded readable explanation without inference |
| lineage(...) | Lineage object | Structured execution/tool relationships |
| walk() | Generator of RunResult | Root followed recursively by descendants; not a concurrency timeline |
| check_invariants() | Validation object | Internal consistency checks, not business correctness |

Lineage supports to_dict(), explain(), render() and to_prompt_context(max_chars=1600). Validation exposes ok, issues and to_dict(). These are returned objects, not additional public constructors. Parameters shown with defaults after the first argument are keyword-only where specified in [exact signatures](API_214_SURFACE.md).

| Fields | Meaning |
|---|---|
| data, text, final | Structured business data and recorded response representations; exact shape depends on the unit |
| ok, status, errors, validation | Execution outcome and checks |
| execution_id, parent_execution_id, children | Execution identity and hierarchy |
| messages, tool_events, raw_responses | Recorded interactions and Tool evidence |
| usage, engine, model, mode | Recorded consumption and execution metadata |
| interrupts, continuation | Process-local pause metadata, not portable recovery |
| meta, trace_schema_version | Additional metadata and trace schema identity |

```python
result = agent.run({"value": 3})  # previously declared agent
payload = result.evidence()
assert payload == result.to_dict()
lineage_dict = result.lineage().to_dict()
validation = result.check_invariants()
print(validation.ok, validation.issues)
print(result.human_results())
for execution in result.walk():
    print(execution.execution_id, execution.status)
```

The export retains existing JSON normalization and secret-redaction rules. It is not general anonymization: business data, prompts and responses can remain sensitive. check_invariants validates structural consistency; it does not prove an answer true or a route correct. Use [Eval checks](EVALUATION.md) for those requirements.

[Migration](MIGRATION_217_TO_218.md) · [Execution](EXECUTION.md)
