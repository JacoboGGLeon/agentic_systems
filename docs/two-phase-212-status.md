# Two-phase application acceptance status

This application-level work belongs to 2.1.2 certification. It does not introduce
EvidenceMemory, context=, persistence, resumption, or compositional algebra.

## Promise matrix

| Promise | Implementation | Evidence | Status |
| --- | --- | --- | --- |
| Select one observed action; reject missing/altered/failed evidence | scripts/certification_evidence.py | tests/contracts/test_certification_evidence.py, 16 tests | Offline passed |
| Preserve identity and reject sibling reuse while allowing ancestor projections | Same selector | Mutation and identity tests | Offline passed |
| Selected payload isolated from subsequent mutation | Frozen JSON-backed application record | Mutation test | Offline passed |
| Explicit action then structured synthesis, no provider fallback | scripts/two_phase_semantic_application.py | 16 original route reports | Deterministic gates passed |
| Judge cannot override deterministic failure | accepted and compact_judge_payload | Contract tests | Offline passed |
| All 12 model routes evaluated on original answers | Compact evidence judge profile v2 | 12 additional judge reports | Automatic approvals; review defects remain |
| Reliable evidence-backed judge explanations | Typed recorded assessments plus manual reading | Six erroneous length statements | Pending |
| Distribution matches certified source | Release provenance gates | Full suite: 1350 passed, 2 failed, 6 existing opt-in live skips | Pending new clean commit and candidate |

Evidence paths are workspace artifacts, not distribution contents:

- work/two-phase-212-matrix-v1: original candidates and first judges.
- work/two-phase-212-compact-judges-v2: judges of those same saved candidates;
  each records the original file SHA-256. No candidate was regenerated.

The original judge parser rejected the tool's legitimate findings field. It was
corrected by explicitly declaring that field, retaining extra=forbid. The first
Ollama judge requests exceeded the endpoint's 4096-token context because they
included duplicate result/transcript/lineage representations. The v2 packet
retains execution identities, runtime, state, selected tool evidence and the
original answer; full trees remain in the original artifacts.

## Manual semantic review

All 16 candidate answers satisfy the deterministic literal format and evidence
checks. Python's four routes are deterministic controls, not creative generation
or LLM judges.

All 12 model judges returned all criteria passed. However, six explanations
incorrectly describe the central line as 323 characters long:

- Ollama: langgraph and strands.
- Bedrock: native, langgraph, openai-agents and strands.

The actual line is the string "323", three characters. These explanation defects
must not be concealed by the derived score/rationale. They are not evidence that
the candidate answer failed, but they block treating the judges as fully
validated. Near-negative judge probes and explicit literal contract fields
remain necessary before final certification.

Some SDK processes also emitted Windows asynchronous-pipe cleanup warnings after
returning their result. These remain visible in process output, not reclassified
as successful platform cleanup.

## Limits preserved

### Citation experiment v5: not a certified replacement

The application now requires a nonempty citation list per criterion, with a
local catalog reference and a typed JSON value. Catalogs are recomputed from
observed answer/execution evidence; quoted values are compared without coercion.
Negative tests cover missing, unknown, duplicate and mismatched references and
forged catalogs. Valid references explicitly do not establish semantic relevance.

The v5 twelve-route run used 25 requests and retained all original candidates.
Nine routes passed reference and fact checks. Ollama/langgraph omitted a required
criterion and failed schema validation. OpenAI/native and OpenAI/openai-agents
cited data-field paths outside the deliberately limited catalog, so the reference
gate rejected them. Bedrock/strands supplied correct citations but still gave
generic explanations; the original semantic issue is not resolved. These are
experimental results, not a claimed improvement in total release certification.
Artifacts are under work/two-phase-212-cited-judges-v5; none of their pending
reviews has been silently promoted to approval. 796 contract/provider tests pass.
Next review must distinguish incomplete catalog design from unsupported citations
and express rubric completeness in the generated schema before further live runs.

### Investigation of copied observation fields

The failed Ollama response copied length_unit, line_count and middle_line_index
from the application contract into a closed observation object. Inspection and
the provider-projection regression test show that the nested schema retains
additionalProperties=false; there is no evidence here of schema loss in the
adapter. Input/output role confusion is the supported working explanation, not
a proven account of model internals.

