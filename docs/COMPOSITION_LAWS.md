# Composition Laws

Status: normative for Checkpoint 1.1.3.

These laws govern Tool and Skill composition independently of Provider and
Framework implementations. They apply inside one explicit composition boundary,
such as a Skill, an AgenticSystem, a Toolkit, or the neutral runtime registry.

## Law 1 - Scoped Identity

**Motivation.** A visible capability name must identify the implementation that
will execute.

**Definition.** A Tool identity is its public `name` inside a composition
boundary. A Skill identity is its public `name` inside that boundary. Identity
is scoped, not process-global.

**Scope.** Tool, Skill, Toolkit, AgenticSystem, and neutral runtime registries.

**Counterexample.** Two different `lookup` functions are registered and the
second silently becomes executable while inspection still describes the first.

**API implication.** `Tool.identity` and `Skill.identity` expose the scoped
identity used by composition.

**Test strategy.** Assert that identity, registry lookup, execution, and
inspection report the same name and selected source.

## Law 2 - No Silent Collision

**Motivation.** Registration order must not accidentally change behavior.

**Definition.** A different definition with an occupied identity MUST fail by
default. The failure MUST identify the kind, identity, existing source, incoming
source, and available explicit policies.

**Scope.** Tool and Skill composition and registration.

**Counterexample.** Assigning `registry[name] = incoming` without checking the
existing definition.

**API implication.** Composition and registration default to
`on_conflict="error"`.

**Test strategy.** Register or compose distinct definitions with equal names and
assert failure plus preservation of the original selection.

## Law 3 - Explicit Precedence

**Motivation.** Some callers intentionally prefer an existing or incoming
definition.

**Definition.** `keep` selects the existing value and `replace` selects the
incoming value. Neither policy is inferred. Source order is the order supplied
to `Skill.compose`; registry order is registration order.

**Scope.** Tools, prompts, contracts, policies, Skill identities, Toolkits, and
neutral runtime registration.

**Counterexample.** "Last import wins" or dictionary update order acts as an
undocumented override policy.

**API implication.** `Skill.compose(..., on_conflict=...)`,
`AgenticSystem.tool(..., on_conflict=...)`, `AgenticSystem.skill(...)`, Toolkit,
and neutral runtime registration accept `error`, `keep`, or `replace`.

**Test strategy.** Compose the same inputs under `keep` and `replace`, then
verify selected implementation, instructions, source, and decision report.

## Law 4 - Idempotent Reuse

**Motivation.** A shared Tool may be packaged by multiple Skills without being
duplicated or treated as a conflict.

**Definition.** Reusing the same Tool object, or the same callable with the same
identity and contracts, is idempotent. It produces one selected Tool and a
`reuse` composition event.

**Scope.** Tool registration and Skill composition.

**Counterexample.** Rejecting the same immutable Tool object merely because two
Skills reference it.

**API implication.** Reuse requires no override policy and does not rebuild the
runtime entry.

**Test strategy.** Compose two Skills that share one Tool and assert one Tool,
stable object identity, and an inspectable `reuse` event.

## Law 5 - Skill Coherence

**Motivation.** A Skill packages capabilities and operational knowledge; it is
not an autonomous actor or an alias for a different implementation.

**Definition.** `Skill.compose` MUST return a Skill containing the selected
Tools, prompts, contracts, policy, metadata provenance, and conflict decisions.
It MUST NOT execute Tools, call a model, expose `run`, or hide a conflicting Tool
behind `keep` during System registration.

**Scope.** Runtime Skill objects. Filesystem `LoadedSkill` remains a packaging
adapter and is not merged into the runtime object model in this checkpoint.

**Counterexample.** Registering a Skill whose `lookup` object differs from the
System's selected `lookup`, then letting Agents execute the System object as if
it belonged to that Skill.

**API implication.** Use `Skill.compose` before registration when `keep` should
resolve collisions across packages. Use explicit `replace` when the incoming
Skill is intended to own the System Tool identity.

**Test strategy.** Assert that composed Skills are non-executable and that
System registration rejects a `keep` resolution that would break package
coherence.

## Law 6 - Inspectable Resolution

**Motivation.** Deterministic rules are insufficient if users cannot see which
rule selected the executable capability.

**Definition.** Composition reports MUST be JSON-serializable and include stable
schema identity, selected identities, sources, and ordered decisions. Inspection
MUST NOT execute Tools or models.

**Scope.** `Skill.composition`, `AgenticSystem.composition`, runtime composition,
and `AgenticSystem.inspect`.

**Counterexample.** A registry rejects or overrides a collision but exposes only
the final list of names, with no provenance or decision.

**API implication.** Composition reports use additive `*.v1` schemas and appear
inside System inspection.

**Test strategy.** JSON round-trip each report and compare selected source with
the implementation actually executed.

## Deliberate Limits

- No algebraic operators or public DSL are introduced.
- Tool identity is not globally unique across processes or Systems.
- `replace` is additive registration; it does not unregister unrelated Tools
  that came from an older Skill package.
- Semantic compatibility of different Tool input/output contracts remains a
  separate contract-composition problem.
- Instructions are represented by the existing prompt mapping; this checkpoint
  does not create an instruction-merging language.
