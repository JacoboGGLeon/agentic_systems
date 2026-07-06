# Agentic Systems

<p align="center">
  <img src="https://raw.githubusercontent.com/JacoboGGLeon/agentic_systems/main/docs/assets/logo_agentic_systems.png" alt="Agentic Systems logo" width="360" />
</p>

<p align="center">
  <a href="https://pypi.org/project/agentic-systems/"><img src="https://img.shields.io/pypi/v/agentic-systems.svg" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/agentic-systems/"><img src="https://img.shields.io/badge/python-%3E%3D3.10-blue.svg" alt="Python >=3.10" /></a>
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen.svg" alt="Coverage 100%" />
  <img src="https://img.shields.io/badge/tests-304%20passed%2C%200%20skipped-brightgreen.svg" alt="Tests 304 passed, 0 skipped" />
</p>

**Agentic Systems is a Python framework for building industrial, auditable and provider-agnostic agentic systems.**

It gives you one consistent public API to compose tools, skills, agents, systems, graphs, environments, evals, contracts, lineage memory and stable human-readable outputs. It supports deterministic local execution and language-model-based execution through explicit runtime selection, provider diagnostics and repeatable evaluation contracts.

Use it when you need agentic workloads that are not just demos, but observable, testable, portable and ready for large-volume execution.

```bash
pip install agentic-systems
```

```python
import agentic_systems as toolkit
```

## Why Agentic Systems Exists

Most agent prototypes fail when they move from a notebook to a real workload because the same questions come back every time:

- Which provider is actually running this agent?
- Which tools were available?
- Which tool calls happened?
- What evidence supports the final answer?
- Can the same behavior be evaluated again?
- Can the same agent run locally, with OpenAI, with AWS Bedrock or against a vLLM-compatible endpoint?
- Can deterministic tools and language-model reasoning live under the same execution contract?

Agentic Systems is built around those questions. The library treats agentic computation as an engineered system: explicit runtime, typed tools, contracts, result envelopes, lineage, environment transitions, eval reports and human output are first-class parts of the workflow.

## What You Can Build

Agentic Systems can be used to build:

- deterministic tool systems for auditable local execution;
- reasoning agents backed by language-model providers;
- native `AgenticSystem` workspaces that register tools, skills and agents;
- graph-based orchestration with state, nodes and edges;
- episodic environments with rewards and execution history;
- eval suites with expected outputs and pass/fail reports;
- lineage-aware workflows that explain what happened and why;
- portable agent code that can switch providers through `runtime(provider=...)`;
- integration facades for LangGraph, Strands and OpenAI Agents-style workflows.

## Core Idea

```text
Tools provide capabilities.
Skills package tools, instructions, contracts and assets.
Agents turn context into actions.
Systems register and compose tools, skills and agents.
Graphs coordinate state, nodes and edges.
Environments run episodes over records and rewards.
Evals validate behavior with repeatable cases.
RunResult keeps the final answer, evidence, usage, validation and errors.
Lineage Memory explains how the result was produced.
Human output renders results for notebooks, reviews and users.
```

The goal is not to hide complexity. The goal is to make the complexity explicit, inspectable and reusable.

## Runtime And Providers

Runtime selection is explicit and inspectable:

```python
scheduler = toolkit.scheduler(timeout_s=30, max_retries=0, max_tool_calls=5)
runtime = toolkit.runtime(provider="auto", scheduler=scheduler)
toolkit.show(runtime.describe())
```

Canonical providers:

| Provider | Use |
|---|---|
| `bedrock-runtime` | AWS Bedrock Runtime provider path. |
| `openai-runtime` | Direct OpenAI provider path. |
| `vllm-runtime` | OpenAI-compatible vLLM provider path for local or Colab GPU inference. |
| `python-runtime` | Local deterministic execution for tools, policies and smoke tests. |
| `auto` | Selects a concrete provider from environment signals before execution. |

Default `provider="auto"` priority is `bedrock-runtime`, then `openai-runtime`, then `vllm-runtime`. Override it per call with `provider_priority=[...]` or per environment with `AGENTIC_SYSTEMS_PROVIDER_PRIORITY=bedrock-runtime,openai-runtime,vllm-runtime`. Add `allow_python_fallback=True` only when deterministic fallback is intentional.

Canonical framework/integration facades:

| Framework | Use |
|---|---|
| `langgraph` | LangGraph graph orchestration. |
| `openai-agents` | OpenAI Agents-style integration over the selected runtime. |
| `strands` | Strands integration over the selected runtime. |

Providers and frameworks are deliberately separate. A provider decides where execution runs. A framework decides who owns the outer orchestration loop.

## Provider Configuration

### OpenAI Runtime

Reads configuration from the environment or `.env`:

```text
OPENAI_API_KEY
OPENAI_MODEL
OPENAI_BASE_URL
```

### vLLM Runtime

Reads configuration from the environment or `.env`:

```text
VLLM_BASE_URL
VLLM_MODEL
VLLM_API_KEY
```

`vllm-runtime` expects a running OpenAI-compatible vLLM server. The package does not start or install the GPU server by default.

