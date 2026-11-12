# Agentic Systems

> **“Did the level of this series change? Compare the observations and show what supports the finding.”**

Build applications around executable Tools. Let actors select capabilities, let graph-backed actuators run declared operations, coordinate them in Systems, and inspect the evidence behind each result.

This guide follows one investigation from a numerical comparison to an episodic, evaluated application. Each question introduces the next part of the grammar.

**Version scope:** this is the README proposal for 2.1.9. The reported executions used the published **2.1.8** SDK. They establish a baseline; verification against the 2.1.9 release candidate remains pending. Explicit Agent contracts and policies, and their broader framework/provider validation, are planned for 2.1.10.

## Start with the executable example

Open [ADA_Time_Series_Discovery_219_Core.ipynb](examples/time_series_discovery_219/ADA_Time_Series_Discovery_219_Core.ipynb). Its filename describes the development target; its dependency pin is `agentic-systems==2.1.8`.

The notebook contains the data, visible declarations, seven teaching blocks, local checks, optional live execution, and evidence export. Live results reported here come from the supplied ADA execution bundles. The downloadable source notebook is supplied without those live cell outputs; those bundles are the live evidence.

Install into the notebook kernel:

```python
%pip install "agentic-systems[bedrock,openai-agents]==2.1.8" "matplotlib>=3.8" "nbformat>=5.10" "nbclient>=0.10" "ipykernel>=6"
```

Restart the kernel after upgrading an already imported SDK, then configure and Run All.

```python
RUN_BEDROCK = True
LIVE_FRAMEWORKS = ("openai-agents",)
# Alternatives: ("native",) or ("native", "openai-agents")

BEDROCK_MODEL_ID = "qwen.qwen3-32b-v1:0"
AWS_REGION = "us-east-1"
```

For local execution only, set `RUN_BEDROCK=False`. Python runs explicitly selected operations; it does not interpret the natural-language questions.

The notebook reuses an existing Boto3 `session` or unwraps `sagemaker_session.boto_session`. Otherwise it creates a Boto3 session using the environment credential chain. No OpenAI API key is needed for the Bedrock/OpenAI Agents profile.

The current continuation configuration retains the existing campaign ledger and explicitly raises its cumulative cap from 60 to 100 HTTP attempts. Keep the same working directory. It expects the existing ledger; set `ALLOW_NEW_CAMPAIGN=True` only for a first-ever campaign. Budget preflight, send counting and failures are recorded. Changing the framework does not reset the counter.

## One dataset, one investigation

| Property | Value |
|---|---|
| Publisher / dataset | FAO / FAOSTAT Production Indices, QI |
| Series | Mexico / Agriculture / Gross Production Index Number |
| Base | 2014–2016 = 100 |
| Coverage | Annual, 1961–2024; 64 observations |
| Source flags | `E`: estimated values |
| Snapshot | [data/series.json](examples/time_series_discovery_219/data/series.json), also embedded in the notebook |
| Transformation | Exact identifier filtering, type conversion and chronological sorting; no imputation or smoothing |
| Snapshot SHA256 | `59109a8fc4f18b0bf73ab9a19df2357800a303debaa23ceb2f505363f271fab2` |

Source provenance, retrieval time and archive hash are recorded in the JSON. The notebook validates the frozen snapshot before analysis; ADA does not need to download FAOSTAT data.

The initial comparison uses 2005–2009 versus 2010–2014. The episodic investigation uses successive non-overlapping ten-year blocks, comparing each block's two five-year halves.

## 1. “Did the level of this series change?”

**user:** Compare the observations and show what supports the finding.

**agentic-systems:** The earlier mean is **84.82**, the later mean is **92.21**, and the difference is **+7.39 index points**.

**context:** Ten observations from 2005–2014, split into equal chronological windows. This is a descriptive comparison; it does not establish a structural break or a cause.

**internals:** A Tool computes the means. A graph-backed actuator executes that operation.

**grammar:** `tool` → `Graph` → `Agent(graph=...)` → `RunResult`.

**route:** Observations → comparison actuator → `compare_windows` → measurement.

This standalone excerpt shows the first declaration:

