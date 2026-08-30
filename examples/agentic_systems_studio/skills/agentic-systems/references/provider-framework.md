# Provider and framework selection

Providers answer where model inference runs. Frameworks answer how an Agent is
implemented. System execution plans answer how Agents or complete Systems are
connected. Do not merge these three choices.

Canonical provider identifiers are python-runtime, openai-runtime,
ollama-runtime, bedrock-runtime and vllm-runtime. python-runtime is
deterministic and does not become a language model provider. auto is a runtime
selection mode, not a sixth Provider.

Canonical framework identifiers are native, langgraph, openai-agents and
strands. native means the Agentic Systems agent loop; the other three select
their real optional SDK adapters.

For each requested combination report four independent facts:

1. dependency installed;
2. credentials or endpoint configured;
3. static compatibility supported;
4. live request verified.

auto resolves from configured provider signals and explicit priority. If more
than one provider is configured, never imply that both run; report which one
was selected and why.

OpenAI uses environment credentials. Ollama uses a local endpoint and model.
Bedrock can use its bearer API key environment variable or the normal AWS
credential chain, including an IAM role in a sandbox. vLLM uses its configured
OpenAI-compatible endpoint. Keep all secrets outside generated artifacts.