### Bedrock Runtime

Reads configuration from the environment or `.env`:

```text
BEDROCK_MODEL_ID
AWS_REGION
AWS_DEFAULT_REGION
AWS_PROFILE
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
```

Diagnostics expose safe configuration flags only. They do not print API keys, secret keys or session tokens.

## Quick Start: Deterministic Tool Agent

```python
import agentic_systems as toolkit

@toolkit.tool
def add(a: int, b: int) -> dict:
    """Add two integers."""
    return {"result": a + b}

runtime = toolkit.runtime(provider="python-runtime")
agent = toolkit.agent(
    name="calculator",
    instructions="Use the available tools and return a structured answer.",
    tools=[add],
    runtime=runtime,
)

result = agent.run({"tool": "add", "input": {"a": 2, "b": 3}})
toolkit.human_result(result)
```

## Quick Start: Native AgenticSystem

Use `AgenticSystem` when you want a system boundary that registers tools, skills, agents, runtime and contracts.

```python
import agentic_systems as toolkit

runtime = toolkit.runtime(provider="python-runtime")
system = toolkit.AgenticSystem(runtime=runtime)

@system.tool
def multiply(a: int, b: int) -> dict:
    return {"result": a * b}

agent = system.agent(
    name="multiplier",
    instructions="Use registered tools to solve arithmetic requests.",
)

inspection = system.inspect()
inspection.raise_if_errors()

result = agent.run({"tool": "multiply", "input": {"a": 6, "b": 7}})
toolkit.human_result(result)
```

## Quick Start: Skills

A skill packages tools, instructions, contracts, assets and metadata.

```python
import agentic_systems as toolkit

@toolkit.tool
def add(a: int, b: int) -> dict:
    return {"result": a + b}

skill = toolkit.Skill(
    name="calculator_skill",
    description="Arithmetic tools and instructions.",
    tools=[add],
    prompts={"instructions": "Use arithmetic tools and return a structured answer."},
)

agent = toolkit.agent(
    name="skill_agent",
    instructions=skill.instructions,
    skills=[skill],
    runtime=toolkit.runtime(provider="python-runtime"),
)
```

## Quick Start: Contracts And Policies

Agents can be constrained with contracts and run policies. This matters when a workflow needs predictable tool usage, strict validation or bounded execution.

```python
import agentic_systems as toolkit

policy = toolkit.RunPolicy(
    max_turns=4,
    max_tool_calls=2,
    temperature=0.0,
    tool_choice="auto",
    repair=True,
    max_repairs=1,
    finalize="on_max_turns",
    trace="compact",
    strict=True,
)
```

`RunPolicy` keeps execution limits visible near the agent definition instead of hiding them inside notebook cells or provider-specific code.

## Results And Human Output

Every run returns a stable `RunResult` envelope:

```text
result.final       user-facing answer dictionary
result.data        reusable evidence payload
result.text        text fallback
result.tool_events executed tool events
result.usage       runtime usage metadata
result.validation  contract validation
result.errors      structured errors
```

Render output with:

```python
toolkit.human_result(result, pretty=False)
toolkit.human_results([result], pretty=False)
```

Normalize final answers with:

```python
toolkit.normalize_output({"a": 1})    # {"a": 1}
toolkit.normalize_output([{"a": 1}])  # {"rows": [{"a": 1}]}
toolkit.normalize_output([1, 2])      # {"items": [1, 2]}
toolkit.normalize_output("ok")        # {"value": "ok"}
```

Use output schemas when the expected response fields matter:

```python
schema = toolkit.output_schema(["procedure", "final_result"])
answer = toolkit.final_answer(
    {"procedure": ["2 + 3"], "final_result": 5},
    schema=schema,
)
```

## Lineage Memory

Lineage Memory explains what happened, how it happened and why the result is supported.

```python
memory = result.lineage(
    name="calculator.run",
    question="What is 2 + 3?",
    goal="Explain the answer from tool evidence.",
)

toolkit.show(memory)
memory.to_prompt_context(max_chars=1200)
```

Public lineage names:

```text
LineageMemory
LineageStep
lineage_memory
LINEAGE_SCHEMA_VERSION
```

## Graphs

Graph APIs coordinate state, nodes and edges. They do not replace tools, agents or systems; they orchestrate them.

Public graph and environment names include:

```text
AgenticEnvironment
EnvironmentTransition
AgentStepGraph
DynamicAgentRouterGraph
PlannedAgentGraph
build_agent_step_graph
build_dynamic_agent_router_graph
build_planned_agent_graph
build_single_agent_step_graph
environment_lineage
```

LangGraph integration helpers include:

```text
agent_node
graph
build_langgraph_agent_graph
build_langgraph_agent_node
build_langgraph_planned_graph
lineage_from_langgraph_result
lineage_from_langgraph_state
```

## Environments And Evals

Use environments when execution is episodic. Each record can become a step, the graph can update state, a reward function can score the transition and history can preserve evidence.

