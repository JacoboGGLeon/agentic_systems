# Agentic Systems Roadmap

Current stable release: `1.1.3`.
Next major line: `2.0` Provider x Framework execution architecture.

Agentic Systems 1.1.3 closes the compatibility-preserving cleanup of the test
and documentation architecture without adding API or runtime behavior.
Completed work and measured release evidence belong in the changelog and
release reports, not in this forward-looking roadmap.

## Direction After 1.1.3

Future work must earn its place through a concrete user contract and evidence.
The preferred order is:

1. Make Native, LangGraph, OpenAI Agents and Strands real execution boundaries
   over the four canonical Providers.
2. Preserve the canonical 1.1 API while removing compatibility-only modules,
   aliases and duplicated bridges in the 2.0 major line.
3. Raise Provider and Framework coverage through controlled transports and
   scheduled live evidence without making pull requests network-dependent.
4. Keep framework SDKs optional and lazy while forwarding their native options

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
