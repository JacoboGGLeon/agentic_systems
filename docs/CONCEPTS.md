# Concepts and composition · 2.1.8

A Tool executes a concrete operation. A runtime Skill groups Tools and instructions. Neither requires a model.

| Element | Responsibility | Use when |
|---|---|---|
| Agent(graph=...) | Explicit capability workflow | You control the sequence and decisions |
| Agent(runtime=...) | Actor execution with an optional framework | An actor selects or executes a capability |
| System(graph=...) | Application coordination | Several responsibilities belong to one application |
| Environment(graph=..., records=...) | Episodic execution with observe/update/stop | Work evolves across records |
| Eval(unit=..., cases=...) | Acceptance of an Agent, System or Environment | You need observable checks |

An Agent accepts graph OR runtime, not both. Graph is LangGraph's original StateGraph exposed as toolkit.Graph. It does not default to a Python provider. Python functions execute Python; actor nodes use their declared runtimes. A single graph can mix both.

A graph node may be an Agent or System containing another graph. This is nested composition: the outer graph coordinates units and each unit owns its internal steps. You do not need every layer. An Environment's graph describes work per episode; records/observe/update/stop govern the episode cycle. Eval can target an Agent or System without an Environment.

Framework and provider are different: native/OpenAI Agents/Strands implement actors; runtime configures Python or model-provider execution. LangGraph orchestrates graph topology.

[Graphs](GRAPHS.md) · [Execution](EXECUTION.md) · [Information](CONTEXT_MEMORY.md)
