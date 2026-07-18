# Test Matrix

The test suite is organized by public API surface under `tests/api/`. Each file
answers one question: which Agentic Systems symbol or integration contract is it
protecting?

| API file | Purpose |
|---|---|
| `test_runtime.py` | Runtime selection, providers, CLI/runtime diagnostics, python-runtime, OpenAI, Bedrock and vLLM paths. |
| `test_scheduler.py` | Scheduler config, retries, timeout, concurrency and execution guards. |
| `test_tool.py` | Tool class, decorators, contracts and tool expectations. |
| `test_skill.py` | Skill loading, manifests, skill-backed agents and skill runtime contracts. |
| `test_agent.py` | Agent construction, direct execution, contracts, runtime paths and policy behavior. |
| `test_compose_result.py` | Canonical composed result helper and notebook output envelopes. |
| `test_human_result.py` | Human output rendering, plain/Rich/debug/lineage/eval/environment paths. |
| `test_lineage_memory.py` | RunResult, final answer, output contracts and Lineage Memory behavior. |
| `test_system.py` | AgenticSystem, public tool registry, tutorial structure and system-level regressions. |
| `test_graph.py` | Graph state, normalized graph output and multi-agent graph contracts. |
| `test_environment_eval.py` | AgenticEnvironment, eval reports, rewards and environment summaries. |
| `tests/contracts/test_run_result_invariants.py` | RunResult consistency, partial failure, evidence, lineage and JSON serialization invariants. |
| `tests/composition/` | Tool and Skill identity, conflicts, precedence, reuse, coherence and inspectable composition. |
| `test_integrations_openai_agents.py` | OpenAI Agents facade behavior without live OpenAI calls. |
| `test_integrations_langgraph.py` | LangGraph facade and optional dependency branches. |
| `test_integrations_strands.py` | Strands facade behavior and framework metadata. |

`tests/api/_legacy_modules/` stores migrated historical test bodies. The public
entrypoints are still the `tests/api/test_*.py` files above. The loader preserves
the old `tests/test_*.py` path semantics so fixtures and repo-root calculations
continue to work while the suite remains grouped by API.

Coverage policy:

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

Current verified status: `334 passed, 0 skipped`, `100.00%` real coverage.
