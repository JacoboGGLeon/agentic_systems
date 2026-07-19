# ADR 0010: Extend AgenticSystem.inspect for Static Analysis

Status: accepted

Date: 2026-07-18

## Context

`AgenticSystem.inspect()` already validated registries and Agents, returning a
dictionary with summary counts, warnings, errors, and composition provenance.
It did not expose relationships, contracts, Provider/Framework profiles,
capabilities, limits, or degradation risks, and its human output contract was
undefined.

The checkpoint requires pre-execution inspection without model or Tool calls.

## Decision

1. Keep `AgenticSystem.inspect()` as the single inspection entry point.
2. Preserve `InspectReport` as a dictionary for existing callers.
3. Make `InspectReport` public and add `to_dict()` and `human_text()`.
4. Add schema `agentic_systems.inspect.v1` and the normative sections defined in
   `STATIC_SYSTEM_INSPECTION.md`.
5. Reuse Provider, Framework, composition, Tool, Skill, Agent, Runtime, and
   scheduler declarations as sources of truth.
6. Normalize diagnostics with actionable suggestions.
7. Prohibit Tool, model, Provider, Framework, and Graph execution during
   inspection.

## Consequences

- Existing dictionary indexing and `raise_if_errors()` continue to work.
- The public surface gains one symbol: `InspectReport`.
- Reports become stable for CLI/notebook rendering and machine policy gates.
- Selected unsupported/degraded capabilities are visible before execution.
- Static inspection describes declared state; it does not certify credentials,
  network availability, model behavior, or dynamic side effects.

## Rejected Alternatives

**Create a separate inspector service.** Rejected because it would duplicate
System registry access and split the public inspection contract.

**Execute smoke calls during inspection.** Rejected because static analysis must
be safe before credentials, endpoints, or side effects are available.

**Return only Pydantic models.** Rejected because existing callers depend on
dictionary behavior.

**Infer capabilities from imports or live clients.** Rejected because static
Provider and Framework profiles already define the contractual boundary.

## Compatibility

Existing `inspect()` calls, dictionary fields, and error behavior remain
compatible. New fields and methods are additive. `PUBLIC_API` increases from
105 to 106 due to public `InspectReport`.

## Verification

Contract tests use Tool functions that fail if called, verify deterministic
human output, JSON round-trip, all required sections, actionable diagnostics,
and legacy error behavior.
