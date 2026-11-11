# Information and resource lifetime · 2.1.8

| Resource | Role | Lifetime |
|---|---|---|
| Graph State | Current business channels | Current computation |
| Context.data / sources | Detached domain information and source identifiers | Declared snapshot, inherited into execution |
| Context.lineage | Compact preceding evidence available at that point | Current execution scope |
| Memory / Context.episodes | Bounded previous episodes and their observations | Memory instance in the current process |
| Borrowed Boto3 session | Live provider resource | Owned by the application, process-local |
| Continuation | Paused compiled execution | Same compiled object and process |

Tools/functions request `*, context: toolkit.Context`. Returned Context data is a detached copy, not mutable shared graph state. Parent and local domain keys must agree when overlapping; conflicts fail instead of silently overriding. Sources are combined. Preceding lineage observations are bounded, not a complete durable event store.

Attach Memory(capacity=...) to an Agent, System or Environment. The execution reads a snapshot at entry and records its outcome; avoid redundant manual remember calls. Successful and failed outcomes are observations, not learned truths. Reuse the same instance for continuity; a child does not automatically receive a new independent memory. Eval isolates toolkit Memory per case while preserving progress within that case.

## Executable example

[Lineage and Memory](../examples/lineage_memory/example.py) defines a payment policy in Context on a System, inherited by two agents. The first execution approves a payment; the second detects its previous approval through context.episodes and requests duplicate review. It also verifies the current fee against preceding lineage. Run it from the repository root:

```bash
python scripts/run_example.py examples/lineage_memory/example.py
```

Context can supply policies, retrieved documents or preferences in model-backed applications. Keep actual business enforcement in Tools/contracts. A Tool can consume context.data and return only the relevant result/source to the actor; this is distinct from exposing all context as model instructions. Verify each adapter's projection rather than assuming arbitrary Context values become a system prompt. Retrieval is supplied by the application/Tools; Context does not automatically perform RAG.

Do not put clients or credentials in State, Context or Memory. A Bedrock runtime can borrow a session, excluded from serialized configuration. Export configuration JSON, create a local session in the destination process and inject it there. The JSON does not transfer a Session or its credentials. A common role is not a common Python object. [AWS contract](ADA_214.md), [historical verified scope](AWS_SESSION_VALIDATION_217.md).
