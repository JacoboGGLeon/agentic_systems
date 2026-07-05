# Agentic Systems

<p align="center">
  <img src="docs/assets/logo_agentic_systems.png" alt="Agentic Systems logo" width="360" />
</p>


Agentic Systems is a Python library for building, running and evaluating
auditable agentic systems with tools, skills, agents, systems, graphs,
environments, evals, contracts, lineage memory and stable human output.

Use the public facade:

```python
import agentic_systems as toolkit
```

## Quality Gate

Current verified test status is documented in [`docs/PYTEST_COVERAGE_REPORT.md`](docs/PYTEST_COVERAGE_REPORT.md):

```text
287 passed, 1 skipped
Coverage: 100.00%
TOTAL statements: 5153
TOTAL missing: 0
```

## What It Exposes

```text
Tool        executable capability
Skill       package of tools, instructions, contracts and assets
Agent       instructions + runtime + tools/skills + contracts
System      workspace that registers and composes tools, skills and agents
Graph       state + nodes + edges orchestration
Environment episodic execution with reward and history
Eval        batch validation and scoring
```

Cross-cutting APIs:

```text
runtime/provider
scheduler
contracts and policies
Lineage Memory
RunResult/final answer
human_result
CLI diagnostics
```

## Providers And Integrations

Canonical providers:

```text
python-direct
openai-runtime
bedrock-runtime
auto
```

Optional integrations:

```text
LangGraph
Strands
OpenAI runtime facade
```

`provider="auto"` is explicit selection mode. Use `runtime.describe()` or the
CLI to see what the current environment selects before executing a model.

OpenAI runtime reads `OPENAI_API_KEY`, `AGENTIC_SYSTEMS_OPENAI_MODEL_ID`,
`OPENAI_MODEL_ID`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, `OPENAI_ORG_ID` and
`OPENAI_PROJECT` from the environment or `.env`. Diagnostics show safe flags,
not secret values.

## Quick Start

```python
import agentic_systems as toolkit

@toolkit.tool
def add(a: int, b: int) -> dict:
    return {"result": a + b}

runtime = toolkit.runtime(provider="python-direct")
agent = toolkit.agent(name="calc", tools=[add], runtime=runtime)

result = agent.run({"tool": "add", "input": {"a": 2, "b": 3}}, mode="eval")
toolkit.human_result(result)
```

## CLI

```bash
agentic-systems version
agentic-systems doctor --json
agentic-systems runtime --provider auto --json
agentic-systems api --tier public --json
agentic-systems public-api --all --json
```

## Tutorials

The official learning path is `tutorials/`:

```text
tutorials/00_runtime_api.ipynb
tutorials/00_runtime_bedrock_provider_api.ipynb
tutorials/00_runtime_openai_provider_api.ipynb
tutorials/00_runtime_scheduler_api.ipynb
tutorials/01_tool_api.ipynb
tutorials/02_skill_api.ipynb
tutorials/03_agent_api.ipynb
tutorials/04_human_result_api.ipynb
tutorials/05_lineage_memory_api.ipynb
tutorials/06_integrations_strands_api.ipynb
tutorials/07_integrations_openai_runtime_api.ipynb
tutorials/08_system_api.ipynb
tutorials/09_graph_api.ipynb
tutorials/10_environment_eval_api.ipynb
```

There is no active `examples/` root. Tutorials both explain and exercise the API.

## Docs

```text
docs/API.md
docs/CLI.md
docs/ARCHITECTURE.md
docs/BOUNDARIES.md
docs/ONBOARDING_FIRST_RUN.md
docs/RUNRESULT_FINAL_ANSWER.md
docs/SMOKE_CHECKLIST_2_4_9.md
docs/CONTRIBUTING_CHECKLIST.md
docs/ROADMAP_CHECKPOINTS.md
```

## Validation

```bash
python -m pytest -q
python -m compileall -q src tests tutorials
agentic-systems doctor --json
```
