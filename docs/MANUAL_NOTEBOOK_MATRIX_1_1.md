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
AGENTIC_SYSTEMS_FORCE_LOCAL_TUTORIALS=1
source notebooks modified by execution: no
```

Executed copies and the machine-readable run report were written outside the
repository. This document is the durable release record.

## Results

| Notebook | Result | External boundary | Evidence |
|---|---|---|---|
| `00_runtime_api.ipynb` | pass | none | Runtime profiles and auto-selection description executed. |
| `00_runtime_bedrock_provider_api.ipynb` | pass with explicit skips | Bedrock live disabled | Client, STS, control-plane, Converse and embedding calls reported as skipped. |
| `00_runtime_openai_provider_api.ipynb` | pass | OpenAI live disabled | Runtime, scheduler, policy and Tool/Agent construction executed; no live claim. |
| `00_runtime_scheduler_api.ipynb` | pass | none | Scheduler limits and deterministic runtime executed. |
| `00_runtime_vllm_provider_api.ipynb` | pass with explicit skips | GPU/server unavailable | Install, server and inference are opt-in; skips remained observable. |
| `01_tool_api.ipynb` | pass | none | Tool contracts, execution and validation executed. |
| `02_skill_api.ipynb` | pass | none | `toolkit.skill(...)`, composition and reuse executed. |
| `03_agent_api.ipynb` | pass | optional LM not required | Deterministic Agent path and full Tool evidence executed. |
| `04_human_result_api.ipynb` | pass | none | RunResult projections and human rendering executed. |
| `05_lineage_memory_api.ipynb` | pass | none | Lineage construction and compact context executed. |
| `06_integrations_strands_api.ipynb` | pass | Strands SDK not invoked | Declarative-only boundary and core execution demonstrated. |
| `07_integrations_openai_runtime_api.ipynb` | pass | OpenAI Agents SDK not invoked | Style-only boundary and core execution demonstrated. |
| `08_system_api.ipynb` | pass | none | System registration, execution and static inspection executed. |
| `09_graph_api.ipynb` | pass | optional LangGraph boundary | Graph state, nodes, edges and result projection executed. |
| `10_environment_eval_api.ipynb` | pass | none | Environment episodes, rewards and eval report executed. |
| `11_single_agentic_system_api.ipynb` | pass with explicit skip | optional LM explainer | Required deterministic path passed; optional explanation skipped. |
| `12_multi_agentic_system_api.ipynb` | pass with explicit skip | optional LM reviewer | Required solver/judge path passed; optional review skipped. |
| `13_multi_agentic_graph_api.ipynb` | pass | optional LM degradation allowed | Multi-agent Graph path and state evidence executed. |

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
| `openai-runtime` | Controlled-client conformance, failure paths and API notebook construction | Live account/model execution not claimed. |
| `bedrock-runtime` | Controlled-client conformance, failure paths and explicit notebook skips | Live AWS execution not claimed. |
| `vllm-runtime` | OpenAI-compatible conformance, safe opt-in notebook and explicit skips | Live GPU server/model execution not claimed. |
| `provider="auto"` | Resolution and observability tests; local tutorial degradation | Credential or endpoint availability not inferred. |
| LangGraph | Adapter and projection tests | Deployed Graph application not claimed. |
| OpenAI Agents-style | Style-only metadata preservation | Agents SDK adapter not claimed. |
| Strands | Declarative-only metadata preservation | Strands SDK adapter not claimed. |

## Promotion Decision

The manual notebook gate passed. Together with the automated package, API,
contract and coverage gates, this matrix supports promotion from `1.1.0rc1` to
`1.1.0` without expanding any live Provider claim.
