# Architecture

Agentic Systems is organized around composable primitives and explicit runtime
boundaries.

## Mental Model

```text
Tool        executable capability
Skill       package of tools, instructions, contracts and assets
Agent       instructions + runtime + tools/skills + contracts
System      native container that registers and composes tools, skills and agents
Graph       state + nodes + edges orchestration
Environment episodic execution with reward and history
Eval        batch validation and scoring
```

Cross-cutting services:

```text
Runtime/Provider  where execution happens
Scheduler         execution limits, retry and timeout policy
Lineage Memory    compact explanation of what/how/why
Human Output      stable rendering for notebooks and CLI diagnostics
Contracts         declarative validation before and after execution
```

## Package Layout

```text
src/agentic_systems/       library package
docs/                      current API and operating docs
tutorials/                 executable learning path
tutorials/skills/          tutorial skills outside the library core
tests/                     regression and API contract tests
```

## Runtime Boundaries

```text
core          provider-agnostic primitives
providers     runtime/model access: python-runtime, bedrock-runtime, openai-runtime, vllm-runtime
integrations  optional LangGraph adapter plus framework/Graph boundary profiles
engines       internal execution implementation details
```

Rules:

```text
- Core imports must not require optional framework dependencies.
- Provider code owns model/backend calls. `vllm-runtime` owns only the OpenAI-compatible client call; the vLLM GPU server is external infrastructure.
- Integration code owns framework adaptation only; accepted framework labels without adapters remain declarative metadata.
- Business and tutorial assets stay outside src/agentic_systems.
- `provider="auto"` must resolve to one concrete provider before execution.
- New user code should not import from `agentic_systems.engines.*`.
```

## Output Flow

```text
tool/agent/system/graph/environment
        -> RunResult or state
        -> final/data/tool_events/usage/validation
        -> human_result or lineage_memory
```

`RunResult.final` is the user-facing answer. `RunResult.data` is reusable
evidence. `RunResult.tool_events`, `usage`, `validation` and `errors` remain in
the envelope.

## Notebook Flow

Tutorials should present output in this order:

```text
1. toolkit.human_result(...) or toolkit.show(...) for the human view
2. compact technical snapshot
3. raw object only when the API lesson needs it
```

The official tutorial route is `tutorials/*.ipynb` in numeric order.

## CLI Flow

The CLI is a diagnostics boundary:

```text
agentic-systems version
agentic-systems doctor
agentic-systems runtime
agentic-systems api
agentic-systems public-api
```

It must remain package-oriented. Do not add domain workflows to the CLI.

## Framework Boundary

`AgentStepGraph`, `DynamicAgentRouterGraph`, and `PlannedAgentGraph` are portable
Agentic Systems Graph adapters used by Environment execution. They require no
external framework and declare `graph_kind="agentic-systems-native"`.

`toolkit.graph(engine="auto")` returns a `GraphApp`. It uses native LangGraph
when installed and otherwise the dependency-free portable backend. The instance
declares `graph_kind="framework-native"` only for LangGraph and
`graph_kind="agentic-systems-native"` for the portable backend.

`AgenticGraph` and the explicit LangGraph builders always belong to the optional
framework integration and remain `framework-native`.

Only LangGraph has an SDK adapter. `openai-agents` is style-only and `strands` is
declarative-only in the current package.

## Lifecycle And Ownership

```text
System composition/configuration
        -> Graph transition state
        -> Environment episode state and evidence
        -> Eval case evidence and aggregation
```

The arrows describe data flow, not ownership transfer. Environment owns episode
seed and a local RNG; Graph owns transition topology; Eval owns checks and
reports. Replay conditions and report invariants are part of the
[Computational Model](COMPUTATIONAL_MODEL.md).

## Execution Resolution

Execution Context is the conceptual snapshot produced while resolving System
binding, input/mode, Runtime/Provider, policy, scheduler, state, and correlation
metadata. It is not another container in the package architecture. Existing
owners remain authoritative, and no ambient global or context-variable state is
introduced. See [Computational Model](COMPUTATIONAL_MODEL.md).

## Static Inspection Boundary

`AgenticSystem.inspect()` projects registered composition and declarative
configuration into an `InspectReport`. It may read local registries, contracts,
Provider profiles, Framework profiles, and composition history. It must not call
models or Tools, probe credentials, compile external Graphs, or import optional
Framework SDKs.

The report has one canonical structured representation and a stable human
projection. Diagnostics identify the affected entity, severity, code, message,
and suggested action. Runtime availability remains a declared risk until actual
execution; inspection does not claim behavioral conformance.

## Namespace Ownership

| Namespace | Owns | Must not own |
|---|---|---|
| `agentic_systems.core` | Provider-neutral contracts, results, scheduler and runtime configuration | SDK calls, framework compilation or business logic |
| `agentic_systems.providers` | Backend/model access for canonical Providers | Framework orchestration or tutorial workflows |
| `agentic_systems.integrations` | External Framework adapters and bridges | Core contracts or Provider implementation |
| `agentic_systems.engines` | Internal execution mechanisms | New user-facing API design |
| `tutorials/` | Executable public-API learning path | Library implementation |
| `docs/` | Current behavior, contracts and operating guidance | Historical checkpoints presented as recommended behavior |

Provider decides where execution happens. Integration adapts Agentic Systems to
an external Framework. LangGraph is an implemented integration; Strands and
OpenAI Agents-style are compatibility identities without SDK adapters.

## Placement Rules

1. Add to core only when behavior is Provider-independent.
2. Put backend/model behavior under providers.
3. Put real Framework adapters under integrations.
4. Keep optional SDKs lazy at base import time.
5. Keep domain teaching material in tutorials and outside package internals.
6. Keep the CLI diagnostic and package-oriented.
7. Document public behavior through `import agentic_systems as toolkit`.
