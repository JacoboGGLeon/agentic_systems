# Financial System, step by step · 2.1.4

[Python notebook](01_financial_system.ipynb) · [English reading view](01_financial_system.md) · [Recorded mixed execution](02_financial_system_mixed.executed.ipynb) · [Recorded native/local execution](03_financial_system_native_local.executed.ipynb).

The notebooks expose Pydantic, runtimes, Tools, Skills, Context, Memory, Agents, Graph, a System decision, Environment reward and isolated Eval. No application constructor is hidden in another example.

| Stage | Python | Recorded mixed profile |
|---|---|---|
| Fee | Python/native | OpenAI gpt-4.1-mini/native |
| Audit | Python/native | Bedrock Qwen3-32B/Strands |
| Local verification | Python/native | Ollama local Qwen3 4B/Strands |
| Final verification | Python/native | Ollama Cloud Gemma4:31b/OpenAI Agents |

All graphs use LangGraph. Amounts are MXN cents; no funds are transferred. Models select Tools; Python computes and applies rules. A 5000-cent payment is approved once and reviewed when repeated.

The first local/native campaign failed because endpoint selection used global Ollama configuration. That failed attempt remains evidence, not PASS. A historical workaround used explicit local/Strands configuration. A later corrected-wheel campaign restored local/native alongside OpenAI/native, Bedrock/Strands and Cloud/OpenAI Agents; sync/arun local/cloud checks are recorded in its own report. These campaigns do not automatically certify newly built artifacts.

[Original campaign](../../revisions/2.1.4/financial-mixed/01/REPORT.md) · [Connection correction and budget](../../revisions/2.1.4/ollama-connection-fix/01/live/REPORT.md).

The default execution profile is Python. Mixed requires environment credentials and an authorized active budget, not merely a profile change. Reading saved outputs consumes no inference. Complete RunResult, Context, Memory and lineage captures are retained with campaign evidence.

This notebook does not validate Bedrock amount:null, IAM/ADA, GPU vLLM, handoffs, MCP/A2A or Studio UI.
