# Concepts and composition · Agentic Systems 2.1.9

Start with an operation you can execute and check. A Tool owns that operation; a runtime Skill groups Tools and capability instructions. Neither needs a language model.

## Two Agent roles

| Declaration | Role | Use when |
|---|---|---|
| `Agent(graph=...)` | **Graph-based agent actuator** | You declare the execution route and decisions |
| `Agent(runtime=...)` | **Model-backed agent actor**, when using a model runtime | A model selects actions from available capabilities |

Agent accepts graph OR runtime, not both. A Python runtime actor executes an explicitly selected Tool; it does not interpret natural language. Graph is LangGraph's original StateGraph exposed as `toolkit.Graph`. A graph-backed Agent does not select a global provider: its Python nodes execute Python, while each actor node uses its own Runtime and Framework.

## Compose only the responsibilities you need

A **System** coordinates capabilities through a Graph. Nodes can be functions, Tools, Agents or other Systems; nested results retain the observed child executions. Add an **Environment** when a graph needs records, accumulated episode state, update logic and a stopping rule. Add **Eval** independently when you need acceptance cases and checks. Neither requires the other, and neither is mandatory after System.

## Keep configuration and information distinct

| Object | Responsibility |
|---|---|
| Runtime | Provider, model and execution limits |
| Framework | Actor execution implementation: Native, OpenAI Agents or Strands |
| Context | Immutable finite reference data and source identifiers |
| Memory | Bounded previous execution observations within a process |
| Graph state | Current business channels and updates |
| RunResult | Outputs, errors, usage, Tool events and nested execution evidence |

LangGraph orchestrates graph topology. Supporting a provider/framework configuration does not establish universal feature parity. Use the appropriate integration guide and evaluate the actual profile.

[Graphs](GRAPHS.md) · [Execution](EXECUTION.md) · [Information](CONTEXT_MEMORY.md) · [Evaluation](EVALUATION.md).
