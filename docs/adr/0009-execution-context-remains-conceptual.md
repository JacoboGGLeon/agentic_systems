# ADR 0009: Execution Context Remains Conceptual

Status: accepted

Date: 2026-07-18

## Context

The computational grammar names Execution Context as the conditions resolved
for one run: actor and System binding, input, mode, Runtime/Provider, optional
Framework, Contract, policy, scheduler, state, and correlation metadata.

These conditions already have explicit owners. A new object could duplicate
`RuntimeConfig`, `AgenticSystem`, `RunPolicy`, Graph/Environment state, and
`RunResult` metadata. The checkpoint must decide whether a public class,
internal object, or concept reduces complexity.

## Decision

Keep Execution Context as a normative conceptual role only.

1. Do not add a public `ExecutionContext` API.
2. Do not add an internal aggregate object in 1.1.7.
3. Do not change Agent, System, Runtime, Provider, Graph, Environment, Eval, or
   result signatures.
4. Keep resolution values in their current owners and ephemeral local
   variables.
5. Permit narrow helpers when they remove control-flow duplication, without
   naming or exposing a context object.
6. Reconsider an internal immutable value only when measured adapter or
   propagation duplication satisfies the triggers in
   [the current Computational Model](../COMPUTATIONAL_MODEL.md).

## Consequences

- The grammar gains an explicit term without adding another composition root.
- Runtime selection remains `RuntimeConfig` responsibility.
- Capability composition remains `AgenticSystem` responsibility.
- Per-run limits remain `RunPolicy` responsibility.
- State and evidence remain in Graph, Environment, and `RunResult` boundaries.
- Public API count, signatures, schemas, dependencies, and runtime behavior are
  unchanged.

## Rejected Alternatives

**Public ExecutionContext dataclass.** Rejected because callers have no distinct
workflow that requires constructing it, and every field would duplicate an
existing owner.

**Internal mutable context object.** Rejected because it would create shared
state and unclear concurrency ownership without reducing adapter complexity.

**Context variable or process-global current execution.** Rejected because
implicit ambient state conflicts with explicit sync/async and episodic
boundaries.

**Alias RuntimeConfig as ExecutionContext.** Rejected because RuntimeConfig
selects execution infrastructure; it does not own input, capabilities, state,
policy evidence, or results.

## Compatibility

Checkpoint 1.1.7 changes zero public symbols, call signatures, serialization
schemas, optional dependencies, and runtime behaviors. `PUBLIC_API` remains at
105 symbols.

## Verification

The full suite, public API smoke, signature inspection, compileall, and wheel
build validate the no-code decision. The checkpoint report records exact
results.
