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

An ok=true value alone never certifies a challenge. The runner applies an
independent semantic review and the validator rejects incomplete cells.

## Judge budgets

Judge limits are derived from their declared Tool contract through
ContractExecutionBudget; they are not selected per provider or framework.
The default reserves one decision turn, one turn per required Tool, one
finalization turn, protocol overhead, and a safety margin. A valid certification
Tool event completes the contract early, so the ceiling does not force extra
model calls.

AGENTIC_SYSTEMS_SEMANTIC_JUDGE_MAX_TURNS is an optional .env override. If it is
below the contract-derived minimum, preflight fails before any live request.
AGENTIC_SYSTEMS_SEMANTIC_JUDGE_MAX_TOKENS remains the independent token cap.

## Current challenge

See [`semantic_challenges/strands_protocol_graph`](../semantic_challenges/strands_protocol_graph/README.md).
It runs a Strands Agent that must call one real MCP Tool and one real A2A Agent,
inside a System-owned LangGraph. `Evaluator` executes that graph inside an
`AgenticEnvironment`, and a Python/native judge certifies the public answer and
the complete execution path.

## Certified 2.1 release evidence

The final 2.1 gate covers all 20 canonical Provider x Framework routes. The
primary matrix passed 76/76 semantic episodes. Bedrock's AWS credential-chain
route passed another 16/16 episodes in SageMaker and was independently repeated
16/16 in the ADA enterprise sandbox, for 108/108 manually reviewed episodes in
total. Review includes the public answer and complete lineage; `ok=true` alone
is never sufficient.

The downloadable `final-certification-summary.json` records the exact wheel
hash, source identity, evidence filenames and hashes. The release workflow
verifies that summary and every public artifact against
`SHA256SUMS-2.1.0.txt` before publishing the Python distributions.
