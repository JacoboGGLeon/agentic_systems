# Conceptual model

The public model has two orthogonal dimensions: computation and time.

Computation hierarchy:

    Tool -> runtime Skill -> Agent -> System

A Tool computes deterministically. A runtime Skill is a reusable capability
package. An Agent is one autonomous or deterministic computation unit and may
own an internal pipeline. A System owns external composition: sequential,
parallel, graph, routing or later compositional algebra. A one-agent System is
valid, but the identities remain different because the System defines the
boundary and execution plan.

Time hierarchy:

    Environment -> Episode -> Step

A step can represent a conversation turn, simulation tick, workflow stage,
round-robin turn or bounded subprocess. Environments do not replace Systems;
they feed and observe them through time.

Evaluation can target an Agent or System directly. It can also evaluate
behavior across Environment episodes. Preserve both the target identity and
episode/step lineage.

Every executable boundary returns RunResult. Framework-specific raw objects may
be retained in raw_responses, but callers should consume normalized text, data,
messages, tool_events, usage, children and metadata.
