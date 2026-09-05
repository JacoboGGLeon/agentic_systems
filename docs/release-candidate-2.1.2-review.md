# 2.1.2 candidate: release remains blocked

This is a review checkpoint, not a release attestation. Agentic Systems 2.1.1
remains the published version; its artifacts are not replaced by this candidate.

## Eval hardening checkpoint (2026-09-05)

The development source now differs from the frozen artifact below. No new wheel
has been certified. Do not reuse the old bundle hashes to attest these changes.

- Public Eval accepts typed deterministic assertions and retains their failures
  inside the report before the judge. The literal poem predicate now participates
  in this boundary; it does not repair the candidate's answer.
- Default deterministic authority is empty: structural passes cannot promote
  negative model judgments. Explicit legacy opt-in remains available, but the
  release runners do not use it.
- Studio's two/eight-turn runner observes each completed turn through Eval with
  a same-provider native model judge and a typed certification Tool. It preserves
  candidate/judge usage separately, human_result and hierarchical lineage.
- The full offline run reached 100% core statement coverage, with 1,296 passed,
  six skipped and five failures. Three coherence failures were subsequently
  resolved by regenerating the API/notebook contracts. Two packaging guards
  correctly rejected dirty core provenance; they must pass after a clean checkpoint.
- A subsequent Studio/API suite passed 570 tests. New runner regression verifies
  no duplicate candidate inference, strict rejection, usage separation and timeout
  aggregation. This is offline behavior, not evidence of model judgment quality.

Live judge calibration remains **blocking**. Four instruction/schema experiments
classified respectively 7/9, 7/9, 4/9 and 6/9 regression fixtures correctly. Reading
the verdicts exposed both false approvals of echoed requests and false rejections
of faithful summaries. No rejection was promoted or candidate answer rewritten.
The final instructions classified all 12 independent translation/summary holdout
fixtures correctly; this does not cancel the remaining regression failures.

All calibration candidates are explicitly fixtures, not application executions.
SDK-reported judge tokens for the five runs: 29,872 + 28,841 + 29,157 + 28,731 +
32,479 = **149,080**. They are additional to the historical 374,515 below, giving
**523,595** observed tokens before the new conversation runs. Failed experiments
remain in `.tmp/eval-hardening/`; none is silently replaced by a passing sample.

Fresh eight-turn native Studio conversations completed for four providers. The
automated results were Python 8/8 (mock control), OpenAI 8/8, Bedrock 8/8 and
Ollama 4/8. These source-development runs are not frozen-wheel attestations.
Manual reading distinguishes the following issues:

- OpenAI and Bedrock produced grounded arithmetic, public Tool/Skill/System code
  and substantive final summaries. Bedrock's Provider/Framework phrasing mixes
  English and Spanish; neither provider's success certifies arbitrary dialogue.
- Ollama's calculation has real `safe_calculate` evidence for 323, despite an
  internally contradictory negative judge finding. Its final answer really does
  echo the summary request. Its ownership explanation incorrectly assigns Tool
  execution to the inference Provider; the System answer primarily explains Skill.
- Ollama judge turns 6–8 did not produce semantic verdicts: the SDK rejected
  prompts of 5,065, 4,929 and 5,121 tokens against the server's 4,096-token context.
  These are operational failures, not zero-quality semantic assessments. Unknown
  SDK usage for these failures is not counted as zero billing.
- Reviewing lineage exposed a separate gap: Studio's `compose_result` aggregates
  Tool events but does not retain child RunResults or execution IDs. The existing
  flat route is observable, but cannot certify the promised execution hierarchy.
  Fix composition at the public API boundary and add a hierarchy gate before a
  new release. Do not manufacture child execution evidence in the renderer.

New conversations consumed candidate/judge tokens respectively: OpenAI
12,416/44,670, Ollama 16,615/25,348, Bedrock 12,986/51,241. Total: **163,276**.
The complete observed ledger is now **686,871** tokens (historical runs plus all
calibrations and these conversations). Python invoked no LM. Candidate network
retries were zero; response repairs were OpenAI one, Ollama two, Bedrock zero.

