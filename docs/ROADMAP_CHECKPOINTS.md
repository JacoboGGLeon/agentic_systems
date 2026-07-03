# Roadmap And Release Notes

This file keeps the historical filename for existing references, but the
content describes the current product state.

## Current State

Agentic Systems is tutorial-first and API-first:

```text
src/agentic_systems/  stable package API
tutorials/            executable API walkthrough
docs/                 operating documentation
```

The active surface is:

```text
tools -> skills -> agents -> systems -> graphs -> environments -> evals
```

with cross-cutting:

```text
runtime/provider, scheduler, contracts, lineage memory, human output, CLI
```

## Closed Cleanup Themes

```text
- tutorials/ is the canonical learning path.
- examples/ is not an active root layer.
- public API is exposed from `import agentic_systems as lab`.
- provider names are canonical: python-direct, bedrock-runtime, openai-runtime.
- graph/framework integrations stay optional.
- CLI diagnostics are available through `agentic-systems`.
```

## Forward Roadmap

| Area | Next work |
|---|---|
| Providers | Keep `auto` selection observable and provider errors explicit. |
| Tutorials | Keep every notebook aligned to `docs/API.md` and `PUBLIC_API`. |
| CLI | Add only package diagnostics and smoke helpers. |
| Docs | Prefer current API docs over migration narrative. |
| Tests | Add focused tests for public API and tutorial coverage. |

## Release Gate

Before sharing a bundle:

```bash
python -m pytest -q
python -m compileall -q src tests tutorials
agentic-systems doctor --json
agentic-systems runtime --provider auto --json
```

The release is not ready if docs teach an import path that tutorials do not use.