```python
from statistics import mean
import math
from pydantic import BaseModel
import agentic_systems as toolkit

class ComparisonState(BaseModel):
    values: list[float]
    measurement: dict = {}

@toolkit.tool
def compare_windows(values: list[float]) -> dict:
    """Compare the means of equal chronological windows."""
    if len(values) < 4 or len(values) % 2:
        raise ValueError("Two equal windows are required")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Finite observations are required")
    midpoint = len(values) // 2
    earlier = mean(values[:midpoint])
    later = mean(values[midpoint:])
    return {"measurement": {
        "earlier_mean": earlier,
        "later_mean": later,
        "difference": later - earlier,
    }}

graph = toolkit.Graph(ComparisonState)
graph.add_node("compare", compare_windows)
graph.add_edge(toolkit.START, "compare")
graph.add_edge("compare", toolkit.END)
actuator = toolkit.Agent("comparison_actuator", graph=graph)

result = actuator.run({"values": [
    80.09, 83.88, 85.97, 88.18, 85.98,
    88.71, 87.69, 92.28, 94.53, 97.84,
]})
assert result.ok
print(result.data["measurement"])
```

The notebook uses a richer measurement schema shared by its later blocks. Evidence: `01_comparison.evidence.json`.

## 2. “Can you choose the analysis from my question?”

**user:** Describe the observations instead of comparing the periods.

**agentic-systems:** Selected `profile_series`. **10 observations**, average **88.515**, minimum **80.09**, maximum **97.84**.

**context:** A Skill exposes description, comparison and endpoint-slope Tools. Instructions ask the actor to choose one appropriate Tool and preserve all observations.

**internals:** The model chooses the operation; the selected Tool performs arithmetic. External checks inspect the actual Tool name and arguments.

**grammar:** `skill` + `runtime` + `framework` → `Agent(runtime=...)`.

**route:** Question → actor → Tool selection → execution → recorded result.

Both Bedrock/Native and Bedrock/OpenAI Agents selected the correct description Tool. Evidence: `bedrock_native_description.evidence.json` and `bedrock_openai_agents_description.evidence.json`.

## 3. “Can you coordinate and validate the investigation?”

**user:** Compare the periods and check the measurement before forwarding a finding.

**agentic-systems:** Discovery profiled the data, selected comparison and verified the recorded measurement. The live Discovery evaluation confirmed **+7.39 points** for 2005–2014.

**context:** Dataset identity, source reference and declared business criteria live in `Context`. Business channels such as measurements and validation flags live in graph state.

**internals:** Three Agents contribute distinct responsibilities:

| Agent | Role | Operation |
|---|---|---|
| Profiler | Actuator | Runs `profile_series` through a graph |
| Investigator | Actor | Selects an analysis Tool |
| Analyst | Actuator | Runs `validate_measurement` through a graph |

**grammar:** Multiple `Agent` declarations → coordination `Graph` → `System`, with `Context` and bounded `Memory`.

**route:** Discovery → Profiler → Investigator → Analyst → checked measurement.

Evidence: each profile's Environment descendants and `*_eval.evidence.json`.

## 4. “Can another capability review and report the finding?”

**user:** Review the finding and produce a report backed by execution evidence.

**agentic-systems:** Review independently recomputed the difference, applied the screening rule and produced a report containing measurement, verdict, threshold and analytical scope.

**context:** At least ten observations and an absolute difference of at least ten index points identify a review candidate. This business screening rule is implemented in a Tool; it is not an explicit Agent `policy` declaration.

**internals:** Challenger selects `check_finding`. Reporter is a graph-backed actuator that runs `render_report`. Together with the three Discovery roles, the application has five logical Agents and two coordinated Systems.

**grammar:** System composition → nested Agents → `evidence()` and `lineage()`.

**route:** Discovery System → Review System → reviewed report.

```mermaid
flowchart TD
    subgraph Discovery
        P["Profiler · actuator"] --> I["Investigator · actor"]
        I --> A["Analyst · actuator"]
    end
    subgraph Review
        C["Challenger · actor"] --> R["Reporter · actuator"]
    end
    A --> C
```

Evidence: `check_finding` and `render_report` events in each live Environment bundle. Review verifies observations and arithmetic; agreement between models is not its acceptance criterion.

## 5. “Can you investigate successive periods and remember prior observations?”

**user:** Process successive periods, retain previous observations and stop when a candidate requires review.

**agentic-systems:** Four episodes were processed. The fourth reached the screening threshold, so the Environment stopped before processing the next record.

