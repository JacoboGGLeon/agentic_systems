# Computational model · Agentic Systems 2.1.9

Define operations as Tools and reusable capability groups as Skills. An Agent owns either a Graph or a Runtime-backed actor, not both. A System coordinates graph nodes; an Environment adds records and episode transitions; Eval executes independent acceptance cases.

Graph is the public LangGraph builder. State carries current business values. Context supplies immutable references, Memory supplies bounded history, and RunResult retains data and observed execution evidence. These objects serve different responsibilities rather than mandatory sequential layers.

[Concepts](CONCEPTS.md) · [Graphs](GRAPHS.md) · [Context and Memory](CONTEXT_MEMORY.md) · [Evaluation](EVALUATION.md).
