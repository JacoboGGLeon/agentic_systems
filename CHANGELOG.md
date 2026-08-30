# Changelog

## 2.1.0 - 2026-08-30

Compatible hardening release. The 2.0 public facade remains stable while three
blocking gates now certify production readiness, Pydantic contracts and
provider/framework substitutability.

### Added

- A canonical registry for five Providers, four Frameworks, capabilities,
  dependencies, environment inputs, six scenarios and all 20 declared pairs.
- Strict versioned Pydantic schemas for execution limits, runtime discriminators,
  public specs, normalized outputs, errors and live attestations.
- Hypothesis boundary/round-trip coverage, Protocol conformance tests, Import
  Linter layer contracts, architecture branch checks, complexity and benchmark
  ratchets, dependency/license/secret audits and weekly mutation testing.
- Protected OpenAI, Bedrock and Ollama live workflows plus an exact-wheel vLLM
  Colab attestation contract with 24-hour freshness validation.
- Reproducible skill, Studio and release asset builds with secret auditing,
  hashes, SBOM generation and PyPI Trusted Publishing.
- Versioned `ModelArtifact`, `VLLMServerSpec`, `EndpointInfo` and `ServerHealth`
  schemas plus the `ModelServer` Protocol and explicit `model_server(...)` facade.
- One Colab tutorial that installs a CUDA-compatible vLLM stack, serves an
  Unsloth/Qwen artifact and certifies native, LangGraph, OpenAI Agents and Strands.

### Changed

- `SchedulerConfig`, `RuntimeConfig` and `RunPolicy` share `ExecutionLimits`;
  `max_tool_calls=0` now consistently means that tools are prohibited.
- `RunResult` uses one public projection across API, CLI, notebooks, Studio and
  evals. A balanced leading native reasoning block is removed from public text
  while raw evidence remains available explicitly.
- Retries are limited to classified transient failures; SDK and tool failures
  carry structured category, runtime identity, code and retryability.
- Provider/Framework lists in compatibility, CLI and Studio derive from the
  canonical registry instead of parallel hardcoded inventories.
- API checksums ignore methods injected by Pydantic, unwrap declared decorated
  methods and fingerprint only the public contract.
- Strands callbacks with typed event parameters are normalized into HookProvider
  objects, preserving compatibility across Strands 1.29 through the current 1.x.
- Strands model policy configuration now follows each SDK model's declared
  shape: OpenAI-compatible request parameters remain nested under `params`,
  while native models such as Bedrock receive `temperature` and `max_tokens`
  directly, preventing ignored settings and invalid-parameter warnings.
- Stateful Strands Agents retain their native SDK conversation while each
  public `RunResult` projects only the current invocation, preventing historical
  Tool events from being counted again against `RunPolicy.max_tool_calls`.
- The OpenAI Agents tutorial bootstraps its optional SDK dependency idempotently
  in a fresh Jupyter kernel instead of failing with a raw ModuleNotFoundError.
- Public local-model defaults and examples now use the exact certified Qwen3 4B
  Instruct 2507 artifacts for Ollama and vLLM; `.env` remains authoritative.

### Compatibility

- No top-level 2.0 export is removed.
- Existing `text`, `final`, `engine`, `model`, `usage` and `meta` result views
  remain available; typed projections are additive.

### Certification

- The primary five-Provider by four-Framework matrix passed all 20 routes and
  all 76 semantic episodes, including the deterministic Python control.
- Bedrock AWS credential-chain execution passed four Framework routes and 16
  semantic episodes in SageMaker, then repeated the same 4/4 and 16/16 result
  in the ADA enterprise sandbox.
- Across the primary matrix and both IAM environments, 108/108 semantic
  episodes were manually reviewed for public answer, hierarchical lineage,
  deterministic evidence, judge verdict, runtime identity and absence of
  fallback. `final-certification-summary.json` pins the exact wheel and evidence
  hashes used by the release gate.

All notable changes to Agentic Systems are documented here.
## 2.0.0 - 2026-08-19

Stable release of the unified computation model. The stable API contains 78
top-level exports, 370 traced export/member IDs, and 10 shared contract scenarios.

### Added

- `Executable`, `ExecutionPlan`, `SequentialPlan`, and `ParallelPlan` as the
  common contract for tools, agents, pipelines, and systems.
