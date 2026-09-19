# Typed claim review: implementation and observed limits

This is an application-level experiment through the public toolkit, not a new
library API or an approved replacement for the long-scenario evaluator.

## Deterministic implementation

`verify_evidence_comparison` resolves a record ID and a typed path against an
application-owned snapshot. It compares the claimed JSON value without string
or boolean coercion. Missing records/paths yield unknown; observed differences
yield contradicted. Duplicate identities, ambiguous JSON and invalid paths are
rejected. A successful comparison Tool execution is distinct from whether the
claim is supported: an operation that failed can support a true description of
its failure.

`typed_claim_evaluator` uses two LLM agents to project and audit claims, then a
Python-runtime Agent executes the comparisons. Every stage retains its normalized
result and lineage. Text coverage, record identity and projection shape are
validated before comparisons; audit vetoes are not silently overridden. Pure
nonfactual text and unresolved relationships remain distinct. No tool names,
fixture numbers, provider identities or expected answers are special-cased.

This does NOT prove that natural-language extraction selected the correct field,
preserved a quantifier or covered every meaning. That boundary remains semantic.

## Preserved live experiments

All results below were inspected, including projections, audit decisions,
comparison outputs, references and errors. Cases were run once per experiment;
earlier failures were not overwritten. These are exposed regressions, not a
held-out certification set.

| Experiment | Route | Accepted | Requests |
| --- | --- | ---: | ---: |
| Typed v1: JSON inside a string; six cases | OpenAI/langgraph | 3/6 | 23 |
| Typed v1: JSON inside a string; six cases | Ollama/native | 0/6 | 18 |
| Typed v2: direct typed schema; three cases | OpenAI/langgraph | 1/3 | 10 |
| Typed v2: direct typed schema; three cases | Ollama/native | 0/3 | 7 |

V1 OpenAI passed mixed operation statuses, unsupported causality (unknown), and
fact/metaphor distinction, with correct citations. It produced malformed JSON
for distinct numeric values. The other two failures were audit vetoes on faithful
projections of false claims. A separate offline diagnostic confirmed that those
projections would be contradicted by the comparator; this does not turn the
original incomplete executions into passes.

V1 Ollama failed at projection in all six cases: five server-side invalid-tool-
argument errors and one invalid JSON tool argument. These are contract/transport
failures, not successful semantic rejections.

V2 changes only the projection tool boundary to a direct Pydantic input model;
the audit and acceptance criteria remain unchanged. Its three cases were mixed
statuses, reversed statuses and distinct numeric values. OpenAI passed mixed
statuses, incorrectly vetoed the faithful negative projection, and omitted the
second sentence from the numeric case. Ollama duplicated a quantified sentence
and dropped punctuation in the mixed case, emitted an invalid kind/comparison
combination in the negative case, and dropped punctuation in the numeric case.
The structural checks blocked these defects. They were not repaired or marked
approved. The absence of the earlier string-format failure in these selected
v2 calls is not full schema certification.

Artifacts remain outside the checkout under `work/typed-claim-regression-v1`
and `work/typed-claim-regression-v2`. Both v2 manifests were checked against all
99 recorded source hashes after execution: zero mismatches.

## Tests, budget and release status

- Latest contract/eval regression: 851 passed.
- Targeted typed-comparison, legacy comparison and acceptance checks: 76 passed.
- Ruff checks passed; `git diff --check` reported no whitespace errors.
- Added varied identifiers, Unicode field names, nested paths, missing/null,
  wrong JSON types, duplicate identities, malformed projections and audit vetoes.
- The four framework constructor/callback tests use controlled LLM stages and
  real Python comparison execution; they are not four live framework passes.

The two pilots consumed 58 new requests. Cumulative budgets are OpenAI/langgraph
288/300 (12 left), Ollama/native 281/300 (19 left), Bedrock/native 300/300 (none).
Bedrock was not called. Monetary reservations remain below USD 5 per route;
they are not actual billing. No allocation was reset or transferred.

The deterministic comparison layer is implemented and tested. Reliable complete
extraction and a faithful audit remain unresolved. Do not widen the live matrix,
replace the current long-scenario evaluator, claim 100% semantic success, or
close 2.1.2 based on this experiment. Any subsequent independent acceptance must
use a new frozen set and retain these failures.
