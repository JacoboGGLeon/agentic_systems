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

`GraphApp`, `AgenticGraph`, and the LangGraph builders are optional integration
objects. Their state model, compilation, and lifecycle belong to LangGraph and
declare `graph_kind="framework-native"` where wrapped.

Only LangGraph has an SDK adapter. `openai-agents` is style-only and `strands` is
declarative-only in the current package.
