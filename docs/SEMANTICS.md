# Semantics

Status: normative semantic baseline for Agentic Systems 1.1.

This document defines the meaning and limits of the public abstraction families
described in [`COMPUTATIONAL_GRAMMAR.md`](COMPUTATIONAL_GRAMMAR.md). It separates
portable semantics from Provider and Framework implementation details.

It does not define public algebraic syntax. Executable composition laws and
conformance fixtures belong to later checkpoints.

## Normative Language

MUST and MUST NOT identify compatibility or correctness requirements. SHOULD and
SHOULD NOT identify defaults that require a documented reason to violate. MAY
identifies permitted variation.

## Common Semantic Properties

### Identity

Identity answers which object a name, event, contract, or result refers to.

- Names MUST be stable within their owning composition boundary.
- Adapters MUST preserve semantic identity when creating Provider-native wrappers.
- Objects with the same name are not automatically identical when owned by
  different AgenticSystems.
- Binding a portable Agent changes execution ownership, not declared identity.

### Contract

A Contract is an inspectable condition over inputs, outputs, actions, failures,
or evidence.

- Static validation occurs before execution when facts are already known.
- Runtime validation occurs when execution evidence becomes available.
- Validation MUST identify failures structurally when a structured result exists.
- Compatibility aliases MAY exist but MUST resolve to one meaning.

### State

State is information intentionally carried between operations or transitions.

- State ownership MUST be attributable to an Agent, System, Graph, Environment,
  or caller.
- Mutation SHOULD be visible through returned state, transition history, result
  metadata, or an inspectable native runtime.
- Provider client caches and SDK objects are implementation state, not grammar
  state.

### Effects

An effect is an externally observable change beyond returning a value. The 1.1
API does not expose a first-class effect descriptor.

- Tools SHOULD document material effects in description or metadata.
- Retries MUST be applied carefully to effectful Tools.
- Missing effect metadata MUST NOT be interpreted as proof of purity.

### Determinism

Determinism means equivalent input and execution conditions produce equivalent
observable output.

- `python-runtime` can support deterministic execution but cannot make an
  effectful or time-dependent Tool deterministic.
- Temperature zero is not a universal Provider determinism guarantee.
- Reproducible Evals SHOULD control Provider, model, policy, fixtures, and
  external dependencies.

### Execution Requirements

Execution requirements include optional packages, credentials, network access,
models, endpoints, async support, and resource constraints.

- Missing requirements MUST fail explicitly.
- Optional requirements MUST NOT break import of Provider-independent core.
- Configuration inspection MUST NOT expose secrets.

### Evidence

Evidence is structured information supporting what occurred and why a result is
valid. It includes Tool events, data, validation, usage, trace, Environment
transitions, and Eval case results.

- Evidence MUST remain machine-readable before rendering.
- Lineage and Human Output MUST be traceable to underlying evidence.
- Renderers and adapters MUST NOT invent missing evidence.

### Failure

Failure is an observable inability to satisfy execution or Contract semantics.

- Provider errors, Tool errors, scheduler limits, validation failures, and Eval
  assertion failures are distinct categories.
- Recovery MAY produce overall success, but relevant recovered failures SHOULD
  remain observable.
- Fallback or degradation MUST identify the actual execution path.

## Abstraction Semantics

### Tool

