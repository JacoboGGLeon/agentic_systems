# Agentic Systems

<p align="center">
  <img src="https://raw.githubusercontent.com/JacoboGGLeon/agentic_systems/main/docs/assets/logo_agentic_systems.png" alt="Agentic Systems logo" width="360" />
</p>

<p align="center">
  <a href="https://pypi.org/project/agentic-systems/"><img src="https://img.shields.io/pypi/v/agentic-systems.svg" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/agentic-systems/"><img src="https://img.shields.io/badge/python-%3E%3D3.10-blue.svg" alt="Python >=3.10" /></a>
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen.svg" alt="Coverage 100%" />
  <img src="https://img.shields.io/badge/tests-393%20passed%2C%200%20skipped-brightgreen.svg" alt="Tests 393 passed, 0 skipped" />
</p>

**Agentic Systems proposes a computational grammar for building, executing, observing, and evaluating intelligent systems.**

Its Python API turns that grammar into explicit, composable abstractions: tools, skills, agents, systems, graphs, environments, evals, contracts, lineage memory and stable human-readable outputs. Runtime and Provider remain separate concepts, so the same computational model supports deterministic execution, OpenAI, AWS Bedrock Runtime and OpenAI-compatible vLLM endpoints through explicit runtime selection.

Use it when agentic workloads need to be observable, testable, portable and ready for repeated execution, not just notebook demos.

**Agentic Systems 1.1 establishes verifiable coherence between its API, documentation, tutorials, and tests.**

```text
API == Docs == Tutorials == Pytests
```

Here, `==` means verifiable traceability: public concepts are defined in the API, explained in the documentation, taught through the canonical tutorials, and enforced by tests and release gates.

Release status: `1.1.0` is the stable 1.1 release. Its automated and manual
evidence is recorded in `docs/RELEASE_1_1.md`.

```bash
pip install agentic-systems
```

```python
import agentic_systems as toolkit
```

### Live Provider Notebooks (Git Bash)

Export the provider configuration before starting Jupyter. Enable only the
provider you are about to test, and start Jupyter from the same terminal so its
kernel inherits the variables.

```bash
# OpenAI
export OPENAI_API_KEY='...'
export OPENAI_MODEL='gpt-4.1-mini'
export RUN_OPENAI_LIVE=1

# vLLM
export VLLM_BASE_URL='http://127.0.0.1:8000/v1'
export VLLM_MODEL='tu-modelo'
export RUN_VLLM_LIVE=1

# Bedrock
export AWS_PROFILE='tu-profile'
export AWS_REGION='us-east-1'
export BEDROCK_MODEL_ID='tu-model-id'
export RUN_BEDROCK_LIVE=1

python -m jupyter lab
```

Live execution is enabled by default. Each notebook detects whether its provider
is ready: configured providers execute on Run All, while unavailable providers
show an actionable preflight skip. Set the corresponding `RUN_*_LIVE=0` only
when you explicitly want to disable a live call. Never commit real credentials.

## Why Agentic Systems

Agent prototypes usually break when they leave the demo path because the important questions are not represented in code:

- Which provider actually ran this workload?
- Which tools were available and which ones were called?
- What evidence supports the answer?
- Can the same behavior be evaluated again?
- Can the same agent run locally, with OpenAI, with Bedrock or with vLLM?
- Can deterministic tools and language-model reasoning share one execution contract?

Agentic Systems represents those concerns as a computational grammar: runtime, tools, contracts, result envelopes, lineage, environments, eval reports and human output are first-class concepts in the same API.

## What You Can Build

| Layer | What it gives you |
|---|---|
| Tools | Typed executable capabilities with structured results. |
| Skills | Packaged tools, instructions, contracts, assets and metadata. |
| Agents | Context transformed into actions through deterministic or LM-backed execution. |
| Systems | A native workspace that registers runtime, tools, skills, agents and environments. |
| Graphs | Explicit state, nodes and edges for orchestrating agents and systems. |
| Environments | Episodic execution over records, transitions, rewards and history. |
| Evals | Repeatable validation cases with pass/fail reporting. |
| Lineage Memory | Human-readable explanation of what happened and why. |
| Integrations | A thin LangGraph adapter plus explicit profiles for declarative framework identities. |

