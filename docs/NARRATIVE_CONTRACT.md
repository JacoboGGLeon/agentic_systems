# Narrative Contract

Agentic Systems is a computational grammar for composing deterministic
capabilities and language-model reasoning into systems whose execution can be
inspected, evaluated and reproduced as evidence.

This document is the editorial contract for the README, tutorials, Studio,
CLI, API reference, tests and release bundles. Those surfaces may teach at
different depths, but they must describe the same product.

## The Grammar

Agentic Systems has three related views. They must not be flattened into one
conveyor belt.

```text
Computation: Tool -> Skill -> Agent -> System
Time:        Environment -> Episode -> Step
Evidence:    Eval -> observes Agent, System or Episode
```

- A **Tool** is an executable capability.
- A **Skill** packages tools, instructions and contracts for runtime use.
- An **Agent** transforms context into actions and answers.
- A **System** composes agents and graphs into coordinated behavior.
- An **Environment** supplies the world and records iterative episodes.
- An **Eval** measures claims against deterministic evidence and, when used,
  judge evidence. It does not become another execution stage.

Graph is an orchestration structure owned by a System. Provider and Framework
are execution choices. MCP and A2A are integration protocols. None of them
replaces a node in the grammar.

## Two Operating Paths

The same grammar supports two operational patterns.

```text
Fast path:
user -> online Agent -> live Tool or Agent collaboration -> answer

Deliberative path:
user -> client Agent -> offline System/Graph -> augmented evidence -> answer
```

The fast path favors interactive work and direct collaboration. The
deliberative path favors bounded processing, data augmentation, review and
durable evidence. A product may use either path or combine them.

These names describe system topology and operating latency. They are not a
claim that the library implements a psychological model of human cognition.

## Execution Choices

The canonical Providers are `python-runtime`, `openai-runtime`,
`ollama-runtime`, `bedrock-runtime` and `vllm-runtime`. `auto` is a selection
mode, not a sixth Provider.

The canonical Frameworks are `native`, `langgraph`, `openai-agents` and
`strands`.

Provider answers where inference runs. Framework answers who owns the Agent
loop. The application grammar and normalized `RunResult` contract remain
stable across those choices, while wording, latency, token accounting and
vendor-specific capabilities may differ.

## Evidence Before Claims

Every public claim must identify its evidence boundary:

```text
declared -> configured -> ready -> executed -> semantically certified
```

Static compatibility is not live verification. A successful tool call is not
semantic certification. Missing SDK metrics remain absent; they are never
invented. Python is identified as a deterministic control, not presented as a
language model. Fallbacks, retries and degraded capabilities remain visible.

## Mirror Rule

The public surfaces are mirrors of one contract:

```text
Source/API -> Docs -> Tutorials/Studio -> Tests -> Release evidence
```

- The source registry owns canonical Provider and Framework identities.
- The API reference owns public names and signatures.
- Documentation explains boundaries and supported behavior.
- Tutorials and Studio demonstrate only public, supported behavior.
- Tests gate mechanically verifiable claims.
- Release attestations bind live claims to one commit and wheel hash.

Generated references and attestations may be terse. Teaching and product
narratives should be direct, graceful and useful, but never compensate for
missing evidence with promotional language.
