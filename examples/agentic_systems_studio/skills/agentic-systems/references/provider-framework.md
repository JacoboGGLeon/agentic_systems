# Provider and framework selection

Providers answer where model inference runs. Frameworks answer how an Agent is
implemented. System execution plans answer how Agents or complete Systems are
connected. Do not merge these three choices.

Canonical reasoning providers are openai-runtime, ollama-runtime,
bedrock-runtime, vllm-runtime and auto. python-runtime is deterministic and
does not become a language model provider.

Canonical optional frameworks are langgraph, openai-agents and strands.
agentic-systems or no framework means the native Agentic Systems agent path.

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