## Core Model

```text
Tool -> Skill -> Agent -> System -> Graph -> Environment -> Eval

Runtime, Provider, Contracts, Lineage Memory and Human Output support the whole cycle.
```

The grammar does not hide complexity. It makes intelligent computation explicit, inspectable, portable and reusable across execution backends.

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

Default `provider="auto"` priority is `bedrock-runtime`, then `openai-runtime`, then `vllm-runtime`. Override it with `provider_priority=[...]` or `AGENTIC_SYSTEMS_PROVIDER_PRIORITY=...`. Bedrock is considered configured only when both a region and an AWS authentication signal are present; a region alone does not outrank a usable OpenAI or vLLM configuration.

Canonical framework facades:

| Framework | Use |
|---|---|
| `langgraph` | LangGraph graph orchestration. |
| `openai-agents` | Style-only identity over the selected runtime; no OpenAI Agents SDK adapter. |
| `strands` | Declarative compatibility identity; no Strands SDK adapter. |

Providers decide where execution runs. A real Framework adapter may own the outer orchestration loop; an accepted framework label alone does not prove adapter execution. Configuration details live in `docs/ONBOARDING_FIRST_RUN.md`, `docs/CLI.md` and the `tutorials/00_runtime_*` notebooks.

## From Zero-to-Hero

### 1. Deterministic Tool Agent

```python
import agentic_systems as toolkit

@toolkit.tool
def add(a: int, b: int) -> dict:
    """Add two integers."""
    return {"result": a + b}

agent = toolkit.agent(
    name="calculator",
    instructions="Use the available tools and return a structured answer.",
    tools=[add],
    runtime=toolkit.runtime(provider="python-runtime"),
)

result = agent.run({"tool": "add", "input": {"a": 2, "b": 3}})
toolkit.human_result(result)
```

### 2. Provider-Backed Agent

```python
runtime = toolkit.runtime(provider="auto")

agent = toolkit.agent(
    name="portable_calculator",
    instructions="Use tools when useful. Return a concise final answer.",
    tools=[add],
    runtime=runtime,
)

result = agent.run("Add 10 and 20 using the tool.")
toolkit.human_result(result, pretty=False, show_lineage=True)
```

### 3. Native AgenticSystem

Use `AgenticSystem` when you want a single system boundary that owns runtime, tools, skills, agents and diagnostics.

```python
system = toolkit.system(runtime=toolkit.runtime(provider="python-runtime"))

@system.tool
def multiply(a: int, b: int) -> dict:
    return {"result": a * b}

agent = system.agent(
    name="multiplier",
    instructions="Use registered tools to solve arithmetic requests.",
)

inspection = system.inspect()
inspection.raise_if_errors()
toolkit.show(inspection.to_dict(), title="Static inspection")
print(inspection.human_text())

result = agent.run({"tool": "multiply", "input": {"a": 6, "b": 7}})
toolkit.human_result(result)
```

### 4. Skills

A skill packages tools, instructions, contracts, assets and metadata.

```python
skill = toolkit.skill(
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

### 5. Graphs

Graphs coordinate state, nodes and edges. They do not replace tools, agents or systems; they orchestrate them.

```python
system = toolkit.system(runtime=toolkit.runtime(provider="python-runtime"))

@system.tool
def double(value: int) -> dict:
    return {"value": value * 2, "ok": True}

agent = system.agent(
    name="doubler",
    instructions="Call double when the input asks for a doubled value.",
    tools=["double"],
)

graph = toolkit.build_single_agent_step_graph(agent, input="input")

state = {
    "input": {"tool": "double", "input": {"value": 21}},
    "history": [],
}

