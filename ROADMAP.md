# Agentic Systems Roadmap

Current stable release: `1.1.2`.
Active maintenance checkpoint: `1.1.3` documentation architecture.

Agentic Systems 1.1.2 closes the compatibility-preserving cleanup of the test
architecture and the internal Bedrock partition. Checkpoint 1.1.3 consolidates
product documentation without adding API or runtime behavior. Completed work
and measured release evidence belong in the changelog and release reports, not
in this forward-looking roadmap.

## Direction During And After 1.1.3

Future work must earn its place through a concrete user contract and evidence.
The preferred order is:

1. Raise Bedrock coverage through fake-client tests while keeping the ratchet
   monotonic and avoiding network-dependent CI.
2. Improve documentation discoverability and tutorial accessibility without
   introducing a second API or competing learning path.
3. Strengthen provider conformance evidence where real integrations exist.
4. Remove accidental complexity before considering new public symbols.

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