Identity: `Tool.identity`, currently its public
ame`, inside one Tool registry.

Owns: callable capability, description, input/output Contracts, metadata, and
strictness.

Does not own: autonomous planning, Provider selection, shared registry lifetime,
or Environment state.

`Tool.run` validates configuration and input, invokes the callable, validates
output, and returns a `RunResult`. Tool failure is represented as a failed result
with a failed Tool event. A Provider adapter may create `RuntimeToolSpec`, native
schemas, or envelopes; these represent the Tool rather than new capabilities.

Example: `add.run({"a": 2, "b": 3})` records that `add` executed and produced
`{"result": 5}`.

Counterexample: an adapter renames `add`, drops its schema, and reports success
under the original identity.

A registry MUST reject a different Tool definition with the same identity unless
the caller explicitly selects `keep` or `replace`. Reusing the same definition
MAY be idempotent and MUST remain inspectable.

### Skill and LoadedSkill

Identity: Skill name plus owning package/System boundary; version refines
identity when present.

Owns: capabilities, prompts/instructions, Contracts, policies, metadata, and
optionally assets.

Does not own: an autonomous execution loop or Provider client.

`Skill` is an in-memory materialization. `LoadedSkill` is a loaded artifact with
manifest and filesystem concerns. Loading or adapting between them MUST preserve
name, declared Tool names, operational knowledge, and validation meaning.

Example: loading a Skill directory produces an inspectable manifest and runtime
Skill without executing its Agent.

Counterexample: incompatible Skill assets silently overwrite one another because
they share a name.

`Skill.compose(...)` MUST combine packages without executing Tools or models. Tool,
prompt, Contract, and policy collisions MUST fail by default. `keep` selects the
existing value and `replace` selects the incoming value only when requested
explicitly. The resulting Skill MUST expose its sources and decisions and MUST
remain a package rather than acquiring an Agent execution loop.

### Agent

Identity: Agent name inside its owning System or caller-managed scope.

Owns: actor instructions, declared Tool/Skill access, Contracts, policy,
input/output expectations, and execution preferences.

Does not own: Provider semantics, globally shared capabilities, or Graph topology.

An unbound Agent is a portable definition. A bound Agent can resolve registered
capabilities and execute. `agent(...)` MAY create a hidden System for ergonomic
use, but execution MUST expose the same ownership and runtime facts as an
explicit System path.

`Agent.run` and `Agent.arun` MUST return semantically equivalent `RunResult`
envelopes for equivalent successful executions. Unsupported async behavior MUST
fail explicitly.

Example: one Agent definition binds to a test System using `python-runtime` and
a production System using `bedrock-runtime` while retaining its Contracts.

Counterexample: changing Provider silently changes instructions or removes a
required Tool.

### AgenticSystem

Identity: caller-owned composition boundary.

Owns: shared registries, Agent binding, runtime defaults, Provider hydration,
execution implementation cache, and System inspection. System state is
composition/configuration state; factories do not transfer Graph, Environment,
or Eval ownership into the registry.

Does not own: the semantic definitions of Tool, Agent, Graph, Environment, or
Eval.

Registration MUST be local to the System. A different Tool or Skill definition
MUST NOT replace an occupied identity silently. Explicit conflict decisions and
selected sources MUST be available through composition inspection. Inspection MUST
expose enough registry and configuration information to explain whether an Agent
can execute. A System MAY offer factories without collapsing the separate
semantics of their results.

Example: `system.inspect()` identifies registered Tools and invalid references
before Provider execution.

Counterexample: registering a Tool in one System makes it available in another
through module-global mutation.

### Graph

Identity: Graph name and native or compiled instance.

Owns: state expectations, nodes, edges, entry, termination, and transition order.
Graph state is transition-scoped and remains distinct from System registry state
and Environment episode state.

Does not own: Provider selection unless a node explicitly contains an actor with
runtime configuration.

Graph state is not a `RunResult`, though it MAY contain or project one. Adapters
MUST preserve access to state and transition behavior. Compilation MAY produce a
Framework-native object without changing Graph-level meaning.

Example: an Agent node maps state to Agent input and maps RunResult evidence back
to explicit state fields.

Counterexample: replacing a RunResult in state with rendered text and losing
validation and Tool evidence.

### Environment

Identity: Environment instance and episode history.

Owns: observations, actions, transition invocation, rewards, termination,
truncation, memory, and transition history.

Does not own: Agent definition or Provider semantics.

`reset` begins an episode. `step` advances one transition and returns the
Gymnasium-shaped tuple supported by the public API. A transition MUST retain
enough evidence to relate observation, action, state, reward, and termination.
The Environment owns the episode seed and a local random generator. The seed
MUST be projected as evidence and MUST NOT mutate process-global random state.

Example: reset selects a record; step invokes the Graph, records an
`EnvironmentTransition`, computes reward, and exposes the next observation.

Counterexample: a step returns reward but discards which action and result
produced it.

### Eval

Identity: evaluation definition plus case set and controlled execution settings.

Owns: cases, checks, scoring/aggregation, and `EvalReport`.

Does not own: the semantics of the Agent or Environment under evaluation.

Each `EvalCaseResult` MUST preserve case identity, pass/fail meaning, and enough
evidence to diagnose failure. Aggregation MUST derive from case results.
Reproducibility MUST be classified as `deterministic`, `seeded`, or
`non_deterministic`. A seed is evidence, not proof that Providers, models,
Tools, external services, or schedulers replay deterministically. The full
contract is defined in `SYSTEM_ENVIRONMENT_EVAL_SEMANTICS.md`.

Example: one case fails during execution; another executes successfully but
fails an expected-output assertion. The report distinguishes both.

Counterexample: a report hides failed mandatory Contracts because one aggregate
score exceeds a threshold.

### Chain

Identity: ordered sequence of named steps.

Owns: deterministic ordering and value propagation.

Does not own: autonomous Tool choice, Environment interaction, or agentic loops.
Changing a Chain into an Agent or Graph is a semantic change and MUST NOT happen
implicitly through an adapter.

## Execution Semantics

### Conceptual Execution Context

One execution resolves:

```text
actor definition
+ System binding and registry
+ user input and mode
+ Runtime and concrete Provider
+ optional Framework adapter
+ Contract and merged RunPolicy
+ Scheduler limits
+ Graph/Environment state when applicable
+ correlation and trace metadata
```

This set is the conceptual Execution Context. It has no required public class in
1.1. Internal representations MAY reduce duplication if public construction and
results remain compatible.

### Resolution Order

The semantic order is:

1. Validate portable definitions and references.
2. Resolve System binding and capabilities.
3. Merge defaults, mode policy, and per-run policy.
4. Resolve `auto` to one concrete Provider.
5. Apply Scheduler limits.
6. Execute through the Provider and optional Framework adapter.
7. Normalize result and evidence.
8. Validate runtime Contracts.
9. Derive lineage, Human Output, or Eval projections on demand.

Implementations MAY optimize this sequence, but observable dependencies MUST be
preserved. Post-run validation, for example, cannot truthfully occur before
result evidence exists.

### Provider Resolution

Provider selection determines execution location and backend. It does not change
the conceptual actor or capability.

- `auto` is a selection request, not a Provider identity.
- The concrete Provider MUST be inspectable once resolved.
- Fallback MUST record the actual Provider used.
- Provider-specific data belongs in metadata unless it maps to a stable core
  field such as usage or Tool events.

### Framework Adaptation

Framework adaptation changes orchestration mechanics, not core meaning.

- Framework names MUST NOT be accepted as Provider names.
- Adapters MAY add native state, tracing, or lifecycle metadata.
- Adapters MUST preserve Tool Contracts and result evidence.
- Native objects SHOULD remain accessible when the adapter is intentionally thin.

### Scheduling

Scheduler configuration constrains execution. RunPolicy and Scheduler limits MUST
merge through documented precedence. The stricter safety limit SHOULD win when
independent limits overlap unless compatibility defines another explicit rule.

Timeout, retry exhaustion, concurrency rejection, Tool-call budget, and turn
budget are operational failures or controlled termination. They MUST be
distinguishable in structured result data or metadata.

## RunResult Semantics

| Field | Meaning |
|---|---|
| `ok` | Overall execution and required-Contract success |
| `final` | User-facing answer dictionary |
| `data` | Reusable evidence or execution payload |
| `text` | Text fallback or summary |
| `tool_events` | Ordered observable Tool invocations |
| `usage` | Provider/runtime resource facts when available |
| `validation` | Structured Contract validation |
| `errors` | Structured unresolved failures |
| `trace` | Execution events useful for diagnosis |
| `meta` | Extensible operational and adapter-specific facts |

Consistency requirements:

- `ok=True` MUST NOT coexist with unresolved required validation failure.
- `ok=True` MUST NOT hide an unresolved fatal execution error.
- A failed Tool event MAY coexist with overall success only when recovery is
  permitted and remains observable.
- `final`, `data`, and `text` MAY differ as projections but MUST NOT assert
  incompatible facts.
- Rendering MUST NOT alter result fields.
- Provider normalization MUST record the actual Provider used.

These requirements define target semantics. Later conformance work will classify
historical payloads before runtime validation becomes stricter.

## Observation Semantics

Observation has three levels:

1. Evidence: RunResult fields, Graph state, transitions, and case results.
2. Explanation: Lineage Memory derived from evidence.
3. Presentation: Human Output and notebook/CLI summaries.

Information may be compacted from level 1 to levels 2 and 3. It MUST NOT be
invented or contradicted. Programmatic consumers MUST use level 1.

Example: compact Human Output may omit token usage; it may not display
"validated" when `result.validation.ok` is false.

Counterexample: lineage claims a Tool supported an answer when no matching Tool
event exists.

## Degradation Semantics

Degradation is execution through a less preferred path after the preferred path
is unavailable or fails. It includes Provider fallback, sync fallback, reduced
tracing, or optional Framework bypass.

Degradation MUST be explicit when it can affect behavior, cost, latency,
capabilities, determinism, or evidence. A degraded result MAY be successful, but
metadata SHOULD state requested and actual paths plus the reason.

Implicit fallback is not Provider substitution conformance. Conformance requires
both paths to satisfy the same declared Contract.

## Public Helper Families

Public helpers realize abstraction semantics without creating new grammar roles:

| Family | Semantic role |
|---|---|
| `agent`, `runtime`, `scheduler`, `tool`, `graph` | Constructors/adapters |
| Contracts, policies, and expectations | Behavioral declarations |
| Output schemas and normalization | Stable answer/data shaping |
| Output Pydantic models | Typed observation projections |
| Lineage helpers | Evidence-derived explanation |
| Human/notebook utilities | Presentation and diagnostics |
| Engine constants and normalization | Stable Provider-selection values |
| Environment Graph builders | Specialized Graph constructors |
| Eval classes and `run_eval` | Verification definitions and reports |
| `core`, `providers`, `integrations` | Ownership namespaces |

Helpers MUST inherit the semantics of the abstraction they construct or project.
They MUST NOT create competing definitions.

## Compatibility Interpretation

For 1.1:

- public names and import style remain stable;
- Tool and Agent execution continue to return `RunResult`;
- Graph state, Environment tuples, and EvalReport remain distinct return shapes;
- both `Skill` and `LoadedSkill` remain supported;
- Provider and Framework dependencies remain optional at core import time;
- engine constants remain public values while engine modules remain internal;
- semantic tightening begins with documentation and conformance tests before
  runtime rejection becomes stricter.

Any implementation change violating these anchors requires an ADR, compatibility
analysis, migration path, and explicit release decision.

## Provider Substitution Semantics

Provider substitution preserves the normalized execution contract, not the
internal mechanism or generated answer. A substitutable Provider MUST preserve
canonical engine identity, structured Tool evidence, structured failure,
Contract validation, mode, and JSON-serializable `RunResult` fields.

Required capabilities are binary conformance requirements. Optional capabilities
MUST be declared as `supported`, `degraded`, or `unsupported`. A degraded
capability may be accepted explicitly, but MUST retain its reason; strict callers
may reject it before execution. Unsupported capabilities MUST NOT be silently
emulated or inferred from method names.

Provider substitution does not imply equal text, model quality, determinism,
latency, cost, token accounting, or vendor-native behavior. Applications that
need stronger semantic equivalence MUST express it through Contracts, expected
Tool evidence, and domain evaluations.

Example: changing from OpenAI to Bedrock is conforming when both results retain
the actual engine, validation, errors, and required Tool events even if their
final wording and usage differ.

Counterexample: a sync implementation exposes `arun` through a worker thread and
claims native async support without declaring degradation.

## Framework Execution Evidence

Framework configuration and Framework execution are distinct facts.
`framework_requested` records configuration; `framework_adapter` records the
adapter that actually projected or orchestrated execution. The compatibility
`framework` field may retain the requested label but MUST NOT be interpreted as
proof that an SDK ran.

Direct Agent execution sets no external adapter. LangGraph full-result
projection records `framework_adapter="langgraph"`. Provider identities such as
`openai-runtime` and `vllm-runtime` MUST NOT be used as Framework identities.

A Graph answer or compact trace is a lossy projection. Consumers requiring Tool
evidence, validation, errors, usage, or lineage inputs MUST request and consume a
full serialized RunResult state key.
