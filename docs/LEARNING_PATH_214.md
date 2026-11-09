# Learning path · Agentic Systems 2.1.5

Start with [one Tool and a visible result](ONBOARDING_FIRST_RUN.md). Continue
through [the core notebooks](../tutorials/README.md) in order, then select
[an example by task](../examples/README.md). Read data and assertions before
execution. Add each abstraction when it owns a distinct responsibility.

First inspect status, ok, data and human_results(). For debugging inspect errors,
invariants and lineage; for audit retain the complete serialized evidence.
A paused execution is not a final completed result even if ok is true.

Choose a provider and actor framework after the offline case works. LangGraph
already orchestrates the route. Handoffs, sessions, guardrails and MCP/A2A have
additional SDK-specific boundaries. Follow [actor contracts](ACTOR_CONTRACTS.md)
and [runtime controls](RUNTIME_SCHEDULER_214.md) before authorizing inference.
