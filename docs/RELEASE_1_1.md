# Agentic Systems 1.1 Release

Version: `1.1.0`.
Status: promoted on 2026-07-19 after automated and manual gates passed.

## Product claim

> Agentic Systems 1.1 establishes verifiable coherence between its API,
> documentation, tutorials and tests.

```text
API == Docs == Tutorials == Pytests
```

## Verified evidence

```text
pytest: 392 passed
coverage: 100.00% (6,193 statements, 0 missing)
canonical notebooks: 18/18 executed, 0 failed
PUBLIC_API: 111 symbols
RunResult invariants: normative contract plus contradiction and round-trip tests
package import: top-level toolkit surface verified
```

See `MANUAL_NOTEBOOK_MATRIX_1_1.md` for notebook and Provider evidence.

## Stable construction surface

```python
import agentic_systems as toolkit

toolkit.tool(...)
toolkit.skill(...)
toolkit.agent(...)
toolkit.system(...)
toolkit.graph(...)
toolkit.environment(...)
toolkit.eval(...)
```

`toolkit.system(...)` is the canonical construction route. The `AgenticSystem` class remains public for typing and extension. Maintainer code that needs the historical module object uses `importlib.import_module("agentic_systems.system")`.

## Claim boundary

Python-runtime execution is verified live and locally. OpenAI, Bedrock and vLLM
have controlled conformance and failure-path evidence, but this release does not
claim live external account, model, GPU server or deployed application runs.

## Package evidence

```text
wheel: agentic_systems-1.1.0-py3-none-any.whl
sdist: agentic_systems-1.1.0.tar.gz
twine check: passed for both artifacts
isolated venv install: passed
isolated import and CLI version: 1.1.0
submodule compatibility: agentic_systems.system preserved
```
