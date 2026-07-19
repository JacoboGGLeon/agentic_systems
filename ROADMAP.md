# Agentic Systems Roadmap

## Release Candidate 1.1

The current repository candidate is `1.1.0rc1`.

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

## Promotion Gate

The candidate is not a final release until automated package gates and the
manual notebook matrix in `docs/RELEASE_CANDIDATE_1_1.md` pass. External Provider
support is claimed only at the evidence level recorded there.