next_state = graph.invoke(state)
toolkit.show(next_state, title="Graph state")
```

### 6. Environments And Evals

Use environments when execution is episodic. Use evals when behavior must be checked repeatedly.

```python
records = [
    {"input": {"tool": "double", "input": {"value": 21}}},
]

def reward_fn(state, row, action, env) -> float:
    return 1.0 if state.get("result", {}).get("ok") else 0.0

environment = system.environment(records, graph=graph, reward_fn=reward_fn)
environment.reset(seed=0)
environment.step()

toolkit.show(toolkit.environment_summary(environment), title="Environment summary")

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

### 7. Results, Lineage And Human Output

Every execution returns a stable `RunResult` envelope with answer, evidence, usage, validation, errors and tool events.

```python
result.final       # user-facing answer dictionary
result.data        # reusable evidence payload
result.text        # text fallback
result.tool_events # executed tool events
result.usage       # runtime usage metadata
result.validation  # contract validation
result.errors      # structured errors
```

Render one execution or a batch with `human_result`.

```python
toolkit.human_result(result, pretty=False, show_lineage=True)
toolkit.human_result([result_a, result_b], pretty=False)
```

Use output schemas when the expected response fields matter:

```python
schema = toolkit.output_schema(["procedure", "final_result"])
answer = toolkit.final_answer(
    {"procedure": ["2 + 3"], "final_result": 5},
    schema=schema,
)
```

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

## Integrations

Use integrations when an external framework should own orchestration while Agentic Systems keeps the same tools, runtime, contracts, lineage and human output conventions.

```python
runtime = toolkit.runtime(provider="auto")

agent = toolkit.agent(
    name="portable_agent",
    runtime=runtime,
    framework="openai-agents",
)
```

Integration-specific arguments stay owned by the selected framework. Agentic Systems keeps a thin facade; it does not reinterpret or hide framework-specific behavior.

## CLI

The package exposes diagnostics and inspection commands:

```bash
agentic-systems version
agentic-systems doctor --json
agentic-systems runtime --provider auto --json
agentic-systems api --tier public --json
agentic-systems public-api --all --json
```

The CLI is for inspection, diagnostics and packaging smoke tests. It should not contain business logic.

## Tutorials

The official learning path is `tutorials/`. It explains and exercises the public API directly from `import agentic_systems as toolkit`.

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
tutorials/11_single_agentic_system_api.ipynb
tutorials/12_multi_agentic_system_api.ipynb
tutorials/13_multi_agentic_graph_api.ipynb
```

There is no active `examples/` root. Tutorials are the executable documentation.

## Documentation

```text
docs/API.md
docs/CLI.md
docs/ARCHITECTURE.md
docs/BOUNDARIES.md
docs/ONBOARDING_FIRST_RUN.md
docs/RUNRESULT_FINAL_ANSWER.md
docs/STATIC_SYSTEM_INSPECTION.md
docs/MIGRATION_1_0_TO_1_1.md
docs/RELEASE_CANDIDATE_1_1.md
docs/PYTEST_COVERAGE_REPORT.md
docs/CONTRIBUTING_CHECKLIST.md
docs/ROADMAP_CHECKPOINTS.md
CHANGELOG.md
```

## Quality Gate

Current verified status:

```text
Version: 1.1.0
PyPI package: agentic-systems
Tests: 393 passed, 0 skipped
Coverage: 100.00%
TOTAL statements: 6193
TOTAL missing: 0
Canonical notebooks: 18/18 executed from fresh kernels
Manual notebook execution: passed, 0 failures
```

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

Author: Jacobo Gerardo Gonzalez Leon

E-Mail 1: jacobogerardo.gonzalez@bbva.com

E-Mail 2: jacoboggleon@gmail.com

LinkedIn: https://www.linkedin.com/in/jacoboggleon/

GitHub Repo: https://www.github.com/JacoboGGLeon/agentic_systems
