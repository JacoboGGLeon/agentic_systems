# Integrations and boundaries · 2.1.9

LangGraph orchestrates graphs. native, openai-agents and strands implement actors. Runtime selects python-runtime, openai-runtime, bedrock-runtime, ollama-runtime or vllm-runtime. An Agent with a graph does not itself select a provider; each actor node has its own configuration.

| Route | Configuration / prerequisites | Limits |
|---|---|---|
| Python | provider='python-runtime' | Deterministic actor; not LM reasoning |
| OpenAI | Explicit model; openai extra; external credentials | Model-specific Tool/schema support |
| Bedrock | Explicit model/region; bedrock extra; IAM or bearer profile | Injected session selects IAM; nullable-field limitation remains |
| Ollama | Explicit endpoint/model and credentials when required | Local server and cloud are separate connection profiles |
| vLLM | Client endpoint/model; separate server environment | GPU/server compatibility is not implied by SDK Python support |

[Provider lessons](../tutorials/README.md) show configuration. [Actor contracts](ACTOR_CONTRACTS.md) specify required Tools and acceptance. Native/OpenAI Agents/Strands share RunResult and the owner execution interface; this is not universal feature parity. Framework-specific handoffs, sessions, guardrails, MCP/A2A require their own supported configuration and verification.

## Evidence states

Installed, configured, offline-tested and live-tested are different claims. doctor checks dependency presence, not authentication or service access. Mocked transport validates an adapter path, not a real model. Historical campaigns remain tied to their hashes: [2.1.5 providers](VALIDATION_215_20261108.md), [2.1.7 AWS sessions](AWS_SESSION_VALIDATION_217.md). Neither certifies a new 2.1.9 wheel.

EMR runtime-role access and distributed PySpark remain unverified by the recorded 2.1.7 SageMaker campaigns. Memory/continuations remain process-local; no rollback or durable recovery is claimed for 2.1.9. Live requests require configured credentials and a persistent campaign budget including errors and retries. No silent model/provider substitution.
