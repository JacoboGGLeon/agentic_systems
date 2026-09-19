# Claim review v4: separate factuality, support and contradiction

This is an exposed regression set, not independent certification. All nine
results and their tool outputs were read. Fixture annotations were frozen before
execution and checked statuses, required citations, irrelevant citations, and
unaltered evidence content. They are never supplied to the agents.

| Route | Requests | Fully accepted | Remaining result |
| --- | ---: | ---: | --- |
| OpenAI / langgraph | 42 | 2/3 | Partial success: incompatible support/contradiction decisions |
| Ollama / native | 30 | 0/3 | All three blocked by incompatible decisions on the first fragment |
| Bedrock API key / native | 55 | 2/3 | Metaphor case interrupted by the request limit |

For OpenAI, causal uncertainty and the fact/metaphor distinction were correct,
including their citations. In the partial-success case both relation stages
returned true and cited the same successful lookup records. For Ollama, the
contradiction stage also returned true on evidence that supported the target;
none of these inconsistent evaluations produced a passing verdict.

Bedrock correctly accepted partial success with complete citations and marked
the causal relation unknown. Its last case retained four successful stage
results, then failed during the contradiction stage with
`acceptance_request_limit`. It is incomplete, not a semantic pass or a semantic
model failure. All 55 requests, including any repeated transport attempts, were
charged to the existing ledger; the cumulative route limit reached 300.

Total additional requests: 127. Cumulative counts: OpenAI/langgraph 207,
Ollama/native 212, Bedrock/native 300. No budget was reset or transferred.
Artifacts and frozen source hashes remain in `work/claim-regression-v4` outside
this checkout.

The fail-closed consistency check prevents contradictory judge decisions from
approving a result, but is not a solution to the remaining false blocks.
The 789-test contract/eval regression passed before the pilot. Four additional
offline controlled-completion tests subsequently confirmed delivery of each
stage's distinct instructions and data through native/langgraph with the
OpenAI/Ollama providers. This does not establish the exact HTTP payload of the
historical live calls, or prove semantic correctness.

Next bounded hypothesis: `record_relation(established=...)` leaves the requested
relation implicit in the instructions. Distinct, explicitly named support and
contradiction tool fields may reduce that ambiguity. Test it without changing
criteria, adding agents, or hiding v4 failures. Bedrock needs new authorization
before any further live requests on this route.
