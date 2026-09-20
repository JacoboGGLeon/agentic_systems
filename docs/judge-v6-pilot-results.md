# Fixed v6 pilot: expansion blocked

The six-point stabilization workflow is implemented at application level. No
public library API or provider/model-specific exception was added. Historical
artifacts remain unchanged. Contract/schema, reference logic and acceptance text
were hashed before inference. Full matrices remain frozen.

## Offline result

803 contract/provider tests passed; targeted lint passed. Tests exercise required
rubric keys in the generated schema, nested/escaped evidence paths, missing or
altered citations, stale reviews and separate integrity/judge/semantic outcomes.
Python Tool/Agent checks retain RunResult and lineage. These tests do not certify
model compliance or semantic entailment.

## Pilot result

Six cases, one original positive and one explicitly injected unsupported-claim
negative per provider, all native. 14 inference requests were reserved/sent through
the guarded transport: OpenAI 6, Bedrock 4, Ollama 4. No second sample, changed
prompt, candidate regeneration or matrix expansion followed the failures.

- OpenAI: both outputs violated the nested citation schema (strings instead of
  citation objects, with misplaced value_json fields). Both are inconclusive.
- Bedrock positive: schema/facts/reference existence passed, but the
  evidence_correctness assessment cited only /answer while asserting that a tool
  output confirmed the product. This does not establish the promised cited
  relationship; independent review cannot approve that explanation.
- Bedrock negative: stopped by the conservative USD 0.10 pilot cost limit.
  This is an operational interruption, not a semantic pass or failure.
- Ollama: both outputs had quote/type/reference-value mismatches. In addition,
  reading the negative's explanations exposed a semantic false approval: it
  ignored the explicit false claims that all calculation tools failed and no
  verified product was returned. The deterministic/reference gates prevented
  final approval, but this does not validate the semantic judge.

All model/schema failures remain distinguishable from candidate-integrity
failures. The negative preserves literal format but is knowingly semantically
false; it is not mislabeled as an original candidate execution. Artifacts and
source hashes: work/judge-stable-pilot-v6/<provider>/.

## Conclusion

The workflow now fails closed and preserves a useful diagnosis, but the v6
evaluation contract has not passed its pilot and is not release-certified.
The citation representation remains a model-compliance burden. Any simplification
must be a new, versioned contract evaluated against the same fixed positive/negative
obligations, not silent output repair or retroactive relaxation. A larger live
matrix is explicitly not justified by these results. No universal model guarantee
is claimed.
