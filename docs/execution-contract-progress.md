# Execution boundary corrections and progressive long control

These are source experiments, not wheel or release certification.

## Implemented

- Explicit agent runtime model takes precedence over a System default; explicit
  agent model still wins. No provider/model-specific rule.
- OpenAI Agents SDK argument-validation errors use the existing private error
  envelope, not a string-matching heuristic. Error-like successful text stays valid.
- Function tools are bounded before invocation; extra calls cannot execute user
  callbacks. Budget state belongs to the per-run copy, not the cached SDK agent.
- Tool identity prefers the SDK's declared tool name over Python function name.
- Strands invocation transcript selection tracks retained message object identities
  rather than a numeric offset invalidated by SDK history pruning. This is tested
  with the installed SDK's retention behavior; copying/replacing old transcript
  objects or pruning messages from the current invocation needs further coverage.

## Compact v3

Evidence directory: `../compact-three-agent-matrix-v3/` from repository root.
Original fixed candidates and negative injections, unchanged prompt, one pair per
route. Core source hashes and outbound tool schemas are saved. 52 requests total.

| Provider | native | langgraph | openai-agents | strands |
|---|---|---|---|---|
| Python control | pass/pass | pass/pass | pass/pass | pass/pass |
| Ollama | fail/fail | fail/fail | fail/fail | fail/fail |
| OpenAI | pass/pass | pass/fail | pass/pass | pass/pass |
| Bedrock API key | pass/pass | pass/pass | pass/pass | pass/pass |

11/16 pairs, including four non-semantic Python controls. This is 23/32 case
gates. Ollama receives nested object schemas, but emits invalid arguments. The
openai-agents failures now remain failures, rather than successful error strings.
OpenAI/langgraph still falsely approves the contradictory negative: its explanation
focuses on the valid numeric line. Other negative explanations identify the false
execution claim, although criterion-level reasons are not uniformly rigorous:
OpenAI/native still calls the negative metaphorical under clarity while rejecting
its grounding. These are not uniformly certified explanations. Improvement in
individual sampled model decisions is not proof that adapter changes fixed
semantic reliability. Historical false positives remain part of the evidence.

## Long deterministic control

`scripts/long_environment_control.py` declares 7 Environment steps, 9 operators,
11 tools and 5 real skills assigned to the operators. Every step executes all
11 operations (77 executions per successful episode). This arithmetic topology
control is not the earlier long semantic benchmark with judges.

Eight tests cover four frameworks: successful two-episode runs, reset state,
independent callback ledger versus normalized evidence, execution IDs and parent
links, historical transition retention, and a failed tool with stopped child
execution. Sibling independent tool completion order is not prescribed.

## Progressive inference

`../long-progressive-v2/` activates only the final operator with an LLM; the first
eight remain Python. OpenAI/openai-agents passed all seven steps with 14 guarded
requests. No judges are included yet, so this proves tool-mediated integration,
not semantic adequacy.
Bedrock/native also passed with 14 requests; its source provenance is explicitly
unsealed because formatting occurred during execution. Its post-run hashes are
not an attestation of loaded bytes and cannot certify a release candidate.
Other routes and semantic long-case acceptance remain
separate gates. No allocation was reset or transferred.

## Not closed

Ollama structured arguments, OpenAI semantic false positives, complete SDK-bound
sync/async and compaction evidence coverage, long semantic positive/negative judges,
remaining progressive routes, full release coverage/provenance/distribution gates.
No release was published or declared complete.
