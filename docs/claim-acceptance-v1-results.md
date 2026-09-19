# Claim partition audit and first held-out sample

This is a source experiment, not release certification. Credentials were loaded
from the canonical .env without recording secrets. Existing per-route allocations
were not reset. The executable application was frozen during each live batch.

## Changes

`claim-review-v2` requests complete clauses/sentences, not short word fragments.
An additional toolkit agent audits semantic boundary coherence before any contrast
calls. A failed audit stops review. Deterministic text coverage still applies;
the audit is a model judgment and is NOT a proof of semantic completeness.
No provider-specific prompts, model-name branches or keyword repairs were added.

Two offline pipeline tests verify that an audit rejection prevents contrast calls,
and that an accepted audit proceeds to contrast and the separate clarity review.

## Calibration: claim-pilot-v3

The original positive/negative pair completed in Bedrock/native,
OpenAI/langgraph and Ollama/native, 12 requests per case (72 total).
Manual review found three coherent fragments in each answer, distinguishing
the numeric result from the two false execution assertions. Bedrock no longer
split the poem word by word in this sample. This does not invalidate prior failures.

## Held-out: claim-acceptance-v1

Fixture `tests/fixtures/claim_acceptance_v1.json` was fixed before execution and
was not used to modify the evaluator. Each of six cases ran once per route.
Artifacts: `../claim-acceptance-v1/<provider>/<framework>/`, with manifests,
source hashes, source fragments, per-stage RunResults and lineage.

| Route | Expected verdicts matched | Requests |
|---|---:|---:|
| Bedrock/native | 6/6 | 90 |
| OpenAI/langgraph | 5/6 | 60 |
| Ollama/native | 5/6 | 56 |

The counts above are verdict matches, NOT complete manual acceptance:

- OpenAI/langgraph falsely supports an assertion that a lookup caused an export
  timeout. The records establish results and a timeout, not causality.
- Ollama/native labels that causal claim contradicted. The correct classification
  is unknown: absence of causal evidence is not evidence that the claim is false.
- In Ollama's partial-success case, the verdict is correct but the combined fragment
  includes the export failure while its references include only the lookups.
  This is an additional reference-completeness failure discovered by reading output.
- Bedrock produced the expected distinctions, including unknown for missing causal
  evidence. Some references are broader than necessary, notably metaphor records;
  do not represent those references as factual support for figurative language.

Unknown matches the explicit insufficient-evidence test only; it never approves
the candidate answer. All eighteen stage pipelines completed, so the remaining
failures are not missing credentials or unavailable services.

## Gates still open

Do not expand these results into a 16/16 or 100% claim. Causal entailment versus
contradiction, and reference completeness for multi-assertion fragments, remain
unresolved. Any further change must preserve this sample's failures and use a
new acceptance sample; do not retune and relabel this one as held-out.

Regression check: 765 contract/eval tests passed; the changed files passed lint.
Full distribution, coverage and release provenance gates were not run here.

## Long case with the new claim evaluator

`../long-claim-evals-v1/openai-runtime/openai-agents/` evaluates the saved original
seven-step candidate, not regenerated answers. Original answers: 7/7 accepted;
explicit false-failure answers: 7/7 rejected. All deterministic evidence checks
remained true. Judge stage executions and lineage are retained separately.
There were 70 requests for the originals and 60 for the negatives; the route
finished at 219/300 cumulative requests with USD 1.11235 conservatively reserved,
not a billing measurement. No budget reset or balance transfer.

Manual review checked each factual original against its cited operation_10 event,
and each false failure assertion against successful events. The prior invented
increment-by-five explanation cannot arise from the fixed evidence rendering.
However, six nonfactual courtesy fragments carry irrelevant tool references.
These must not be advertised as supporting evidence for those fragments.
Therefore correct 14/14 binary decisions are not complete citation-quality
certification. Candidate remains eight Python operators plus one LLM operator;
this is one route, not the full long-case matrix.
