# Boundaries

This document defines where new code belongs.

## Namespace Ownership

| Namespace | Owns | Must not own |
|---|---|---|
| `agentic_systems.core` | runtime-agnostic contracts, results, scheduler and runtime config | provider SDK calls, framework compilation, business logic |
| `agentic_systems.providers` | backend/model access for `python-direct`, `bedrock-runtime`, `openai-runtime` | framework orchestration or tutorial-specific workflows |
| `agentic_systems.integrations` | adapters to external frameworks and bridges | core contracts or provider implementation details |
| `agentic_systems.engines` | internal execution modules | new public API design |
| `tutorials/` | executable API learning path | library implementation |
| `tutorials/skills/` | reusable tutorial skills and assets | package core code |
| `docs/` | current usage, API and operating rules | historical compatibility as recommended behavior |

## Provider vs Integration

Use this rule:

```text
provider    decides where model/tool execution happens
integration adapts Agentic Systems to an external framework
```

Examples:

```text
python-direct      provider
bedrock-runtime    provider
openai-runtime     provider
langgraph          integration
strands            integration
```

## Public vs Internal

Public user code should use:

```python
import agentic_systems as toolkit
```

Internal modules can change. Avoid documenting direct imports from:

```text
agentic_systems.engines.*
agentic_systems.providers.* internals
agentic_systems.integrations.* internals
```

unless the document is explicitly for maintainers.

## Rules For New Work

```text
1. Add new primitives to core only if they are provider-agnostic.
2. Add backend/model behavior under providers.
3. Add framework adapters under integrations.
4. Add teaching material under tutorials.
5. Add diagnostics to the CLI only when they inspect the package/runtime.
6. Keep optional dependencies optional at import time.
7. Add tests for every public API change.
```

## Documentation Boundary

Docs should describe the current API first. Historical names can remain in test
filenames, but user-facing docs should not teach old migration paths as normal
usage.