Next: preserve composition lineage, supply a bounded but sufficient judge context
without silently discarding evidence, and verify judge calibration and complete
conversation semantics again. Publication and new external validation bundles
remain blocked until candidate and evaluation quality are demonstrated together.

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
- OpenAI: 16 episodes passed the old automated gate. Subsequent manual reading
  found forbidden trailing spaces in its native poem too. This is another false
  positive, not a provider-specific Ollama defect.
- Ollama: one native calculation timed out at 120 seconds; the other 15 episodes
  passed the old gate. An isolated four-episode repeat finished, but manual review
  then found a false positive in its poem.
- Bedrock: the initial 16 episodes failed with an expired bearer token. After the
  user renewed it, a fresh strict-gate matrix completed 16/16 episodes across four
  frameworks. All 16 human results and rendered lineages were read: correct
  evidence, one specialist per supported case, none for unsupported requests, and
  literal three-line poems.

### Blocking false positive: exact poem formatting

The request requires the middle line to be exactly `323`, with no spaces or
punctuation. The observed response contained `323` followed by two spaces. The
validator stripped formatting and extracted digits, accepting that response and
also accepting `323,` and `3 2 3`. The model judge approved it too.

The gate now compares the original middle line literally and requires exactly
three lines. Regression tests replay the observed response: arithmetic evidence
remains valid, but request fulfillment fails. Creative wording on the outer lines
is not prescribed. No provider/model branch or automatic answer rewrite was added.

A fresh Ollama native run reproduced the malformed poem and the corrected release
gate rejected it (three episodes passed, one failed). The nested generic eval and
model judge still reported success: the generic deterministic contract does not
yet express this text-format predicate. Move explicit scenario predicates into
the eval validation boundary so nested verdicts also reflect this failure.
The changed gate passed 147 release tests; six tests were skipped.

### Blocking false positives: Studio conversation semantics

Eight-turn Studio runs completed for Python, OpenAI and Ollama. Python is a mock,
not a language-model comparison. OpenAI used one bounded response repair; Ollama
used two. These are reported separately from network retries (zero observed).

Manual review of Ollama found that its last answer echoed the request to summarize
instead of summarizing the conversation. Another turn inaccurately attributed
tool execution to the provider. Keyword checks approved both. Consequently the
Studio report's `ok` is insufficient for semantic release approval. Strengthen
the evidence-backed conversational evaluation and rerun before closing this item.

Bedrock's renewed eight-turn Studio run also completed, without response repairs
or network retries. Reading its answers confirmed real arithmetic evidence,
public Tool/Skill/System code and the Provider/Framework distinction. Its System
explanation loosely attributes episode handling to System; review this against
Environment ownership rather than approving the narrative unconditionally.

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
| Ollama native, corrected strict gate | 3,798 | 19,919 |
| Bedrock matrix, renewed token and strict gate | 31,435 | 85,279 |
| Bedrock Studio, renewed token, eight turns | 12,963 | Not run |

Observed total for these runs: **374,515 tokens**. Usage for the initial expired
Bedrock calls was unavailable; Python control did not invoke a language model.
Later runs must be added as new
ledger entries rather than silently replacing failed attempts.

## Remaining release gates

1. Rerun corrected semantic validation, preserving initial failure evidence.
2. Resolve conversational false positives with evidence-backed evaluation, not
   additional approval keywords; verify final answers and lineage manually.
3. Preserve the renewed Bedrock evidence; rerun affected scenarios after the
   remaining evaluation changes.
4. Regenerate validated kits with the corrected gate assets, then obtain fresh
   AWS IAM, ADA IAM and vLLM evidence for this exact wheel.
5. Seal the reviewed release manifest, prove TestPyPI OIDC publication and
   idempotent replay, then publish through the production workflow and close the
   GitHub Release only when all required evidence agrees.

No TestPyPI or PyPI publication is authorized by this document.
