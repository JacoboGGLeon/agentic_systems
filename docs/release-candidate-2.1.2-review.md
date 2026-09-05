# 2.1.2 candidate: release remains blocked

This is a review checkpoint, not a release attestation. Agentic Systems 2.1.1
remains the published version; its artifacts are not replaced by this candidate.

## Artifact identity

- Core source commit: `c3aca9cabd0ebc16d66fa7f85bb45dddb1d60b36`.
- Wheel: `agentic_systems-2.1.2-py3-none-any.whl`.
- Wheel SHA256: `80d41870b5417d5eb4684291812a89af3da3f2128798843a6fe58a2de21a1f76`.
- The validation scripts are separate gate assets. Their corrected hashes must
  accompany new reports and rebuilt validation kits; old successful flags do not
  certify the corrected gate.

## Verified checks

- Quality CI passed for the core candidate and the subsequent cache-exclusion
  packaging change (`4519c299f9edfd2b7e0ab02c193d51578d4bde0f`).
- Wheel and sdist passed metadata checks. An isolated, non-editable Python 3.10
  installation passed `pip check`, a deterministic API/tool/invariant smoke and
  CLI help outside the repository.
- Five candidate ZIPs passed file inventory, checksum, notebook parsing, cache
  exclusion and secret checks. This is packaging evidence, not semantic approval.

## What the live runs actually established

The first automated matrix reported 43 passing and 17 failing episodes out of 60.
Those numbers describe the old gate's output, **not manual certification**:

- Python: 12 deterministic control episodes passed.
- OpenAI: 16 episodes passed the automated gate; complete manual certification
  remains pending.
- Ollama: one native calculation timed out at 120 seconds; the other 15 episodes
  passed the old gate. An isolated four-episode repeat finished, but manual review
  then found a false positive in its poem.
- Bedrock: all 16 episodes failed with an expired bearer token. This is an
  authentication failure, not a semantic verdict. Renew credentials without
  placing them in reports, then rerun.

### Blocking false positive: exact poem formatting

The request requires the middle line to be exactly `323`, with no spaces or
punctuation. The observed response contained `323` followed by two spaces. The
validator stripped formatting and extracted digits, accepting that response and
also accepting `323,` and `3 2 3`. The model judge approved it too.

The gate now compares the original middle line literally and requires exactly
three lines. Regression tests replay the observed response: arithmetic evidence
remains valid, but request fulfillment fails. Creative wording on the outer lines
is not prescribed. No provider/model branch or automatic answer rewrite was added.

### Blocking false positives: Studio conversation semantics

Eight-turn Studio runs completed for Python, OpenAI and Ollama. Python is a mock,
not a language-model comparison. OpenAI used one bounded response repair; Ollama
used two. These are reported separately from network retries (zero observed).

Manual review of Ollama found that its last answer echoed the request to summarize
instead of summarizing the conversation. Another turn inaccurately attributed
tool execution to the provider. Keyword checks approved both. Consequently the
Studio report's `ok` is insufficient for semantic release approval. Strengthen
the evidence-backed conversational evaluation and rerun before closing this item.

## Observed token ledger

These are SDK-reported tokens, not a billing estimate. Failed calls without SDK
usage are unavailable and must not be interpreted as zero billed tokens.

| Execution | Candidate tokens | Judge tokens |
| --- | ---: | ---: |
| Initial OpenAI matrix | 14,134 | 64,640 |
| Initial Ollama matrix | 14,661 | 74,901 |
| Isolated Ollama native repeat | 3,805 | 19,787 |
| OpenAI Studio, eight turns | 12,578 | Not run |
| Ollama Studio, eight turns | 16,615 | Not run |

Observed total for these runs: **221,121 tokens**. Bedrock usage was unavailable;
Python control did not invoke a language model. Later runs must be added as new
ledger entries rather than silently replacing failed attempts.

## Remaining release gates

1. Rerun corrected semantic validation, preserving initial failure evidence.
2. Resolve conversational false positives with evidence-backed evaluation, not
   additional approval keywords; verify final answers and lineage manually.
3. Renew the local Bedrock token and rerun matrix and Studio.
4. Regenerate validated kits with the corrected gate assets, then obtain fresh
   AWS IAM, ADA IAM and vLLM evidence for this exact wheel.
5. Seal the reviewed release manifest, prove TestPyPI OIDC publication and
   idempotent replay, then publish through the production workflow and close the
   GitHub Release only when all required evidence agrees.

No TestPyPI or PyPI publication is authorized by this document.