**context:** Chronological ten-year records, bounded episode history, accumulated processed count and candidate flag.

**internals:** Environment executes the Discovery/Review graph per record. `update` accumulates state; `stop` checks the candidate flag. Prior episodes are available through context.

**grammar:** `Environment` + `records` + `state` + `update` + `stop` + `max_steps` + `Memory`.

**route:** Record → Discovery/Review → state update → stop decision → next record if needed.

```mermaid
flowchart TD
    E["Next record"] --> D["Discovery System"]
    D --> R["Review System"]
    R --> U["Update state and history"]
    U --> S{"Candidate or record limit?"}
    S -->|"No"| E
    S -->|"Yes"| F["Finish with evidence"]
```

Both frameworks produced the same observed progression:

| Episode | Period | Difference, index points | Prior episodes available | Decision |
|---|---|---:|---:|---|
| 1 | 1961–1970 | +5.928 | 0 | Continue |
| 2 | 1971–1980 | +7.850 | 1 | Continue |
| 3 | 1981–1990 | +3.142 | 2 | Continue |
| 4 | 1991–2000 | +10.034 | 3 | Stop: candidate |

Evidence: `*_environment.evidence.json`; summary reports `processed=4`, `candidate_found=true`, `reason="stop"` and `truncated=false`.

The final difference exceeds the threshold by only 0.034 points. The result is sensitive to the declared threshold and windows. Availability of history does not demonstrate that memory improved analytical quality.

## 6. “How do I know the result and the procedure are correct?”

**user:** Verify the finding and confirm that the required operations used the original observations.

**agentic-systems:** Result and trajectory checks passed for live Discovery under both frameworks. Local acceptance also covered an Agent, a System, an Environment and rejecting controls.

**context:** A numerical oracle using `math.fsum` checks the result independently of the comparison Tool. Trajectory checks inspect operation order, successful status and exact original values.

**internals:** Eval executes the declared unit and applies checks to its `RunResult`. Separate negative evaluations retain evidence of deliberately rejected behavior.

**grammar:** `Eval` → `unit` + `cases` + `checks` → evaluation result.

**route:** Case → actual execution → result checks + trajectory checks → acceptance evidence.

| Evaluation | Observed outcome |
|---|---|
| Local Agent acceptance | PASS |
| Local Discovery System acceptance | PASS |
| Local Environment acceptance | PASS |
| Deliberately incorrect expected difference | Rejected as intended |
| Invalid odd-sized comparison windows | Rejected as intended |
| Live Discovery result and trajectory, Native | PASS |
| Live Discovery result and trajectory, OpenAI Agents | PASS |

Evidence: `06_*` and `*_eval.evidence.json`. A failed negative-control execution can be the correct test outcome. Structural invariants are checked separately from analytical correctness.

Eval is fail-fast. Memory isolation is process-local and starts from existing toolkit history; it does not isolate SDK sessions or external effects. Use separate evaluations when each negative case needs a report.

## 7. “Can I change the framework and preserve the application?”

**user:** Run the actors through OpenAI Agents while retaining Bedrock, IAM and Qwen3 32B.

**agentic-systems:** Both Native and OpenAI Agents completed description, the four-episode Environment and the live Discovery evaluation with the same numerical results and decisions.

**context:** Same dataset, Tools, Skills, graph structure, provider and model; fresh application Memory per profile. Sessions stay outside serialized configuration.

**internals:** Reconstruct the actors using the selected framework. Native uses `max_turns=1`; OpenAI Agents uses `max_turns=2` to allow Tool selection and final response. Both use `max_tool_calls=1` per actor.

**grammar:** Independent framework and runtime selection, preserving graph composition and external Evals.

**route:** Selected framework → Bedrock actor → Tool → graph continuation → evidence.

**OpenAI Agents is the framework; Bedrock remains the provider.** LangGraph orchestrates the surrounding graphs. Actors and actuators are architectural roles implemented through `Agent`.

| Layer | Role in this example |
|---|---|
| Tool | Deterministic operation and argument validation |
| Skill | Reusable capability group and instructions |
| Runtime | Provider, model, borrowed session and operational limits |
| Framework | Native or OpenAI Agents actor execution |
| Graph | Explicit execution edges and state flow |
| Agent | Model actor or graph-backed actuator |
| System | Application coordination |
| Context | Immutable reference data and sources |
| Memory | Bounded local episode history |
| Environment | Records, episode updates and stopping |
| Eval | Result and trajectory acceptance |
| RunResult | Outputs, failures, usage and execution evidence |

