# Grammar To API Map

Status: stable 1.1 baseline, promoted as
`1.1.0`.

This document maps the normative 1.1 computational grammar to the release
candidate implementation. `COMPUTATIONAL_GRAMMAR.md`, `SEMANTICS.md`, and the
specialized contract documents define normative behavior.

## Public Surface Baseline

The supported import remains:

```python
import agentic_systems as toolkit
```

`src/agentic_systems/api.py` defines the public inventory and
`src/agentic_systems/__init__.py` exports every name in `PUBLIC_API`.

| API group | Symbols | Role |
|---|---:|---|
| `RECOMMENDED_API` | 38 | Names intended for first-use documentation |
| `CORE_API` | 54 | Core factories, contracts, results, output, and composition objects |
| `BEDROCK_PRIMITIVE_API` | 2 | Direct Bedrock primitives |
| `CHAIN_API` | 2 | Sequential composition helpers |
| `ENGINE_API` | 7 | Canonical engine names and normalization |
| `INTEGRATION_API` | 2 | Recommended graph integration entry points |
| `EVAL_API` | 5 | Evaluation cases, reproducibility, evaluator, report, and runner |
| `ENVIRONMENT_API` | 9 | Episodic environment and specialized graph helpers |
| `NOTEBOOK_API` | 24 | Rendering, normalization, diagnostics, and notebook helpers |
| `TRACE_API` | 1 | Trace schema version |
| `LINEAGE_API` | 4 | Lineage records and factory |
| `NAMESPACE_API` | 3 | `core`, `providers`, and `integrations` namespaces |
| `ADVANCED_API` | 109 | Deduplicated union of the public groups |
| `PUBLIC_API` | 110 | `ADVANCED_API` plus `__version__` |

The 38 recommended symbols are:

```text
tool, skill, agent, system, graph, environment, eval, runtime, scheduler,
output_schema, final_answer, normalize_output, Tool, Agent, RunResult,
LineageMemory, LineageStep, lineage_memory, LINEAGE_SCHEMA_VERSION,
AgentContract, ContractPolicySpec, RunPolicy, validate_contract_policy,
AUTO_PROVIDER_ENV_VAR, DEFAULT_AUTO_PROVIDER_PRIORITY, RuntimeConfig,
normalize_provider_priority, resolve_auto_provider, SchedulerConfig,
OutputSchema, human_result, load_skill, Skill, LoadedSkill, expect, core,
providers, integrations

The tier constants themselves are maintainer API in `agentic_systems.api`; they
are not top-level exports. Documentation and tests must not imply that
`toolkit.PUBLIC_API` or `toolkit.RECOMMENDED_API` exists.

## Concept Map

| Grammar concept | Current public API | Primary implementation | Current semantics |
|---|---|---|---|
| Capability | `Tool`, `tool` | `tools/tool.py`, `tools/decorators.py` | Portable callable wrapper with scoped `identity`, optional Pydantic contracts, and `RunResult` execution. |
| Operational knowledge | `Skill`, `LoadedSkill`, `load_skill` | `skills/skill.py`, skill loader modules | Runtime packages compose through `Skill.compose`; filesystem-loaded packages remain a separate compatible object model. |
| Actor | `Agent`, `agent` | `agents.py`, `factories.py` | Portable configuration/execution facade; the factory creates an internal `AgenticSystem`. |
| Composition/governance | `AgenticSystem` | `system.py` | Registry and factory with explicit `error`/`keep`/`replace` conflict policy and inspectable provenance. |
| Explicit state/composition | `graph`, `agent_node`; advanced graph classes | `integrations/langgraph.py`, `environments.py`, `graphs/` | Thin LangGraph facade plus specialized graph implementations. |
| Episodic interaction | `AgenticEnvironment`, `EnvironmentTransition` | `environments.py` | Gymnasium-shaped, record-driven episodes backed by an invokable graph. |
| Verification | `run_eval`, `Evaluator`, `EvalReport`, `EvalReproducibility`, `EvalCaseResult` | `evals.py` | Batch execution with case checks, scoring, aggregate invariants, and explicit replay classification. |
| Execution result | `RunResult` | `results.py` | Shared envelope for tool and agent execution; carries answer, evidence, events, usage, validation, errors, trace, and metadata. |
| Execution selection | `runtime`, `RuntimeConfig` | `factories.py`, `core/runtime.py` | Declarative provider selection, including environment-based `auto` resolution. |
| Execution limits | `scheduler`, `SchedulerConfig`, `RunPolicy` | `factories.py`, `core/scheduler.py`, `contracts.py` | Timeout/retry/concurrency configuration merged with per-run policy. |
| Provider | provider names and namespace | `providers/`, `engines/` | Backend/model and deterministic execution paths selected through canonical engine names. |
| Framework adapter | `graph`, `agent_node`, `integrations` | `integrations/` | Optional adapters; `framework` is also stored on `Agent`. |
| Contract | `AgentContract`, `RunPolicy`, validation helpers | `contracts.py`, `results.py` | Pre-run policy plus post-run evidence/output validation. |
| Observation | `RunResult`, lineage, human output, `inspect` | `results.py`, `lineage.py`, `human_output.py`, `system.py` | Structured evidence plus human-oriented projection and diagnostics. |

## Composition Paths

The currently supported conceptual path is:

```text
callable -> Tool -> Skill -> Agent -> AgenticSystem
                              |             |
                              v             v
                           RunResult      Graph
                                            |
                                            v
                                      Environment -> EvalReport
