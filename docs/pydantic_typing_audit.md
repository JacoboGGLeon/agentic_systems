# Pydantic typing audit for Agentic Systems 2.1

## Decision

Pydantic should own data that crosses a boundary: public configuration,
serialization, persistence, inspection, evidence, evals, and release
attestations. It should not own executable objects or native SDK resources.

The intended separation is:

    Pydantic Specs -> domain objects -> Protocols -> provider/framework adapters

This keeps validation strict without coupling the domain to OpenAI, AWS,
Ollama, vLLM, LangGraph, OpenAI Agents, or Strands.

## Current findings

The source contains 1,275 textual uses of Any. This number is not itself a
defect:

- 398 occur at external adapter/SDK normalization boundaries, where unknown
  native shapes are expected.
- 197 occur in core contract modules (results, evals, lineage, contracts,
  inspection, and runtime facades), where stronger schemas have higher value.

The current schemas package already establishes the correct direction:

- versioned Specs for Tool, Skill, Agent, System, Environment, Eval, runtime,
  and vLLM serving;
- closed immutable contracts;
- discriminated provider runtime configuration;
- secret exclusion;
- live and semantic attestation validation.

The main remaining debt is not the absence of Pydantic. It is that several
runtime-facing classes still expose open dictionaries instead of consuming the
typed projections already present in agentic_systems.schemas.

Pyright reports zero errors in the schemas package. The semantic E2E runner has
65 pre-existing strict-mode errors, dominated by open evidence dictionaries and
the dynamic top-level convenience API. Moving its boundary payloads to the
typed eval/result schemas is therefore measurable debt reduction, not cosmetic
annotation work.

## Priority 0: release blockers

### Contract-derived execution budgets

Status: implemented.

ContractExecutionBudget derives the minimum turn and Tool budget from the
contract. Explicit limits smaller than that minimum fail before an SDK call.
For a judge that must record one certification Tool, the portable default is:

    decision 1 + required Tool 1 + finalization 1 + protocol overhead 1
    + safety margin 1 = 5 turns

This calculation is independent of provider and framework. The runtime still
owns termination: completion=when_required_tools_satisfied stops after a valid
certification event.

### Shared execution-limit parity

Status: present, keep blocking.

SchedulerConfig, RuntimeConfig, and RunPolicy must continue delegating to the
same ExecutionLimits semantics. Add a parity property test whenever a new limit
is introduced.

## Priority 1: highest-value hardening

### Canonical usage schema

Consolidate the duplicate/open usage shapes into:

- TokenUsage: input, output, total, cached, reasoning;
- RequestUsage: requests and provider operations;
- LatencyUsage: client duration and provider-reported service latency;
- SchedulerUsage: attempts, retries, timeout, scheduler latency;
- UsageInfo: the aggregate.

Every field must be optional when the SDK provides no evidence. Never synthesize
provider latency. Preserve legacy aliases (prompt_tokens, completion_tokens)
only in the 2.x facade.

### Typed public RunResult projection

Keep RunResult as the compatible executable facade, but make its public
projection consume:

- RuntimeIdentity;
- canonical UsageInfo;
- typed ExecutionError;
- typed ToolEvent;
- ValidationReport;
- ReasoningMetadata;
- recursive child execution references.

Keep _native_result private. raw_responses must contain sanitized JSON evidence,
never SDK clients or sessions.

### Typed eval and semantic evidence

Replace open dictionaries in EvalCaseResult and SemanticEpisodeEvidence with:

- EvalCaseSpec;
- ExpectedOutcome;
- DeterministicValidation;
- JudgeResult;
- typed RunResultProjection;
- typed EnvironmentEpisode;
- typed LineageMemory.

This prevents an attestation from saying ok=true while an inner candidate,
judge, route, or lineage contradicts it.

### Typed inspection and lineage

Replace the InspectReport(dict) implementation with a typed
InspectReportSchema behind the existing facade. Type diagnostics,
relationships, provider selections, and framework selections.

Restrict LineageStep.evidence, LineageMemory.usage, validation, and metadata to
JSON-safe schemas. The domain builder may accept native values only before
normalization.

## Priority 2: manifest and authoring quality

### Skills

SkillManifest currently uses extra=allow and open dictionaries. Move extensions
into an explicit JSON-safe metadata/extensions field, version the manifest, and
migrate existing payloads. LoadedSkill must remain a domain object because it
owns callables and a live registry.

### Compatibility and API manifests

Convert CompatibilityCase, ApiContractEntry, and ContractScenario to closed
persisted schemas. This gives stable JSON Schema, explicit versions, and
reliable checksums without reflecting Pydantic-generated methods.

### Provider configuration

Keep RuntimeConfig and ModelProviderConfig as 2.x facades, but have both
delegate to the same discriminated provider specs. Provider-specific
credentials and endpoints then cannot leak into unrelated providers.

### Environment and chain evidence

Type persisted EnvironmentTransition and ChainStep projections. Do not turn
AgenticEnvironment, Chain, graph executors, callbacks, or reward functions into
Pydantic models.

## Intentionally not Pydantic

The following should remain domain objects, dataclasses, Protocols, or private
attributes:

- Agent, AgenticSystem, AgenticEnvironment, executable Skill;
- Executable, AsyncExecutable, execution plans, graph apps;
- Python callables, signatures, Tool registries, hooks, sessions;
- provider clients, SDK responses, model objects, processes, locks;
- framework-native agent_kwargs and run_kwargs values;
- adapter-local raw payloads before normalization.

For these objects, static typing and small Protocols provide more value than
runtime validation. Pydantic should describe their portable public projection,
not attempt to serialize their behavior.

## Implementation order

1. Finish and certify ContractExecutionBudget.
2. Consolidate UsageInfo and update every provider/framework adapter.
3. Introduce a typed RunResultProjection while preserving the 2.1 facade.
4. Type eval cases, deterministic validation, semantic episodes, and lineage.
5. Close and version Skill, compatibility, inspection, and API manifests.
6. Reduce Any in the domain/application layers; permit it at documented
   adapter boundaries.

Each step is blocked by JSON Schema stability, JSON round-trip, property tests,
secret redaction, API compatibility, offline provider/framework contracts, and
the live semantic matrix.
