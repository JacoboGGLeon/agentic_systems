# Claim evaluator: bounded calibration, not release certification

Application declaration: `scripts/claim_evaluator.py`. No library API additions.
Stages use public toolkit agents/tools: verbatim partition, per-fragment contrast,
independent clarity, deterministic aggregation. `claim_eval_adapter.py` connects
the application to the existing Eval judge interface for the long case.

## Guarantees and limits

Partition validation rejects omitted, invented or reordered non-whitespace text.
All fragments need exactly one review; evidence identities must be unique and
references valid. Supported/contradicted decisions need references. Any contradiction
fails grounding; unknown stays nonpassing. A nonfactual-only answer is inconclusive.
Records are rendered from copied evidence, not explanatory facts invented by a model.

These checks prove textual coverage and referential integrity, NOT semantic
atomicity, relevance or correctness. The returned `semantic_completeness_proven`
and `release_approved` fields remain false. A plausible cited model verdict is
not a proof. Clarity is separate from grounding.

## Pilot evidence

`../claim-pilot-v1/` preserves the application callback binding failure (18 requests).
The model returned usable partitions in the inspected Ollama case, but a callback
mistakenly expected the interior list instead of a Pydantic payload. This was an
application defect, not evidence of model incapacity. Offline callback regressions
were added before the separately named v2 run.

`../claim-pilot-v2/` freezes the unchanged application for three route pairs, using
the compact v3 source packets, one positive and one injected negative each.
Existing route allocations remain cumulative. A separate pilot cap is 40 requests
per route, within the existing 300-request/USD5 route authorization.

| Route | Positive | Negative | Requests |
|---|---|---|---:|
| Ollama/native | Correct verdict and coherent fragments | Both false assertions contradicted | 20 |
| OpenAI/langgraph | Correct verdict and coherent fragments | Both false assertions contradicted | 20 |
| Bedrock/native | Model passed, but segmentation inadequate | Incomplete: pilot request cap reached | 40 |

Manual review of v2 records: Ollama and OpenAI separated the numeric assertion
from both execution-failure assertions, and cited the successful source event.
Bedrock split much of the positive into individual words, including one fragment
crossing line boundaries around the number. Character coverage passed, but this
is not a satisfactory claim partition. Do not count that route as accepted or
interpret its budget exhaustion as a semantic rejection. No retries seeking a
favorable result were performed after these observations.

## Next acceptance gates

1. Enforce or independently audit meaningful proposition boundaries, without
   language/model-specific keyword rules. Preserve original text coverage.
2. Freeze held-out positives and close negatives covering partial tool failures,
   negation, multiple values, unsupported causal claims, misleading citations and
   mixed metaphor/factual language. These must not be the calibration pairs above.
3. Certify repeated runs across the full matrix, with integrity and semantics
   reported separately; inconclusive is not success.
4. Apply the frozen accepted evaluator to the original long-run evidence. The Eval
   adapter is implemented but the new claim evaluator has not yet been live-tested
   across all seven long steps. Prior long-evals-v1 results remain unchanged.

Current evidence supports progress on two formerly failing routes, not a 100%
claim, statistical reliability guarantee, or release completion.
