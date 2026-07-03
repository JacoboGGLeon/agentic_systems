# Agentic Systems roadmap

## Current State

Agentic Systems is in a production-clean tutorial-first state.

```text
src/agentic_systems/  library package
tutorials/            API walkthroughs
docs/                 current docs
tests/                regression suite
dist/                 built wheel and sdist
```

Removed surfaces:

```text
examples/
src/agentic_systems/examples/
tutorials/tools/
legacy package imports
demo_case / run_tools top-level exports
```

## Active Route

```text
tutorials/00_runtime_api.ipynb
tutorials/00_runtime_provider_api.ipynb
tutorials/00_runtime_scheduler_api.ipynb
tutorials/01_tool_api.ipynb
tutorials/02_agent_api.ipynb
tutorials/03_human_result_api.ipynb
tutorials/04_lineage_memory_api.ipynb
tutorials/05_lineage_memory_strands_api.ipynb
tutorials/06_lineage_memory_openai_runtime_api.ipynb
tutorials/07_lineage_memory_langgraph_single_agent_tools_api.ipynb
tutorials/08_lineage_memory_langgraph_multi_agent_system_api.ipynb
tutorials/09_lineage_memory_environment_eval_api.ipynb
```

## Runtime Boundary

```text
engines      canonical execution names
providers    backend implementations
integrations framework adapters
```

Canonical engines:

```text
python-direct
bedrock-runtime
openai-runtime
```

Framework integrations:

```text
langgraph
openai-runtime
strands
```

## Release Rule

Before handoff:

```bash
python -m pytest -q
python -m compileall -q src tests tutorials
python -m build --no-isolation
```

The wheel and sdist must not include `tests/`, `tutorials/`, `docs/`, or `agentic_systems/examples`.