The framework comparison is observed compatibility for this scenario, not universal feature parity.

## Observed framework comparison

Numbers cover description + Environment + live Discovery Eval. The two profiles were executed separately.

| Measurement | Bedrock / Native | Bedrock / OpenAI Agents |
|---|---:|---:|
| Description selection | PASS | PASS |
| Environment and stopping check | PASS | PASS |
| Discovery result/trajectory Eval | PASS | PASS |
| Environment episodes | 4 | 4 |
| Environment Tool calls | 20 | 20 |
| Live inference requests | 20 | 20 |
| Input tokens | 53,039 | 51,920 |
| Output tokens | 1,741 | 1,636 |
| Total tokens | 54,780 | 53,556 |
| Structural invariants across 13 saved results | PASS | PASS |

OpenAI Agents used about 2.2% fewer tokens in these executions. A single run per profile is insufficient to establish an efficiency ranking or a reliability rate.

History increased Environment input tokens substantially:

| Episode | Native | OpenAI Agents |
|---|---:|---:|
| First | 4,152 | 4,049 |
| Fourth | 17,068 | 16,508 |

These counts aggregate both actors per episode. Compact history is a potential optimization; it requires its own evaluation.

## Inspect and export the execution

With a result from the notebook:

```python
evidence = result.evidence()
lineage = result.lineage().to_dict()
trace = result.trace()
validation = result.check_invariants()

print(result.human_results())
for execution in result.walk():
    print(execution.execution_id, execution.status)
```

`compile()` prepares a definition without business execution or inference. `run()` and `arun()` execute it; direct execution compiles internally. Async execution alone does not introduce parallel branches.

| Saved artifact | Purpose |
|---|---|
| `manifest.json` | SDK/dependency versions, source hashes and profile configuration |
| `*.evidence.json` | Results, descendants, Tool arguments and outputs, errors and usage |
| `*.lineage.json` | Relationships among executions and Tools |
| `*.trace.json` | Bounded execution projection |
| `*.invariants.json` | Structural checks |
| `*.runtime.json` | Serialized runtime configuration, excluding the borrowed session |
| `live_summary.json` | Per-profile status and failure stage |
| `budget.json` | Cumulative HTTP sends, remaining allowance and cap-change history |
| `summary.json` | Completed notebook summary |
| `<run>_bundle.json` | Combined JSON evidence; excludes notebook checkpoints |

The live runner exports saved evidence before re-raising a stage failure. `summary.json` is produced only when the final summary cell runs. `write_run_bundle()` can also be called manually after a failure.

An operational failure is surfaced before checking model selection. Insufficient allowance is reported as `BLOCKED_BUDGET`, rather than an incorrect Tool-selection verdict. No silent model, provider or Python fallback is used.

## Verification boundaries and release scope

The baseline validates this example with Python/Native and two live Bedrock profiles on SDK 2.1.8. The live Environment contains the coordinated Discovery/Review operations; blocks 3–5 were not all executed as separate live acceptance campaigns.

The business output is grounded in Tool results. Generated intermediate prose is not comprehensively evaluated: Native used the phrase “significant increase” without a significance test. The deterministic report retains the descriptive limitation. Extending text evaluation is separate work.

Memory is bounded and process-local. Borrowed Boto3 sessions must be supplied in each process. Timeouts do not guarantee termination or rollback. The persistent HTTP ledger bounds send count, not monetary spend or tokens. Neither this example nor structural invariants certify all SDK integrations.

| Target | Scope |
|---|---|
| 2.1.9 | Core grammar, executable real-data example, visible evidence and the demonstrated Native/OpenAI Agents paths; release-candidate verification still required |
| 2.1.10 | Explicit Agent contracts and policies, completion semantics including `any_of`, interactions with limits, and the associated framework/provider test matrix |

Before publishing the 2.1.9 claim, rerun against its exact candidate artifact, retain the 2.1.8 baseline, and compare numerical outputs, Tool arguments, episode stopping, negative controls and invariants. Publish the executed notebook and selected evidence with the JSON snapshot so readers can inspect the run directly.
