# Long saved-execution evals v1

Application: `scripts/long_environment_evals.py`, using `toolkit.eval().evaluate`.
The candidate is a saved original execution, never regenerated during evaluation.
Source: `../long-progressive-v2/openai-runtime/openai-agents/result.json`.
Outputs and frozen hashes: `../long-evals-v1/openai-runtime/openai-agents/`.

## Deterministic gates

Seven per-step evaluations compare normalized tool events with the independent
callback observer (including multiplicity), check unique event identities, actor
and tool counts, parent relationships, execution status and operation outputs.
Regression negatives inject omissions, duplicate identities, corrupted outputs
and foreign parent IDs. An approving control judge cannot override integrity
failure. The surrounding long-control tests retain reset and cross-episode checks.

## Semantic pilot

Judge: OpenAI gpt-4.1-mini through openai-agents. Two criteria: grounding and
clarity. The judge receives all eleven compact tool events for the relevant step,
their source IDs and the original final operator answer. The negative replaces
only that answer with an explicitly recorded false claim of total tool failure.
The nine-agent candidate topology is unchanged; evaluation judges are external.

One fixed pass over seven originals and seven negatives: 28 guarded requests,
charged to the existing route allocation. No budget reset and no best-of reruns.

- Original verdicts: 7/7 accepted; explanations identify the observed final values.
- Negative verdicts: 7/7 rejected under grounding; deterministic integrity remains
  true, demonstrating that rejection comes from semantics rather than corruption.
- Manual explanation audit: negative step_5 invents an increment by five. The
  tools have distinct increments, so that explanation is not fully supported,
  despite its correct rejection of the false failure claim. Do not certify all
  fourteen explanations or hide this defect behind correct binary verdicts.

This is one route, one episode, and a narrow contradiction family. The first eight
candidate agents are Python and the final agent is LLM-backed. It is not a complete
long semantic matrix, an all-LLM system, or release certification. Candidate and
judge share a model/provider, so independent model-family judging remains absent.

No automatic reasoning-relevance proof is claimed. The explanation defect remains
a blocking observation for a claim of fully faithful semantic evaluation.
