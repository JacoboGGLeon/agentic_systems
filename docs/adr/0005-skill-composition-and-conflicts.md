# ADR 0005: Skill Composition and Conflicts

Status: accepted

Date: 2026-07-18

## Context

`Skill.check()` rejected duplicate Tool names inside one Skill, but registration
used dictionary assignment in several paths. Different Tools or Skills with the
same visible name could therefore replace each other silently. The existing
behavior also made composition difficult to inspect and left prompt, contract,
and policy precedence undefined.

The 1.1 model defines Skill as a package of Tools and operational knowledge, not
as an Agent. Composition must preserve that boundary and remain independent of
Providers and Frameworks.

## Decision

1. Tool and Skill names are identities inside one composition boundary.
2. A different definition with an occupied identity fails by default.
3. Explicit policies are `error`, `keep`, and `replace`.
4. Reusing the same definition is idempotent and recorded as `reuse`.
5. `Skill.compose` combines Tools, prompts, contracts, and policy in source
   order and returns another non-executable Skill.
6. System and runtime registration use the same conflict vocabulary.
7. Skill, System, and runtime composition decisions are exposed as structured,
   JSON-serializable reports.
8. System registration rejects `keep` when it would make a Skill name refer to
   a different Tool implementation. Callers must compose first or explicitly
   replace the Tool.

## Consequences

- Previously silent collisions now raise actionable `ValueError` exceptions.
- Existing non-colliding registration is unchanged.
- Re-registering the same Skill or Tool definition remains idempotent.
- Intentional overrides require a visible keyword and leave evidence.
- `Skill.info()` and `AgenticSystem.inspect()` gain additive composition data.
- Replacing a Skill does not remove unrelated Tool identities already present in
  the System; removal semantics are outside this checkpoint.

## Rejected Alternatives

**Always last-wins.** Rejected because import and registration order would remain
a hidden behavioral input.

**Namespace every Tool automatically.** Rejected because it would break the 1.0
public names and make direct Tool reuse harder.

**Turn Skill into an executable actor.** Rejected because Agent already owns
autonomous selection and execution semantics.

**Introduce `+` or another composition DSL.** Rejected until ordinary API laws,
precedence, and contract compatibility are mature.

## Verification

`tests/composition/test_tool_skill_composition.py` verifies identity,
non-collision, explicit precedence, reuse, Skill coherence, runtime and Toolkit
registration, inspection, and JSON serialization.