The application now separates returned facts from formatting requirements,
deriving the partition and output-field guidance from LiteralObservation's
declared fields. Unknown response fields remain errors. No provider/model
branch, schema relaxation, output repair or public API was introduced.

The fixed-profile v4 run evaluated all twelve OpenAI/Ollama/Bedrock API-key by
native/langgraph/openai-agents/strands routes once, retaining original candidates.
All twelve produced valid typed observations and passed the deterministic factual
checks, using 24 requests in existing allocations. Reading all sixty explanations
yielded eleven approvals and one rejection: Bedrock/strands gave generic assertions
instead of evidence-specific reasons. Original and separate reviewed artifacts are
under work/two-phase-212-separated-judges-v4. Prior failures remain preserved.
789 contract/provider tests passed. Windows async pipe-cleanup warnings still
occurred in two processes; these are not silently treated as resolved.
This fixes the observed schema failure in the tested sample, not universal model
compliance or release certification, and does not close the remaining semantic gate.

### Typed judge observations and content-bound review

The current application judge tool records typed value/text/length observations
and retains every criterion explanation, including positive assessments. The
release verdict checks these observations with a deterministic Tool/Agent and
remains pending until an independent explanation review is attached to a SHA-256
of the exact judge input, execution, decision, observations and assessments.
This hash binds content; it does not authenticate a reviewer or prove semantics.

In `work/two-phase-212-observed-judges-v3`, native OpenAI and Bedrock each used
two requests to judge their original saved candidates. Their typed facts and
five explanations were read and approved in separate `*-reviewed.json` files.
Original files remain unchanged. Native Ollama used three requests and failed:
it copied three extra contract fields into the closed observations schema.
That rejection is preserved; the fields were not dropped or silently accepted.
This is calibration on three native routes, not complete framework or release
certification. Earlier negative-probe false approval/rejection findings remain.

### Live notebook execution follow-up

The six previously skipped notebook routes have now been executed with real
inference and kernel-local per-route allocation enforcement:
OpenAI/native, Bedrock API key/native, Ollama/native, OpenAI/langgraph,
OpenAI/openai-agents and OpenAI/strands. This is six routes, not a new
certification of every provider/framework combination.

Evidence is retained outside the distribution in
`work/notebook-live-212-v1/*/{executed.ipynb,observations.json,summary.json}`;
the corrected OpenAI Agents execution is in `work/notebook-live-212-v4/openai-agents`.
Failed attempts v1-v3 are preserved. The v3 guard diagnostic proves that the
native handoff target was submitting a request without an output-token bound.
Prepared native agents now retain their explicitly declared max_tokens, including
when entered directly by the SDK's handoff machinery. No model-specific override
or new public API was introduced. The notebook policies also declare output caps.

All six notebook execution checks passed, including Strands MCP/A2A local
controls. The unit suite passed 190 tests; the focused tutorial/adapter/evidence
suite passed 57 tests before adding five prepared-handoff regression cases.
These observations concern the working source, not a sealed wheel. Existing
pytest live gates remain opt-in; this independent execution does not turn skips
from an earlier test run into passes.

Manual review found that the successful SDK handoff certificate names the expected
specialist, but its generated response says it is transferring the conversation
onward. Preserve this narrative defect separately from technical handoff success;
do not claim semantic conformance from the certificate alone. The earlier six
judge explanation defects also remain unresolved.

The tools-plus-structured-output Ollama/openai-agents case is now resolved in the
adapter without a model-specific branch. One public Agent invocation uses two
bounded protocol phases: executable work first, then non-executable typed
synthesis. OpenAI-compatible endpoints receive the same JSON Schema as a prompt
constraint when native response-format support is not portable; the SDK still
performs strict validation against the original output type.

The deterministic sync/async regressions preserve one Tool event, aggregate all
three provider requests, reject an impossible one-turn budget before execution,
and retain messages, usage, raw responses, and Tool evidence if synthesis fails.
The live Ollama/openai-agents reproduction passed with exactly one independently
observed multiply call and a validated two-field result; its source-tree evidence
is under work/structured-tool-output-phased-v3. Earlier failed attempts remain
unchanged. This result does not certify an old wheel: the case must be repeated
from the sealed 2.1.2 artifact during release certification.
