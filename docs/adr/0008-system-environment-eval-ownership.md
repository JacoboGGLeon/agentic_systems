# ADR 0008: System, Environment, and Eval Ownership

Status: accepted

Date: 2026-07-18

## Context

System, Graph, Environment, and Eval were public and documented, but episode
state ownership and reproducibility were underspecified. `reset(seed=...)` used
the seed in episode identity without exposing an Environment-owned random
generator. `run_eval` called itself deterministic while it could execute an
arbitrary remote or stochastic Agent, and aggregate report fields could
contradict their case list.

## Decision

1. System owns composition and runtime binding, not Graph or episode state.
2. Graph owns transition topology and state rules, not Environment lifecycle.
3. Environment owns episode identity, cursor, memory, rewards, history, seed,
   and one local random generator.
4. Eval owns cases, assertions, aggregation, classification, and report
   evidence, not the semantics of its subject.
5. Environment seeds never mutate the process-global random generator.
6. Evals classify reproducibility as `deterministic`, `seeded`, or
   `non_deterministic`; the conservative default is `non_deterministic`.
7. Eval reports validate aggregate fields against case results.

## Consequences

- `AgenticEnvironment.seed` and `AgenticEnvironment.rng` are inspectable.
- Episode seed evidence appears in Graph state, info, render, and summary.
- Seed-aware callbacks can replay without relying on process-global state.
- `EvalReport` serialization gains schema and reproducibility metadata.
- Existing report constructors remain valid through additive defaults when
  their aggregates already match their cases.
- Strong replay claims require explicit caller classification and conditions.

## Rejected Alternatives

**Seed Python's global random module.** Rejected because unrelated libraries and
parallel episodes would share hidden mutable state.

**Infer determinism from Provider name.** Rejected because model settings,
Tools, external services, scheduling, and Provider behavior can still vary.

**Repair inconsistent report totals silently.** Rejected because stored or
caller-created contradictions must fail visibly.

**Make Environment own Graph topology.** Rejected because the same Graph may be
reused across episodes and Framework lifecycles remain separate.

## Verification

`tests/contracts/test_system_environment_eval_semantics.py` verifies local RNG
replay and isolation, seed evidence, Eval classifications, serialization
consistency, and contradiction errors.
