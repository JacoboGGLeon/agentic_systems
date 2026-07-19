# Execution Context Decision

Status: normative through Checkpoint 1.1.7.

## Decision

Execution Context remains a conceptual role. Agentic Systems 1.1.7 does not add
a public `ExecutionContext` class, an internal context container, a new
constructor argument, or a new serialization schema.

The concept names the resolved conditions relevant to one execution. It does
not own them and is not a composition root.

## Existing Owners

| Concern | Existing owner |
|---|---|
| Provider, model, region, scheduler configuration | `RuntimeConfig` |
| Tool/Skill registries, Agent binding, runtime defaults | `AgenticSystem` |
| Actor instructions, contracts, selected capabilities | `Agent` |
| Limits, sampling, repair, trace, and tool-choice policy | `RunPolicy` |
| User payload and mode | `Agent.run` / `Agent.arun` call |
| Transition state | Graph or native Framework runtime |
| Episode memory, seed, cursor, and history | `AgenticEnvironment` |
| Correlation, execution identity, usage, and evidence | `RunResult` metadata and fields |

Execution Context is the read-only conceptual union of those resolved values at
one point in time. It MUST NOT become an alternative owner for any row above.

## Why No Object

A useful object must establish one of these benefits:

1. remove repeated resolution logic from at least three independent execution
   paths;
2. provide an atomic value that must cross a real adapter boundary;
3. enforce invariants that cannot be enforced by existing owners;
4. enable a public workflow that cannot be expressed without copying internal
   dictionaries.

None is true in 1.1.7.

`Agent.run` and `Agent.arun` mirror policy and scheduler resolution, but that is
sync/async control-flow symmetry, not evidence that a second configuration
object is needed. Existing helpers already own policy resolution, scheduler
execution, result finalization, and metadata attachment. A context container
would aggregate references to those objects and then immediately unpack them
for Providers.

## Non-Goals

Execution Context is not:

- another name for `RuntimeConfig`;
- a replacement for `AgenticSystem`;
- a mutable dependency-injection service locator;
- Graph state or Environment memory;
- a request-global singleton or `contextvars` store;
- a second result/evidence envelope;
- prompt context such as `LineageMemory.to_prompt_context()`.

The unqualified word "context" MAY continue to describe Tool call metadata,
Framework callback objects, or prompt material. Those uses do not imply the
Execution Context concept.

## Resolution View

The conceptual view is resolved in this order:

```text
Agent definition + System binding
        -> input and mode
        -> RuntimeConfig and concrete Provider
        -> Contract and merged RunPolicy
        -> Scheduler limits
        -> optional Graph/Framework/Environment state
        -> execution
        -> RunResult evidence and correlation metadata
```

This order is normative. Its in-memory representation is not.

## Compatibility Impact

Measured against the Checkpoint 1.1.6 baseline:

| Surface | Change |
|---|---:|
| Top-level public symbols | 0 |
| `PUBLIC_API` count | 0 (remains 105) |
| `RuntimeConfig` fields/signature | 0 |
| `AgenticSystem` constructor/factories | 0 |
| `Agent.run` / `Agent.arun` signatures | 0 |
| Provider and Framework adapter protocols | 0 |
| Graph/Environment return shapes | 0 |
| `RunResult` and Eval serialization schemas | 0 |
| Optional dependencies | 0 |
| Runtime behavior | 0 |

The checkpoint is documentation-only by decision. No migration path or
deprecation is required.

## Reconsideration Triggers

The ADR may be superseded when evidence demonstrates at least one of:

- three or more execution adapters duplicate the same immutable resolved field
  set and validation;
- tracing/cancellation/correlation must cross sync, async, Provider, and
  Framework boundaries atomically;
- an extension API needs a stable, provider-neutral invocation object;
- concurrency bugs arise from separately propagated execution metadata.

Even then, the first candidate SHOULD be an internal immutable resolution value.
A public API requires independent user-facing use cases, versioned
serialization rules, and conformance tests.
