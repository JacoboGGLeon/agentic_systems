# Semantic certification

Agentic Systems has a dedicated semantic-certification layer. Structural smoke
tests answer “did something run?”; semantic challenges answer “did the complete
Agentic System do the right work, through the declared route, and explain the
right result?”

## Layers

1. **Contract tests** validate schemas, adapters, invariants, and error paths.
2. **Broad semantic matrix** exercises Skill, Agent, System, Environment, Eval,
   deterministic validation, and judge behavior across providers/frameworks.
3. **Focused semantic challenges** combine difficult native capabilities such as
   MCP, A2A, and LangGraph and retain full human-readable evidence.
4. **Studio** demonstrates a user application. It is deliberately not treated as
   a release attestation.

## Required evidence

Each focused challenge records:

- exact provider, framework, model, commit, and wheel hash when supplied;
- public `human_result` output;
- hierarchical `RunResult` lineage;
- exact Tool and protocol evidence;
- deterministic validation and judge verdict;
- observed usage only (unknown values are not fabricated);
- retries, fallback state, and invariant results.

An `ok=true` value alone never certifies a challenge. The runner applies an
independent semantic review and the validator rejects incomplete cells.

## Current challenge

See [`semantic_challenges/strands_protocol_graph`](../semantic_challenges/strands_protocol_graph/README.md).
It runs a Strands Agent that must call one real MCP Tool and one real A2A Agent,
inside a System-owned LangGraph. `Evaluator` executes that graph inside an
`AgenticEnvironment`, and a Python/native judge certifies the public answer and
the complete execution path.
