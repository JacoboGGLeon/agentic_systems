# Claim review v3: live regression, not certification

The existing v1 fixture was reused deliberately as an exposed regression set.
There were no retries seeking a favorable answer and no provider substitutions.
Artifacts are in `work/claim-regression-v3`, outside this checkout. Each route
manifest records the application and core source hashes used for execution.

## Observed results

| Route | Requests | Aggregate matches | Manual semantic/citation acceptance |
| --- | ---: | ---: | ---: |
| OpenAI / langgraph | 30 | 2/3 | 0/3 |
| Ollama / native | 31 | 2/3 | 0/3 |
| Bedrock API key / native | 30 | 3/3 | 3/3 |

All nine executions completed. Models remain gpt-4.1-mini,
qwen3:4b-instruct-2507-q4_K_M, and us.amazon.nova-pro-v1:0 respectively.
The 91 requests count against the existing per-route allocations, not fresh
budgets. Cumulative request counts are 165, 182, and 245 respectively.

Manual inspection covered every fragment, status and cited record:

- OpenAI: the success and failure fragments have correct statuses but both cite
  all three events, including irrelevant records. The causal assertion is
  incorrectly supported by co-occurring events. The metaphor is incorrectly
  supported by a lookup event.
- Ollama: the combined success/failure fragment cites only the export failure,
  omitting both successful lookups. The causal assertion is incorrectly
  supported. The metaphor is incorrectly supported by a lookup event.
- Bedrock: all three cases have the expected statuses and relevant citations;
  the causal assertion remains unknown and the metaphor is nonfactual with
  no citations.

Thus 7/9 matching aggregate labels must NOT be reported as 7/9 complete semantic
passes. No release approval follows from this regression run.

## Interpretation and next gate

The v3 instruction change did not solve the semantic failures. The deterministic
rule rejecting citations on a nonfactual classification is useful but cannot
detect a model incorrectly classifying a metaphor as supported. Supplying the
original answer did not establish reliable fragment-local judgment. These runs
do not isolate which prompt or context change caused each regression.

Before another broad matrix, the acceptance harness needs explicit per-claim
classification and citation expectations, including combined fragments, so it
does not mistake a matching aggregate label for semantic acceptance. A bounded
experiment should isolate context from the judgment target and test factuality,
support, and contradiction separately, using the same declaration for every
route. This remains application-level work, not a new public library API.

Retain the v1 and v3 failures unchanged. Subsequent independent acceptance must
use a new frozen fixture, not call these exposed examples held-out evidence.
