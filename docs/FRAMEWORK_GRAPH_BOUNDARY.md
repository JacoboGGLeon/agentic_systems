# Framework and Graph Boundary

Status: normative for Checkpoint 1.1.5.

This document defines which semantics belong to Agentic Systems and which
belong to an external orchestration framework. It also distinguishes portable
Agentic Systems Graphs from framework-native Graph objects.

## Ownership Boundary

Agentic Systems owns:

- Tool, Skill, Agent, Contract, Policy, RunResult, evidence, and validation;
- Provider selection and canonical runtime identity;
- portable Agent-to-state and RunResult-to-state projection rules;
- the internal Graph adapters used by AgenticEnvironment;
- framework profiles and explicit requested/actual adapter metadata.

An external Framework owns:

- its native state model, node and edge registration, compilation, lifecycle,
  persistence, streaming, and framework-native callbacks;
- native object types and errors that are not normalized by a thin adapter;
- behavior invoked directly through its exposed native object.

A Framework adapter MUST NOT redefine Tool, Agent, Contract, or RunResult. It
MAY project those objects into framework state, but required evidence must
remain available through explicit state keys.

## Implemented Integration Status

| Identity | Status | What executes |
|---|---|---|
| `langgraph` | `native-adapter` | `agentic_systems.integrations.langgraph` builds nodes, StateGraph objects, and compiled LangGraph apps. |
| `openai-agents` | `style-only` | Agentic Systems Providers execute; no OpenAI Agents SDK adapter is included. |
| `strands` | `declarative-only` | The label is accepted for compatibility metadata; no Strands SDK adapter is included. |

The machine-readable source is `framework_profile(...)`. A caller that requires
an external adapter must validate it explicitly:

```python
from agentic_systems.integrations import framework_profile

framework_profile("langgraph").check(require_adapter=True).raise_if_failed()
framework_profile("strands").check(require_adapter=True).raise_if_failed()  # fails
```

Accepting a framework identity on `Agent` is not proof that its SDK executed.
Execution metadata separates:

- `framework`: backward-compatible requested label;
- `framework_requested`: explicit user configuration;
- `framework_adapter`: adapter that actually projected or orchestrated the run.

Direct Agent execution has `framework_adapter=None`. A LangGraph result
projection records `framework_adapter="langgraph"` in its serialized result.

## Graph Kinds

### Agentic Systems Native

`AgentStepGraph`, `DynamicAgentRouterGraph`, and `PlannedAgentGraph` are portable
internal Graph adapters. They expose `invoke(state)`, require no optional
framework dependency, and support Environment execution. Their boundary kind is
`agentic-systems-native` and `framework` is `None`.

They own portable transition and projection behavior. They do not claim
LangGraph compilation, persistence, or lifecycle semantics.

### Framework Native

`GraphApp`, `AgenticGraph`, `build_langgraph_agent_graph`,
`build_langgraph_planned_graph`, and `graph(...)` belong to the optional
LangGraph integration. Their native object or compiled return value belongs to
LangGraph. Wrapper objects declare `framework-native` and expose the native
object where applicable.

Despite its short name, public `graph(...)` is a LangGraph facade and currently
accepts only `engine="langgraph"`. It is not the portable Graph implementation.

## Result Projection Contract

Graph state is not RunResult. A Framework node may return a partial state update
instead of RunResult, but a conforming full-result projection preserves:

```text
ok
final
data
tool_events
usage
engine
model
mode
validation
errors
```

Callers that need the central contract MUST configure `result_key`. Compact
`trace` and human-facing output fields are additive projections; they are not
substitutes for the full serialized result.

`evaluate_framework_projection(...)` checks this contract for controlled
success evidence and reports named, JSON-serializable failures.

## Thin Adapter Rules

A Framework adapter is thin when it:

1. imports the optional SDK only at the integration call site;
2. maps explicit state to Agent input;
3. invokes the existing Agent API rather than reimplementing Provider logic;
4. projects RunResult without changing central fields;
5. exposes the native object for unsupported framework-specific behavior;
6. keeps framework exceptions native unless it explicitly normalizes them;
7. adds adapter metadata without pretending that requested and executed paths
   are the same.

## Non-Equivalence

This boundary does not promise framework substitution. A portable Graph and a
LangGraph app may share a state-transition contract while differing in
compilation, concurrency, persistence, retries, streaming, and lifecycle.

OpenAI runtime support is not OpenAI Agents SDK support. A Strands label is not
Strands execution. Those equivalences may be introduced only with real adapters,
profiles, tests, dependency declarations, and compatibility review.

## Counterexamples

- `RunResult` Tool evidence is replaced by rendered answer text in Graph state.
- `framework="strands"` produces `framework_adapter="strands"` without loading
  or invoking a Strands adapter.
- `vllm-runtime` is written into the Framework field.
- Core modules import LangGraph merely to create an Agent or RunResult.
- A facade reimplements Contract validation differently from `Agent.run`.
- A compiled LangGraph object is documented as the portable native Graph.
