# Grammar To API Map

Status: Checkpoint 1.1.0 audit baseline for Agentic Systems 1.0.7.

This document maps the 1.1 computational grammar to the current implementation.
It is descriptive, not yet normative. Normative semantics and composition laws
belong to later checkpoints.

## Public Surface Baseline

The supported import remains:

```python
import agentic_systems as toolkit
```

`src/agentic_systems/api.py` defines the public inventory and
`src/agentic_systems/__init__.py` exports every name in `PUBLIC_API`.

| API group | Symbols | Role |
|---|---:|---|
| `RECOMMENDED_API` | 33 | Names intended for first-use documentation |
| `CORE_API` | 49 | Core factories, contracts, results, output, and composition objects |
| `BEDROCK_PRIMITIVE_API` | 2 | Direct Bedrock primitives |
| `CHAIN_API` | 2 | Sequential composition helpers |
| `ENGINE_API` | 7 | Canonical engine names and normalization |
| `INTEGRATION_API` | 2 | Recommended graph integration entry points |
| `EVAL_API` | 4 | Evaluation cases, evaluator, report, and runner |
| `ENVIRONMENT_API` | 9 | Episodic environment and specialized graph helpers |
| `NOTEBOOK_API` | 24 | Rendering, normalization, diagnostics, and notebook helpers |
| `TRACE_API` | 1 | Trace schema version |
| `LINEAGE_API` | 4 | Lineage records and factory |
| `NAMESPACE_API` | 3 | `core`, `providers`, and `integrations` namespaces |
| `ADVANCED_API` | 103 | Deduplicated union of the public groups |
| `PUBLIC_API` | 104 | `ADVANCED_API` plus `__version__` |

The 33 recommended symbols are:

```text
agent, runtime, scheduler, output_schema, final_answer, normalize_output,
tool, Tool, Agent, RunResult, LineageMemory, LineageStep, lineage_memory,
LINEAGE_SCHEMA_VERSION, AgentContract, ContractPolicySpec, RunPolicy,
validate_contract_policy, AUTO_PROVIDER_ENV_VAR,
DEFAULT_AUTO_PROVIDER_PRIORITY, RuntimeConfig, normalize_provider_priority,
resolve_auto_provider, SchedulerConfig, OutputSchema, human_result, load_skill,
Skill, LoadedSkill, expect, core, providers, integrations
```

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
| Verification | `run_eval`, `Evaluator`, `EvalReport`, `EvalCaseResult` | `evals.py` | Batch agent/environment execution with case checks and scoring. |
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
| Determinism | Inferred mainly from provider/engine identity | Add a semantic field only after use cases and compatibility are defined. |
| Execution requirements | Scattered across provider config, optional dependencies, and tool async metadata | Model conceptually first. |
| Evidence | Present in `RunResult.data`, tool events, trace, and lineage, but not governed by one invariant | Define evidence ownership and consistency laws. |
| Execution context | Implicit across input, runtime config, scheduler, mode, graph state, environment memory, and metadata | Do not add a public class in 1.1.0. |
| Degradation | Implemented through fallback and structured failures in several paths | Define a common observable rule before adding API. |
| Substitution | Provider selection exists; behavioral equivalence is not tested as a law | Add conformance fixtures in later checkpoints. |

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

## Next Normative Work

Later checkpoints should turn this descriptive map into:

1. `COMPUTATIONAL_GRAMMAR.md`: syntax, categories, and legal compositions.
2. `SEMANTICS.md`: identity, ownership, state, effects, evidence, and failures.
3. `COMPOSITION_LAWS.md`: executable invariants and substitution laws.
4. ADRs for result, context, provider/framework, skill, graph, and environment
   decisions that cannot be derived from backward compatibility alone.

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
