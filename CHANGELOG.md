# Changelog

All notable changes to Agentic Systems are documented here.

## 1.1.3 - 2026-08-11

Documentation-maintenance release preserving the 1.1 runtime behavior and
111-symbol public API while consolidating current product evidence.

### Changed

- Consolidated conceptual, semantic and contract documents into explicit current
  sources of truth.
- Removed repository-local ADRs, an unaccepted RFC, migration notes and
  release/checkpoint narratives after consolidating every still-current
  contract into the canonical product documentation.
- Corrected stale Graph backend, migration, CLI inventory and release narratives.
- Reduced `docs/` to current product guidance; Git, this changelog and GitHub
  Releases remain the historical evidence layers.
- Reorganized the 66-module pytest layout into 92 owner-based modules across
  API, unit, integration, Provider, and release layers; removed historical
  `extended`, `branches`, `residual`, and `remaining` naming from test files and
  test functions.
- Removed one redundant negative wrapper-absence test. The resulting 383 tests
  preserve the behavioral boundary through the frozen public-API and test-suite
  architecture gates.
- Made API/documentation coherence executable: the API index must equal the 111
  top-level symbols in order, every documented `toolkit.*` call is checked against
  source signatures, and each tutorial `api_coverage` inventory must equal its real
  AST usage.

## 1.1.2 - 2026-08-10

Maintenance release completing the controlled retirement of legacy tests and
the internal partition of the Bedrock runtime.

### Changed

- Migrated or retired all 52 routed legacy test modules into owner-based API,
  unit, Provider, release, and contract suites; removed the quarantine, dynamic
  loader, Ruff exclusion, and numeric inventory guard.
- Split the 2,961-line Bedrock implementation behind its unchanged public
  `providers.bedrock_runtime` facade into focused internal components; reduced
  `run_direct` to a 37-line orchestrator.
- Added frozen public-API and Bedrock-signature contracts plus Python 3.10/3.14
  CI gates for Ruff, tests, coverage, packaging, and isolated wheel smoke.
- Kept core coverage at 100% over 6,194 statements and introduced a separate
  Bedrock coverage ratchet with `fail_under = 53.1` (measured 53.17%).
- The tutorial gate executes 13 deterministic notebooks.
- It checks 5 Provider notebooks statically; live OpenAI, Bedrock and vLLM
  execution remains outside the release claim.
- Removed four genuinely unused imports from active source.
## 1.1.1 - Unpublished checkpoint (2026-08-10)

Unpublished maintenance checkpoint focused on coherence and surface reduction; superseded by 1.1.2.

### Changed

- Removed accidental top-level `build_single_agent_step_graph` and `PUBLIC_API`
  attributes; the canonical routes are `toolkit.graph(...)` and `toolkit.__all__`.
- Removed the undocumented `vll` extra and the misleading `tutorials` extra.
  Notebooks remain repository content and their dependencies now live in `dev`.
- Scoped the 100% coverage claim to core modules because the Bedrock runtime is
  explicitly omitted from the coverage configuration.
- Separated deterministic notebook execution evidence from static Provider
  notebook checks.
- Updated stable installation and onboarding instructions.

## 1.1.0 - 2026-07-19

Stable 1.1 release. The release candidate was promoted after the complete
manual notebook matrix and updated automated gates passed.

### Closure evidence

- 18 of 18 canonical notebooks executed from fresh kernels; no failures.
- 393 tests passed with 100.00% coverage over 6,193 statements.
- Canonical construction remains under `import agentic_systems as toolkit`.
- Added ergonomic `toolkit.skill(...)`, `toolkit.environment(...)`, and
  `toolkit.eval()` factories over existing public types.
- Preserved `toolkit.system(...)` to avoid shadowing the supported
  `agentic_systems.system` module import.
- vLLM installation, server startup, SDK smoke and Agentic Systems smoke are
  opt-in and report explicit skips when disabled.
- Live OpenAI, Bedrock and vLLM execution remains outside the release claim.

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
- Tutorials 11-14 were consolidated into three end-to-end paths: single
  AgenticSystem, multi-agent System, and the same multi-agent System as Graph.
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
- Static compilation and source-clean checks for all 18 canonical notebooks.
- Package API inventory and documentation checksum.
- Wheel and source distribution content inspection.

Live OpenAI, Bedrock, vLLM, Strands SDK, and OpenAI Agents SDK execution are not
claimed. Strands and OpenAI Agents SDK adapters are not part of 1.1.

## 1.0.7

Baseline stable release used by the 1.1 grammar audit. Historical details remain
in the repository history and checkpoint 1.1.0 audit.
