# Agentic Systems 1.1 Manual Notebook Matrix

Release: `1.1.0`.
Execution date: 2026-07-19.

## Environment

```text
OS: Windows
Python: 3.14.2
execution: fresh python3 kernel per notebook
working directory: repository root
external credentials: disabled for the run
live RUN_* flags: 0
local Agent providers: python-runtime
AGENTIC_SYSTEMS_GRAPH_ENGINE=portable
source notebooks modified by execution: no
```

Execution used in-memory notebook copies; outputs were not persisted into the
source notebooks. This document is the durable release record.

## Results

| Notebook | Result | External boundary | Evidence |
|---|---|---|---|
| `00_runtime_api.ipynb` | pass | none | Runtime profiles and auto-selection description executed. |
| `00_runtime_bedrock_provider_api.ipynb` | pass with explicit skip | Bedrock live disabled | The public runtime -> system -> agent -> RunResult route was constructed; the external model call was skipped. |
| `00_runtime_openai_provider_api.ipynb` | pass with explicit skip | OpenAI live disabled | Runtime, System, Tool and Agent construction executed through the public API; no live claim. |
| `00_runtime_scheduler_api.ipynb` | pass | none | Scheduler limits and deterministic runtime executed. |
| `00_runtime_vllm_provider_api.ipynb` | pass with explicit skip | vLLM live disabled | Public environment snapshot and runtime route executed; the external endpoint call remained opt-in. |
| `01_tool_api.ipynb` | pass | none | Tool contracts, execution and validation executed. |
| `02_skill_api.ipynb` | pass | none | `toolkit.skill(...)`, composition and reuse executed. |
| `03_agent_api.ipynb` | pass | optional LM not required | Deterministic Agent path and full Tool evidence executed. |
| `04_human_result_api.ipynb` | pass | none | RunResult projections and human rendering executed. |
| `05_lineage_memory_api.ipynb` | pass | none | Lineage construction and compact context executed. |
| `06_integrations_strands_api.ipynb` | pass with explicit skip | Strands SDK not invoked | Declarative-only profile inspection and live gate executed. |
| `07_integrations_openai_runtime_api.ipynb` | pass with explicit skip | OpenAI Agents SDK not invoked | Style-only profile inspection and async live gate executed. |
| `08_system_api.ipynb` | pass | none | System registration, execution and static inspection executed. |
| `09_graph_api.ipynb` | pass | portable graph forced | Graph state, nodes, edges and result projection executed. |
| `10_environment_eval_api.ipynb` | pass | none | Environment episodes, rewards and eval report executed. |
| `11_single_agentic_system_api.ipynb` | pass | provider selectable | Full deterministic Tool, Agent and Eval path passed with python-runtime. |
| `12_multi_agentic_system_api.ipynb` | pass | provider selectable | Two real Agent runs and RunResult composition passed with python-runtime. |
| `13_multi_agentic_graph_api.ipynb` | pass | portable graph forced | Multi-agent Graph path, real RunResults and state evidence executed. |

Summary:

```text
notebooks: 18
pass: 18
fail: 0
external live Provider claims: 0
```

## Provider Evidence Matrix

| Provider / Framework | 1.1 evidence | Claim boundary |
|---|---|---|
| `python-runtime` | Live deterministic notebook execution and conformance tests | Supported locally. |
| `openai-runtime` | Provider conformance, failure paths and API-first notebook construction | Live account/model execution not claimed. |
| `bedrock-runtime` | Provider conformance, failure paths and API-first notebook skip | Live AWS execution not claimed. |
| `vllm-runtime` | OpenAI-compatible conformance, public environment snapshot and safe opt-in notebook | Live GPU server/model execution not claimed. |
| `provider="auto"` | Resolution and observability tests; local tutorial degradation | Credential or endpoint availability not inferred. |
| LangGraph | Native adapter plus portable backend and projection tests | Deployed Graph application not claimed. |
| OpenAI Agents-style | Style-only metadata preservation | Agents SDK adapter not claimed. |
| Strands | Declarative-only metadata preservation | Strands SDK adapter not claimed. |

## Promotion Decision

The manual notebook gate passed. Together with the automated package, API,
contract and coverage gates, this matrix supports promotion from `1.1.0rc1` to
`1.1.0` without expanding any live Provider claim.
