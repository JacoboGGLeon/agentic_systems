# Acceptance testing

Offline gates:

- every public Tool validates its input and returns a dictionary;
- every runtime Skill resolves its declared tools;
- every Agent and System passes inspect;
- notebooks parse and execute deterministic cells from a fresh kernel;
- direct notebook, UI, tests and docs call the same public constructor;
- `.env` is the canonical runtime contract and the UI does not override it;
- bundles contain required assets, no credentials and valid checksums.

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

For a conversational application, test the same System directly and through its
UI. The UI is a presentation adapter, not a second implementation of the
agentic logic.
