# RunResult Contract

Status: current normative execution-result contract for the 2.1 line.

`RunResult` is the common execution envelope for Tool and Agent runs. This
document defines structural invariants that all producers and adapters must
preserve without forcing Graph, Environment, or Eval APIs to return RunResult.

## Contract

| Area | Invariant |
|---|---|
| `final`, `data`, `text` | They are distinct projections and may differ, but must not make incompatible factual claims. Empty `final` is derived from legacy `data`/`text`. |
| Success | `ok=True` means execution and every required Contract succeeded. |
| Validation | Required validation failure forces `ok=False` and creates structured `validation_failed` errors. |
| Partial failure | Failed Tool events may coexist with overall success only when recovered or explicitly allowed by policy. |
| Errors | Errors remain structured evidence. Success with errors is reviewable, not automatically invalid, because recovered failures are valid. |
| Usage | Numeric usage values must be non-negative. Missing metrics are preferable to invented values. |
| Tool events | Non-empty event ids are unique. A successful event cannot carry an active error. Event order is evidence. |
| Lineage | Lineage preserves overall status, usage, validation, and Tool evidence; it is a projection, not a source of truth. |
| Evidence | `data`, Tool events, validation, errors, usage, and trace remain machine-readable before rendering. |
| Serialization | `model_dump(mode="json")`, `to_dict()`, and JSON round-trip must preserve the public envelope. |

## Projection Rules

`final` is the answer shaped for the user request. `data` is reusable execution
evidence or business payload. `text` is a textual fallback or summary. Equality
between these fields is not required.

Valid:

```python
RunResult(
    text="Request approved.",
    data={"record_id": 7, "rule": "R-12"},
    final={"decision": "approved"},
)
```

Invalid: `final` says approved while `data` identifies the authoritative decision
as rejected. Structural validation cannot infer every domain contradiction, so
domain Contracts remain responsible for factual consistency.

## Success And Validation

`RunResult.apply_validation(...)` is the canonical way to attach Contract
validation. It:

1. serializes the `ValidationResult` into `validation`;
2. combines execution and validation status without allowing failed validation
   to become success;
3. records each error-severity issue as a deduplicated structured error.

Passing warnings do not force failure. Reapplying the same validation does not
duplicate errors.

## Partial Failure

Tool failure classification is chronological and name-scoped:

- recovered: a later successful event for the same Tool exists;
- unresolved: no later successful event for that Tool exists.

Recovered and unresolved events remain in `tool_events`, `errors`, and trace.
`errors[].resolved` and `recovered_by_tool_event_id` make recovery explicit.

An unresolved Tool failure with `ok=True` is a warning because an explicit
partial-failure policy may permit it. Contract validation decides whether a
specific run requires `no_unresolved` or `fail_fast` behavior.

## Invariant API

```python
check = result.check_invariants()
check.raise_if_failed()

# Equivalent convenience API:
result.raise_if_inconsistent()
```

`check_invariants()` does not mutate the result. Errors identify contradictions;
warnings identify states that are valid only with additional policy or context.

Current error codes:

```text
success_with_failed_validation
validation_status_mismatch
duplicate_tool_event_id
successful_tool_event_with_error
negative_usage_value
not_json_serializable
```

Current warning codes:

```text
success_with_unresolved_tool_failure
success_with_recorded_errors
failure_without_error_evidence
success_without_answer
```

## Serialization Compatibility

The 1.1 compatibility baseline preserves:

- all existing RunResult fields;
- `agentic_systems.run.v1` normalized schema identity;
- `agentic_systems.trace.v1` trace identity;
- `to_dict()` as Pydantic JSON-mode output;
- legacy automatic derivation of `final` from `data` and `text`;
- Graph state, Environment tuple, and EvalReport return boundaries.

The only additive error detail is recovery metadata for failed Tool events and
structured errors for failed required validation. Consumers must continue to
ignore unknown keys inside error objects, as required for additive compatibility.

Round-trip expectation:

```python
payload = result.to_dict()
restored = RunResult.model_validate(json.loads(json.dumps(payload)))
assert restored.to_dict() == payload
```

Provider-native raw responses are retained separately and are not the portable
serialization contract.

## Final Answer And Rendering

`RunResult.final` is the answer shaped for the user request. `RunResult.data` is
reusable evidence or payload, and `RunResult.text` is a textual fallback. These
projections may differ without contradicting one another.

```python
schema = toolkit.output_schema(["procedure", "final_result"])
answer = toolkit.final_answer(
    {"procedure": ["2 + 3 = 5"], "final_result": 5},
    schema=schema,
)
```

Normalization is stable:

```text
mapping          -> the same mapping
list of mappings -> {"rows": [...]}
other list       -> {"items": [...]}
scalar           -> {"value": ...}
None             -> {}
```

`human_result(...)` renders the answer and selected evidence but is never the
source of truth. Graphs, Environments and Evals may contain or project a
RunResult; they retain their own return contracts.
