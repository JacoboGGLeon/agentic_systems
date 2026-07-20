# Agentic Systems Roadmap

## Stable Release 1.1

The current repository release is `1.1.0`.

```text
src/agentic_systems/  package
tutorials/            18 canonical notebooks
docs/                 normative and operating documentation
tests/                API, contract, composition, integration, and release gates
```

## Closed 1.1 Checkpoints

```text
1.1.0 grammar audit
1.1.1 normative grammar and semantics
1.1.2 RunResult invariants
1.1.3 Tool and Skill composition
1.1.4 Runtime and Provider substitution
1.1.5 Framework and Graph boundary
1.1.6 Systems, Environments, and Evals
1.1.7 Execution Context decision
1.1.8 static System inspection
1.1.9 tutorials, migration, and release closure
```

## Runtime Boundary

Canonical Providers:

```text
python-runtime
bedrock-runtime
openai-runtime
vllm-runtime
auto
```

Framework status:

```text
langgraph       optional implemented adapter
openai-agents   style-only metadata
strands         declarative-only metadata
```

## Promotion Evidence

Automated package gates and the 18/18 manual notebook matrix passed. External
Provider support remains limited to the evidence recorded in
`docs/MANUAL_NOTEBOOK_MATRIX_1_1.md`.
