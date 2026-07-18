# System, Environment, and Eval Semantics

Status: normative through Checkpoint 1.1.6.

This document fixes the ownership, state, lifecycle, and reproducibility
boundary between `AgenticSystem`, Graph, `AgenticEnvironment`, and Eval.

## Ownership Matrix

| Abstraction | Owns | Does not own |
|---|---|---|
| System | capability registries, Agent bindings, runtime defaults, Provider hydration, composition provenance | Graph transition state, episode cursor/memory/history, Eval cases or scores |
| Graph | transition topology, node-local rules, state schema, entry and termination routing | System registries, Environment reward/history, Eval aggregation |
| Environment | episode id, seed and local RNG, cursor, observations/actions, memory, reward, termination/truncation, transition history | Graph topology, Agent/Provider semantics, Eval pass/fail policy |
| Eval | case definitions, assertions, scoring, aggregation, reproducibility declaration, report | mutation of the evaluated System, Graph, or Environment contract |

A convenience factory does not transfer ownership. `system.graph(...)`,
`system.environment(...)`, and `system.eval(...)` create or invoke separate
abstractions; their state does not become System registry state.

## State Flow

```text
System registry/config
        |
        v
Graph transition(state) <--- Environment action + episode state
        |
        v
Environment transition + reward + memory + history
        |
        v
Eval case result + aggregate report
```

Graph state is transition-scoped data. Environment state is mutable
episode-scoped data. System state is composition/configuration data. Eval state
is verification evidence. The same dictionary MUST NOT be treated as all four.

An Environment MAY place episode metadata in Graph state. The current contract
uses `state["episode"]` with `id`, `seed`, `step_index`, `row_index`, and
`total_records`. The Graph may read that projection but does not own the
Environment cursor or seed.

## Episode Lifecycle

1. Construction freezes the record snapshot and compiles or accepts an
   invokable transition.
2. `reset(seed=...)` starts a new episode, resets cursor/history, and seeds the
   Environment-owned `random.Random`.
3. `step(action)` builds Graph state, invokes one transition, computes reward,
   updates Environment memory, records evidence, then advances termination.
4. `close()` ends ownership of future episode execution for that instance.

`env.rng` is the only random generator controlled by `env.reset(seed=...)`.
Callbacks that require seeded behavior SHOULD consume this generator. The
Environment does not mutate Python's process-global random generator.

## Reproducibility Contract

The same seed is necessary but not sufficient for replay. Reproducible replay
requires all of the following:

- identical ordered records, inputs, actions, initial memory, and configuration;
- the same Agentic Systems and dependency versions;
- the same Graph, Agent, Provider, model, policy, and Tool definitions;
- all random branches consume the declared Environment seed or another recorded
  seed;
- external side effects are deterministic, captured, or replayed;
- concurrency and time-dependent behavior are fixed or recorded.

A seed controls `AgenticEnvironment.rng`; it does not automatically control a
remote model, Provider service, Tool process, network response, wall clock, or
framework scheduler.

Example: a reward callback and router both consume `env.rng`, and the Eval pins
fixtures and runtime configuration. Repeating the episode with the same seed
can be declared `seeded`.

Counterexample: `reset(seed=7)` calls a remote model with sampling enabled and
the report claims deterministic replay without a Provider seed guarantee.

## Eval Classification

`EvalReproducibility.classification` has three values:

| Value | Meaning | `replayable` |
|---|---|---|
| `deterministic` | Subject and evaluator contain no uncontrolled variation under the declared conditions. | `true` |
| `seeded` | Variation exists, every stochastic component consumes the recorded seed, and the declared conditions are pinned. | `true` |
| `non_deterministic` | At least one source of variation is uncontrolled or its replay guarantee is unknown. | `false` |

`run_eval` defaults to `non_deterministic`. This is intentionally conservative:
the runner can seed its Environment, but it cannot infer that an arbitrary
Agent, Provider, model, Tool, or external service is deterministic.

Callers opt into stronger claims explicitly:

```python
report = run_eval(
    agent,
    cases,
    determinism="seeded",
    seed=17,
    reproducibility_conditions=["provider snapshot model-2026-07"],
)
```

`seeded` requires a non-null seed. `non_deterministic` cannot claim
`replayable=True`.

## Report Invariants

`EvalReport` uses schema `agentic_systems.eval-report.v1` and embeds
`agentic_systems.eval-reproducibility.v1`.

For every valid report:

```text
total == len(cases)
passed == count(case.ok is true)
failed == total - passed
pass_rate == passed / total, or 1.0 when total == 0
ok == (failed == 0)
```

Construction rejects contradictions with one error listing every inconsistent
aggregate. `to_dict()` and `normalized()` preserve the same reproducibility
block so machine reports and human-output projections describe the same run.
