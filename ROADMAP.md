# Agentic Systems Roadmap

Current stable release: `2.0.0`.
Current release line: `2.1`. Next development line: `2.2`.

Agentic Systems 2.0 establishes the five-Provider by four-Framework execution
architecture, the common RunResult contract, dual Bedrock authentication,
ToolSet, explicit System execution plans and the Python/CLI tutorial mirrors.
Completed work and measured release evidence belong in the changelog and
release reports, not in this forward-looking roadmap.

## Direction After 2.0

Future work must earn its place through a concrete user contract and evidence.
The preferred order is:

1. Automate scheduled live evidence for Bedrock IAM/bearer, vLLM and Ollama
   without making ordinary pull requests network-dependent.
2. Introduce compositional algebra at the System execution-plan boundary
   without redefining Agent pipelines or the Agent/System distinction.
3. Design portable Open Agent Skill adapters, resources and script isolation
   as one versioned contract rather than provisional parameters.
4. Keep Provider and Framework SDKs optional and lazy while expanding native
   option forwarding and conformance evidence.

## Guardrails

- Preserve the single `import agentic_systems as toolkit` teaching path.
- Keep Runtime, Provider and Framework responsibilities explicit.
- Keep optional SDKs lazy at base import time.
- Add no public API without a documented contract, tutorial need and tests.
- Treat historical checkpoints as evidence, not as the current product plan.
- Keep releases reproducible from a clean tag and independently installable
  wheel.

No item in this roadmap is a compatibility promise or release commitment until
it is accepted into a versioned release plan.