```

`Skill.compose(...)` is an ordinary API composition step: it combines packages
without adding execution semantics. Conflicts default to errors; explicit `keep`
or `replace` decisions are ordered and inspectable.

This is not a single uniform return-type pipeline. Tools and agents return
`RunResult`; graphs return framework state; environments return Gymnasium tuples;
evaluations return `EvalReport`. The 1.1 grammar should define the adapters and
observation laws between these boundaries instead of claiming identical return
types.

## Known Mapping Gaps

| Desired concept | Current state | Audit disposition |
|---|---|---|
| Effects | No first-class tool effect descriptor | Specify before implementing. |
| Determinism | Eval replay is classified; Provider behavior remains capability-dependent | Preserve explicit `deterministic`, `seeded`, and `non_deterministic` conditions. |
| Execution requirements | Provider config, optional dependencies, and Tool async metadata remain distributed | Keep ownership local and expose requirements through profiles and inspection. |
| Evidence | Governed by RunResult invariants, lineage derivation, and Eval report contracts | Do not add a second evidence envelope. |
| Execution context | Conceptual union across existing owners | Checkpoint 1.1.7 confirms no public or internal aggregate object; see ADR 0009. |
| Degradation | Provider/Framework profiles and static inspection expose declared risks | Do not infer live availability from static declarations. |
| Substitution | Shared conformance fixtures validate the common observable contract | Do not promise equivalent model outputs or optional capabilities. |

## Compatibility Anchors

The following are compatibility constraints for 1.1 work:

- Preserve `import agentic_systems as toolkit` and the existing top-level names.
- Preserve `Tool.run` and `Agent.run` returning `RunResult`.
- Preserve `AgenticEnvironment.step` as a Gymnasium-shaped tuple.
- Preserve optional imports for providers and frameworks.
- Preserve canonical provider names and `provider="auto"` observability.
- Preserve direct `Skill` and filesystem `LoadedSkill` workflows until a tested
  migration or unification strategy exists.
- Treat `engines/` as internal even though engine names are public.

## Normative Closure

The 1.1 candidate is governed by:

1. `COMPUTATIONAL_GRAMMAR.md` and `SEMANTICS.md`;
2. `RUNRESULT_INVARIANTS.md` and `COMPOSITION_LAWS.md`;
3. Provider, Framework/Graph, System/Environment/Eval, Execution Context, and
   Static Inspection contracts;
4. ADRs 0005 through 0010;
5. executable contract tests and the release evidence matrix.

## Checkpoint 1.1.4 Provider Contract Map

| Grammar role | Public advanced API | Implementation | Observable contract |
|---|---|---|---|
| Provider capability | `CapabilityDeclaration` | `providers/conformance.py` | Required or optional status with a normative detail. |
| Provider profile | `ProviderProfile`, `provider_profile`, `provider_profiles` | `providers/conformance.py` and adapter `profile()` methods | Immutable, JSON-serializable capability declaration. |
| Provider conformance | `ProviderConformanceReport`, `evaluate_provider_conformance` | `providers/conformance.py` | Common success/failure checks over normalized `RunResult`. |
| Required capability vocabulary | `REQUIRED_PROVIDER_CAPABILITIES` | `providers/conformance.py` | Base substitution requirements shared by all canonical Providers. |
| Optional capability vocabulary | `OPTIONAL_PROVIDER_CAPABILITIES` | `providers/conformance.py` | Explicit supported, degraded, or unsupported operational differences. |

These symbols live in `agentic_systems.providers`; they are advanced adapter API
and are intentionally not added to the recommended top-level grammar.

## Checkpoint 1.1.5 Framework Boundary Map

| Boundary role | Advanced API | Implementation | Meaning |
|---|---|---|---|
| Framework declaration | `FrameworkProfile`, `framework_profile`, `framework_profiles` | `integrations/boundary.py` | Distinguishes real adapter, style-only, and declarative-only identities. |
| Graph boundary | `GraphBoundary`, `describe_graph_boundary` | `integrations/boundary.py` plus Graph class attributes | Distinguishes portable Agentic Systems Graphs from framework-native wrappers. |
| Projection conformance | `FrameworkProjectionReport`, `evaluate_framework_projection` | `integrations/boundary.py` | Verifies preserved RunResult fields in explicit Framework state projection. |
| Portable Graph | `AgentStepGraph`, `DynamicAgentRouterGraph`, `PlannedAgentGraph` | `environments.py` | Framework-independent `invoke(state)` adapters for episodes. |
| LangGraph facade | `graph`, `agent_node`, `GraphApp`, `AgenticGraph`, LangGraph builders | `integrations/langgraph.py` | Optional framework-native nodes, state graphs, compilation, and native access. |
| Declarative identities | `openai-agents`, `strands` constants and Agent configuration | `engines/names.py`, `agents.py` | Compatibility metadata only; no external SDK adapter in 1.1.5. |

## Checkpoint 1.1.6 Lifecycle And Eval Map

| Boundary | Public API | Owner |
|---|---|---|
| Composition state | `AgenticSystem`, `composition`, `inspect` | System instance |
| Transition state | Graph `invoke(state)` APIs | Graph/native Framework runtime |
| Episode state | `AgenticEnvironment`, `EnvironmentTransition`, `seed`, `rng` | Environment instance |
| Verification state | `EvalCaseResult`, `EvalReport`, `EvalReproducibility` | Eval definition/report |

Normative replay conditions and aggregate invariants are in
`SYSTEM_ENVIRONMENT_EVAL_SEMANTICS.md`.

## Checkpoint 1.1.7 Execution Context Map

| Resolved concern | Existing API owner |
|---|---|
| Provider/model/scheduler configuration | `RuntimeConfig` |
| Capability composition and Agent binding | `AgenticSystem` |
| Per-run limits and behavior | `RunPolicy` |
| Transition and episode state | Graph / `AgenticEnvironment` |
| Correlation and execution evidence | `RunResult` |

No `ExecutionContext` symbol is added. `PUBLIC_API` remains 105 symbols and no
existing owner, signature, schema, or return shape changes. The normative
decision is `EXECUTION_CONTEXT_DECISION.md`.

## Checkpoint 1.1.8 Static Inspection Map

| Inspection role | Public API / field | Source |
|---|---|---|
| System projection | `AgenticSystem.inspect()` | `system.py` |
| Structured and human report | `InspectReport`, `to_dict()`, `human_text()` | `inspection.py` |
| Registered definitions | `entities`, `relationships`, `contracts` | System registries and composition history |
| Adapter declarations | `providers`, `frameworks`, `capabilities` | Static conformance profiles |
| Actionable analysis | `conflicts`, `limits`, `degradation_risks`, `diagnostics` | Static report builder |

Inspection adds one public symbol. `PUBLIC_API` changes from 105 to 106 without
removing names or changing the legacy dictionary fields returned by `inspect()`.
The normative contract is `STATIC_SYSTEM_INSPECTION.md`.
