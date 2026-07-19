# Pytest Coverage Report

Cutoff: 2026-07-18, release candidate `1.1.0rc1`.

## Verified Result

The measurement comes from the repository virtual environment:

```powershell
.\.venv_agentic_systems\Scripts\python.exe -m pytest `
  --basetemp=C:\tmp\agentic_systems_pytest_tmp `
  -o cache_dir=C:\tmp\agentic_systems_pytest_cache `
  --cache-clear `
  --cov=agentic_systems `
  --cov-report=term-missing `
  --cov-report=json:C:\tmp\agentic_systems_coverage.json `
  -q
```

```text
359 passed, 0 skipped
TOTAL statements: 6079
TOTAL missing: 0
TOTAL coverage: 100.00%
```

## Covered Surfaces

- public API, CLI, Runtime, Scheduler, Tools, Skills, Agents, and Systems;
- RunResult, contracts, output, lineage, and human rendering;
- Provider conformance with controlled clients and failure paths;
- Framework/Graph boundaries and optional dependency behavior;
- Environment/Eval ownership and reproducibility;
- static System inspection and non-execution;
- RC version, documentation, and tutorial source contracts.

Coverage of adapter code with controlled clients is not evidence of live account,
credential, endpoint, GPU, model, Strands SDK, or OpenAI Agents SDK execution.

## Tutorial Gate

All 19 canonical notebooks parse, use the public import, contain no persisted
outputs, and compile statically. Full notebook execution is the separate manual
gate in `RELEASE_CANDIDATE_1_1.md`.
