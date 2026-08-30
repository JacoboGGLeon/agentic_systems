# Semantic challenges

This directory is the canonical home for tests that certify **meaning and
execution paths**, not merely `ok=true`.

Semantic challenges are different from:

- `tests/`: fast unit, contract, integration, and release regressions;
- `tutorials/`: progressive teaching material;
- `studio/`: the conversational demonstration application;
- `scripts/run_semantic_matrix.py`: the broad provider × framework release gate.

Every challenge owns a manifest, narrative, runnable application, deterministic
checks, live attestation, and a human review. A challenge passes only when its
answer, lineage, runtime identity, protocol evidence, and eval judgment agree.

## Catalog

| Challenge | Purpose | Runtime matrix |
|---|---|---|
| [`strands_protocol_graph`](strands_protocol_graph/README.md) | Real Strands MCP + A2A, System-owned LangGraph orchestration, AgenticEnvironment/Eval, and a native deterministic judge | OpenAI, Bedrock, Ollama locally; vLLM and Bedrock IAM externally |
| [Semantic E2E matrix](../docs/semantic-certification.md) | Skill -> specialist -> orchestrator -> judge across Provider/Framework combinations | Python + four LM Providers x four Frameworks |

## Evidence policy

Generated attestations are immutable release evidence and are not source code.
They belong under the bundle's `outputs/` directory. Secrets, native SDK objects,
and private reasoning are never persisted.
