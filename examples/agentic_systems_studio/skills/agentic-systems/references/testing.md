# Acceptance testing

Offline gates:

- every public Tool validates its input and returns a dictionary;
- every runtime Skill resolves its declared tools;
- every Agent and System passes inspect;
- Mermaid stage identities equal executable stage identities;
- SQLite inventory equals the catalog;
- scaffolding is non-destructive by default;
- notebooks parse and execute deterministic cells from a fresh kernel;
- CLI, UI, tests and docs call the same public constructors;
- nested bundles contain required assets and pass checksum verification.

Live gates:

- use the same prompt and model class where a provider comparison is intended;
- record provider, framework, model, elapsed time, normalized RunResult and
  child lineage;
- distinguish unavailable dependency, unconfigured credential, unsupported
  combination, quota denial and execution failure;
- do not substitute a provider after a failure;
- run OpenAI and Ollama locally when configured;
- run Bedrock through both API-key and IAM paths only when each is available;
- run vLLM on the target GPU environment.

A release claim should enumerate tested combinations. Static matrix support is
not equivalent to a successful live invocation.
