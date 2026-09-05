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

The model judge certifies through one typed Tool call. Its Pydantic input requires
exactly one explicit pass/fail assessment, with public evidence, for every rubric
criterion. The Tool—not free-form model text—derives scores, findings, and the
overall verdict from that complete assessment set.

AGENTIC_SYSTEMS_SEMANTIC_JUDGE_MAX_TURNS is an optional .env override. If it is
below the contract-derived minimum, preflight fails before any live request.
AGENTIC_SYSTEMS_SEMANTIC_JUDGE_MAX_TOKENS remains the independent token cap. Its
portable default is 4096: this is a ceiling, not a request to consume that many
tokens, and it gives smaller reasoning-capable models enough room to reach the
required certification Tool without provider-specific branches.

## Current challenge

See [`semantic_challenges/strands_protocol_graph`](../semantic_challenges/strands_protocol_graph/README.md).
It runs a Strands Agent that must call one real MCP Tool and one real A2A Agent,
inside a System-owned LangGraph. `Evaluator` executes that graph inside an
`AgenticEnvironment`, and a Python/native judge certifies the public answer and
the complete execution path.

## Certified 2.1 release evidence

The final 2.1 gate covers the 20 canonical routes in the primary Provider x
Framework matrix and 76/76 primary semantic episodes. Bedrock's AWS
credential-chain route then passed the same four Framework routes and 16/16
episodes in AWS SageMaker and again in the ADA enterprise sandbox. The final
total is therefore 28/28 certified routes and 108/108 reviewed semantic
episodes, all using the same checksum-verified wheel. Review includes the
public answer and complete lineage; `ok=true` alone is never sufficient.

The downloadable `final-certification-summary.json` records the exact wheel
hash, certified runtime commit, release-assembly commit, core-tree equivalence,
evidence filenames and hashes. `scripts/build_release_certification.py`
constructs this summary from validated live artifacts; it is not edited by
hand. The release workflow verifies that summary and every public artifact
against `SHA256SUMS-2.1.2.txt` before publishing the Python distributions.
