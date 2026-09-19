# Claim review v5: explicit relation schemas

Application-only change: the same six agents and deterministic aggregation now
use `record_support(all_assertions_supported, evidence_ids)` and
`record_contradiction(any_assertion_contradicted, evidence_ids)` instead of an
ambiguous shared `established` input. Outputs remain normalized relation
decisions. No public library API or provider-specific behavior was added.

The three exposed regression cases and annotation criteria did not change.
Each was run once per route; no unsuccessful run was replaced. Full results,
normalized tool evidence, lineage and pre-run source hashes are preserved under
`work/claim-regression-v5`, outside this checkout. All 97 recorded source hashes
per manifest were checked after execution: zero mismatches on both routes.

| Route | Partial success | Unsupported causality | Fact plus metaphor | Requests |
| --- | --- | --- | --- | ---: |
| OpenAI / langgraph | Blocked: inconsistent decisions | Correct unknown | Correct, with relevant citations | 48 |
| Ollama / native | Incorrect unknown | Correct unknown | Correct, with relevant citations | 44 |
| Bedrock / native | Not run | Not run | Not run | 0 |

All six executed results were manually reviewed, including every stage's tool
arguments/outputs and the successful verdicts' references. The strict annotation
gate agrees: 4/6 accepted on this small regression set, not a full matrix result.

OpenAI correctly reviewed both successful lookups. On the second fragment,
"The export failed.", it returned both full support and contradiction, citing
the same failed export record. Deterministic aggregation blocked the result;
it did not choose a favorable judge. Ollama kept both sentences together and
reported neither support nor contradiction, wrongly leaving an evidenced
statement unknown. These false blocks remain failures.

The latest contract/eval regression passed 793 tests. Ruff checks passed on the
changed application and test files. Four controlled completion-boundary tests
verify distinct stage instructions and payloads through native and langgraph
with both OpenAI and Ollama. They are offline transport-contract tests, not
semantic evidence or substitutes for SDK/network certification.

## Budget and limits

V4 and v5 together consumed 219 additional reserved requests this work session.
Current cumulative ledgers: OpenAI/langgraph 255/300 (45 left), Ollama/native
256/300 (44 left), Bedrock/native 300/300. Bedrock was not retried in v5 and
requires explicit authorization for any increase. Monetary reservations remain
below USD 5 per route; reservations are not actual billing.

No independent held-out acceptance set, full 16-route recertification, wheel
certification, or publication was completed. The current release remains open.

## Next implementation boundary

The remaining mixed-status case confuses an operation's failure with the truth
of a claim describing that failure. The next bounded design should represent
execution-state claims as typed comparisons against observed fields and compute
those comparisons deterministically through tools. Semantic extraction and
coverage must still be checked separately: a correct comparison does not prove
that a model extracted the right assertion or selected complete evidence.
Do not special-case fixture text, tool names, providers, models, or expected
answers, and do not relax the existing acceptance annotations.