- Hierarchical `RunResult` values with execution and parent identity, child
  results, and tree traversal.
- `ToolSet` as the public name for a namespaced collection of tools.
- Pure `toolkit.skill(path=...)` loading without a hidden `AgenticSystem`.
- `ModelProviderConfig` and `toolkit.provider(...)`, separating provider
  configuration from runtime execution.
- `Agent.pipeline(...)`, `AgenticSystem.add(...)`, `compile(...)`, and direct
  system `run`/`arun` execution.
- Generic `Evaluator.evaluate(...)` support for any executable agent or system.
- A public 5 Provider x 4 Framework compatibility report and matrix notebook
  covering all 20 combinations.
- Portable `vllm`/`vllm-client` extras and a separate `vllm-server` extra.
- Real Native, LangGraph, OpenAI Agents, and Strands adapter dispatch.
- FrameworkConfig, exact native kwargs forwarding, Agent.prepare,
  Agent.native_agent, and RunResult.native_result.
- Offline 5 Provider x 4 Framework certification with fake transports and real
  Framework SDK loops.
- Layered 21-notebook Python curriculum mirrored by 21 preserved-output CLI notebooks.
- Deterministic Framework and matrix tutorials executed from clean kernels.
- OpenAI Agents offline certification for mixed Tools, typed output, sessions, guardrails and handoffs.
- Strands offline certification for mixed Tools, hooks, structured output and sync/async execution.
- Native Strands MCP certification over local stdio and Streamable HTTP
  transports, executed through the deterministic Python Provider.
- Non-secret Provider environment snapshots now load the nearest `.env`
  consistently with runtime factories and the CLI; OpenAI gains the symmetric
  `openai_environment_snapshot()` public helper.
- OpenAI Agents tracing is disabled per run by default for non-OpenAI Providers,
  preventing cross-provider trace export when several credentials coexist.
- Native Bedrock API-key recognition across auto resolution, diagnostics, and
  notebook readiness. `AWS_BEARER_TOKEN_BEDROCK` and the standard AWS credential
  chain are two authentication modes of the same boto3 `bedrock-runtime`
  Provider; boto3/botocore >=1.39 is required for the Bearer mode.
- Agentic Systems Studio as a portable product bundle with ten independently
  reusable system bundles, a system creator, SQLite catalog, Mermaid topology,
  notebooks, CLI, tests and sandbox validation.
- A standalone, reproducible `agentic-systems-skill-2.0.0.zip` skill artifact.

### Removed

- providers.python_direct, engines.python_direct, PYTHON_DIRECT_ENGINE,
  and the tools.compat quarantine.
- Runtime engine coercion, include_aliases, and output_contains aliases.
- style-only and declarative-only Framework states.
- The Bedrock-specific OpenAI Agents bridge, its nine public helper methods and
  its `disable_openai_runtime_tracing` constructor option. OpenAI Agents over
  Bedrock now uses the general Framework adapter exclusively.
- All disable_framework_tracing parameters. 2.0 has no parallel public switch
  or shim; native SDK configuration remains available, with a safe no-egress
  default for OpenAI Agents runs backed by non-OpenAI Providers.
- The domain-specific `tutorials/skills/accountability_otc` legacy tutorial and
  its private-data-shaped tests. The neutral `tutorial_api_inspection` filesystem
  Skill now teaches the 2.0 runtime Skill contract; OTC assets are absent from
  release bundles.

The tutorial gate executes 17 deterministic notebooks, validates 4 Provider notebooks
offline, and verifies 21 preserved-output CLI notebooks mapped 1:1 to the Python curriculum.

Live OpenAI and local Ollama `qwen3:4b` evidence passed all four Frameworks
through the strict matrix gate with real tool calls and normalized `RunResult`
values; Ollama executed 100% on an NVIDIA GPU. Bedrock bearer authentication and
inference-profile discovery passed, but live agent execution is not certified
because the account returned its daily-token `ThrottlingException`. Bedrock IAM
and vLLM server evidence remain external until their environments execute the
same `--live --require-pass` route.
The Bedrock ratchet rises to 100% over all 620 remaining statements.
Branch ratchets are fixed at Core 98.1%, Providers 97.7%, and Frameworks 98.8%;
each threshold is the measured alpha result truncated to one decimal and may
only increase.


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
