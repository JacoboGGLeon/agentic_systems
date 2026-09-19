# Compact three-agent matrix: source experiment

This is not release certification and does not cover the long Environment case.
The application reuses saved candidate executions and runs a new preparation,
semantic judgment and deterministic aggregation pipeline. It does not regenerate
the original candidates. Each route has one original positive and one explicitly
injected contradictory answer, with no best-of selection.

Evidence: `../compact-three-agent-matrix-v2/` relative to the repository.
Each route contains source hashes, original candidate hash, normalized results,
lineage, decisions and accumulated budget counters. Historical attempts remain.

## Results

Cells show positive / negative gates, not universal provider capability.

| Provider | native | langgraph | openai-agents | strands |
|---|---|---|---|---|
| Python control | pass / pass | pass / pass | pass / pass | pass / pass |
| Ollama | fail / fail | fail / fail | fail / fail | fail / fail |
| OpenAI | pass / fail | pass / fail | pass / pass | pass / fail |
| Bedrock API key | pass / pass | pass / pass | pass / fail | pass / pass |

20/32 case gates passed. 8/16 routes passed both cases, including four Python
controls: these fixtures are not semantic inference. There were 53 guarded
requests: Ollama 20, OpenAI 16, Bedrock 17. Budgets were not reset.

## Explanation review and failure classification

- OpenAI native, langgraph and strands incorrectly approved the negative.
  Their explanations focused on the correct numeric middle line and described
  contradictory execution claims as metaphor or ignored them. These are false
  semantic approvals, not missing evidence: the received packet contains both
  the false failure claim and the successful tool event.
- OpenAI openai-agents and Bedrock native, langgraph and strands rejected the
  negative with explanations identifying the contradiction. Positive explanations
  matched the numeric result and successful source event. This is manual review
  of this sample, not a bound certification receipt or broad statistical claim.
- Ollama returned invalid tool argument structures in inspected cases. Native
  and langgraph supplied strings where Assessment objects were required;
  strands recorded tool failure. openai-agents projected an SDK validation error
  string as successful tool output; downstream aggregation rejected it. That
  failure-normalization discrepancy requires a dedicated adapter regression.
- Bedrock openai-agents negative failed the max_tool_calls policy: four observed
  calls with a limit of one. It is not counted as a correct semantic rejection.
  Raw events must be checked before attributing repeated calls versus projection.

## Configuration incident

The preceding v1 run passed eight Python controls but failed all model cases
before guarded inference (zero requests). System's Python model default overrode
the judge runtime model. The application now sets the agent model explicitly and
checks it before compilation. Three offline regressions cover explicit model
preservation for the LLM providers. No provider-specific fallback was added.

## Remaining work

Inspect SDK-bound tool schemas and error normalization before attributing all
Ollama failures to model capacity. Investigate the Bedrock repeated tool events.
Preserve semantic false positives; any later prompt or contract change requires
a new named experiment, not overwriting these results. The 7-step Environment,
9-agent, 5-skill, 11-tool case remains untested with this topology.
