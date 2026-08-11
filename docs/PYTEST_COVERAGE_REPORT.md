# Pytest Coverage Report

Cutoff: 2026-08-10, release `1.1.2`.

## Verified result

Core and Bedrock are intentionally measured as separate blocking gates.

### Core

```powershell
python -m pytest -q `
  --cov=agentic_systems `
  --cov-config=pyproject.toml `
  --cov-report=term-missing
```

```text
381 passed
TOTAL statements: 6194
TOTAL missing: 0
TOTAL coverage: 100.00%
```

The core configuration explicitly omits the public Bedrock facade and the
internal `providers/bedrock/` package.

### Bedrock

```powershell
python -m pytest -q tests/providers/bedrock `
  --cov=agentic_systems.providers.bedrock_runtime `
  --cov=agentic_systems.providers.bedrock `
  --cov-config=.coveragerc-bedrock `
  --cov-report=term-missing
```

```text
27 passed
TOTAL statements: 1151
TOTAL missing: 539
TOTAL coverage: 53.17%
Blocking ratchet: 53.1%
```

The ratchet is upward-only. Tests use controlled clients and require no AWS
credentials or network.

## Covered surfaces

- public API, CLI, Runtime, Scheduler, Tools, Skills, Agents and Systems;
- RunResult, contracts, output, lineage and human rendering;
- Provider conformance with controlled clients and failure paths;
- Framework/Graph boundaries and optional dependency behavior;
- Environment/Eval ownership and reproducibility;
- static System inspection and non-execution;
- release version, documentation, tutorial, artifact and quarantine-absence gates.

Coverage with controlled clients is not evidence of live account, credential,
endpoint, GPU or model execution.

## Tutorial gate

Thirteen deterministic notebooks execute from fresh kernels under pytest. Five
Provider notebooks are checked statically and remain outside live-provider
claims.
