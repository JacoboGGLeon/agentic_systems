# Evaluation contract v6 — frozen before the pilot

This is an application contract, not a new library API. Historical v1–v5 evidence
is immutable and is not reclassified against this contract. Full live matrices
remain frozen until the pilot meets every condition below.

## Three separate outcomes

- Candidate integrity: deterministic format, evidence and execution checks.
- Judge validity: complete closed schema, factual observations, local references,
  and independent content-bound review of the explanations.
- Semantic quality: pass/fail only when the judge is valid; otherwise unknown.

An invalid judge yields an inconclusive evaluation. It does not establish that
the candidate is wrong. A deterministic candidate violation still blocks release.

## Contract and acceptance

The required criterion object is generated from the existing rubric. Every key
is required, extra keys forbidden, and each value contains a boolean, a nonempty
explanation and nonempty citations. References can address any actual field under
the observed answer/execution evidence, with escaped local paths. They cannot
address external executions or use requirements as observed facts. Citation values
must match without type coercion; catalog data is recomputed, not trusted.

Explanation review checks whether the cited content supports the stated judgment.
Short explanations are sufficient if the evidence-to-conclusion relation is clear.
There is no minimum prose length, keyword threshold or eloquence score. A correct
reference alone is insufficient; unsupported, irrelevant or contradictory reasoning
makes the judge invalid. Review receipts are content-bound, not authentication.

## Offline gate

Test nearby positives and negatives for missing criteria, extra fields, bad types,
absent/altered/duplicate citations, forged catalogs, escaped nested paths, stale
reviews, and valid citations with irrelevant/contradictory reasoning. The latter
requires an independent negative review; JSON equality does not decide entailment.

## Fixed pilot

OpenAI, Bedrock API key and Ollama, all native; one saved original positive and one
injected semantic negative per provider. The negative keeps the literal three-line
format/product while falsely claiming the observed multiplication failed and no
verified product was returned. It is labeled as injected in the audit artifact,
never as original execution evidence, and the expected verdict is hidden from the
judge. No regenerated candidates, best-of retries, prompt tuning or full matrix.

At most six inference requests and USD 0.10 conservative reservation per provider,
within—not instead of—the existing route allocations. Freeze source hashes before
the first request. Every attempt and operational failure is retained.

Expansion requires all six cases to produce valid, factually consistent judgments,
positive/negative semantic decisions as specified, and independent explanation
review. One failure blocks expansion. Python remains a deterministic operator,
not a model judge. This pilot is calibration, not wheel/release certification.
