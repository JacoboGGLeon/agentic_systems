# Changelog

All notable changes to Agentic Systems are documented here.

## 1.1.0rc1 - 2026-07-18

Release candidate. Full notebook execution remains a manual release gate.

### Added

- Normative computational grammar and semantics.
- RunResult invariants for success, validation, partial failure, errors, usage,
  tool events, lineage, evidence, and serialization.
- Explicit Tool and Skill identity, conflict, precedence, and composition laws.
- Provider capability profiles and a shared conformance suite.
- Framework and Graph boundary profiles.
- Environment/Eval ownership and reproducibility classifications.
- Public `InspectReport` with structured and stable human projections.
- Static System diagnostics for relationships, contracts, capabilities,
  conflicts, limits, and degradation risks.
- Migration guide from 1.0 to 1.1.

### Changed

- The canonical deterministic Provider name taught by docs is
  `python-runtime`; `python-direct` remains a compatibility alias.
- Tool and Skill collisions require an explicit decision.
- Provider and Framework concepts are documented independently.
- Auto Provider resolution requires both AWS authentication and region signals
  before selecting Bedrock; a region alone no longer masks configured OpenAI or
  vLLM backends.
- Tutorial LM reviewers degrade explicitly when optional Provider execution
  fails, while required deterministic results preserve their own status.
- Arithmetic integration tutorials validate expected tool outputs, preventing a
  final answer from contradicting its execution evidence.
- Eval reports record deterministic, seeded, or non-deterministic replay
  conditions.
- The public API grows additively from 105 to 106 symbols with
  `InspectReport`.

### Compatibility

- `import agentic_systems as toolkit` is unchanged.
- Tool and Agent execution continues to return `RunResult`.
- `AgenticSystem.inspect()` remains dictionary-compatible.
- No public `ExecutionContext` object was added.
- No new optional runtime dependency is required by the core package.

### Verified Evidence

- Unit, contract, composition, and integration-boundary tests.
- Static compilation and source-clean checks for all 19 canonical notebooks.
- Package API inventory and documentation checksum.
- Wheel and source distribution content inspection.

Live OpenAI, Bedrock, vLLM, Strands SDK, and OpenAI Agents SDK execution are not
claimed. Strands and OpenAI Agents SDK adapters are not part of 1.1.

## 1.0.7

Baseline stable release used by the 1.1 grammar audit. Historical details remain
in the repository history and checkpoint 1.1.0 audit.