```python
import agentic_systems as toolkit

runtime = toolkit.runtime(provider="python-runtime")
system = toolkit.AgenticSystem(runtime=runtime)

@system.tool
def double(value: int) -> dict:
    return {"value": value * 2, "ok": True}

agent = system.agent(
    name="doubler",
    instructions="Call double when the input asks for a doubled value.",
    tools=["double"],
)

graph = toolkit.build_single_agent_step_graph(agent)
records = [
    {"input": {"tool": "double", "input": {"value": 21}}},
]

def reward_fn(state, row, action, env) -> float:
    return 1.0 if state.get("result", {}).get("ok") else 0.0

environment = system.environment(records, graph=graph, reward_fn=reward_fn)
observation, info = environment.reset(seed=0)
observation, reward, terminated, truncated, info = environment.step()

toolkit.show(toolkit.environment_summary(environment), title="Environment summary")
```

Use evals when you want repeatable validation over declared cases:

```python
cases = [
    {
        "name": "double_21",
        "input": {"tool": "double", "input": {"value": 21}},
        "expected": {"data_contains": {"value": 42, "ok": True}},
    }
]

report = system.eval(agent, cases)
toolkit.human_result(report)
report.raise_if_failed()
```

Public eval names:

```text
EvalCaseResult
EvalReport
Evaluator
run_eval
```

## Integrations

Use integrations when an external framework should own orchestration while Agentic Systems keeps the same tools, runtime, contracts, lineage and human output conventions.

```python
import agentic_systems as toolkit

runtime = toolkit.runtime(provider="auto")
agent = toolkit.agent(
    name="portable_agent",
    runtime=runtime,
    framework="openai-agents",
)
```

Integration-specific arguments stay owned by the selected framework. Agentic Systems does not reinterpret or hide framework-specific behavior.

## Notebook Utilities

Notebook utilities are public because tutorials use them, but they are not the first layer to teach:

```text
configure_notebook_environment
show_json
show
compare
compose_result
mask_sensitive
aws_environment_snapshot
boto3_session_snapshot
repair_ada_credential_chain
run_result_output
run_result_view
run_result_summary
tool_result_summary
chain_history_summary
environment_summary
eval_report_output
eval_report_summary
maybe_show_trace
agent_output
agent_output_mapper
make_agent_output_mapper
```

Use `compose_result(...)` when a notebook combines several real executions into one visible result while preserving engine names, framework metadata, usage and tool events.

## CLI

The package exposes diagnostics and inspection commands:

```bash
agentic-systems version
agentic-systems contact
agentic-systems doctor --json
agentic-systems runtime --provider auto --json
agentic-systems api --tier public --json
agentic-systems public-api --all --json
```

The CLI is for inspection, diagnostics and packaging smoke tests. It should not contain business logic.

## Tutorials

The official learning path is `tutorials/`:

```text
tutorials/00_runtime_api.ipynb
tutorials/00_runtime_bedrock_provider_api.ipynb
tutorials/00_runtime_openai_provider_api.ipynb
tutorials/00_runtime_vllm_provider_api.ipynb
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
tutorials/11_multi_agentic_system_api.ipynb
tutorials/12_multi_agentic_graph_api.ipynb
tutorials/13_single_agentic_system_api.ipynb
tutorials/14_multi_agentic_system_api.ipynb
```

There is no active `examples/` root. Tutorials both explain and exercise the API.

## Documentation

```text
docs/API.md
docs/CLI.md
docs/ARCHITECTURE.md
docs/BOUNDARIES.md
docs/ONBOARDING_FIRST_RUN.md
docs/RUNRESULT_FINAL_ANSWER.md
docs/PYTEST_COVERAGE_REPORT.md
docs/CONTRIBUTING_CHECKLIST.md
docs/ROADMAP_CHECKPOINTS.md
```

## Quality Gate

Current verified status:

```text
Version: 1.0.1
PyPI package: agentic-systems
Tests: 304 passed, 0 skipped
Coverage: 100.00%
TOTAL statements: 5299
TOTAL missing: 0
```

Covered layers include core execution, contracts, results, output contracts, tools, skills, factories, chain, expectations, providers, Bedrock Runtime client with fakes, LangGraph facade, environments, evals, Lineage Memory, human output, notebook utilities and CLI diagnostics.

Run validation locally:

```bash
python -m pytest -q
python -m compileall -q src tests tutorials
agentic-systems doctor --json
```

For full coverage validation:

```bash
python -m pytest --cov=agentic_systems --cov-report=term-missing -q
```

## Design Principles

```text
One public import.
Explicit runtime selection.
Provider and framework separation.
Typed tools and predictable payloads.
Stable result envelopes.
Contracts before hidden behavior.
Lineage before opaque answers.
Evaluation before claims.
Diagnostics without leaking secrets.
Tutorials as executable API documentation.
```

## Contact

Author: Jacobo Gerardo González León

E-Mail 1: jacobogerardo.gonzalez@bbva.com

E-Mail 2: jacoboggleon@gmail.com

LinkedIn: https://www.linkedin.com/in/jacoboggleon/

GitHub Repo: https://www.github.com/JacoboGGLeon/agentic_systems
