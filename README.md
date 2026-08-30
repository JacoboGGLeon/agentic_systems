# Agentic Systems

<p align="center">
  <img src="https://raw.githubusercontent.com/JacoboGGLeon/agentic_systems/main/docs/assets/logo_agentic_systems.png" alt="Agentic Systems logo" width="360" />
</p>

<p align="center">
  <a href="https://pypi.org/project/agentic-systems/"><img src="https://img.shields.io/pypi/v/agentic-systems.svg" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/agentic-systems/"><img src="https://img.shields.io/badge/python-%3E%3D3.10-blue.svg" alt="Python >=3.10" /></a>
  <img src="https://img.shields.io/badge/core%20coverage-100%25-brightgreen.svg" alt="Core coverage 100%; Bedrock separately gated" />
  <img src="https://img.shields.io/badge/tests-passing-brightgreen.svg" alt="Tests passing" />
</p>

**Agentic Systems gives Python applications one explicit, testable model for
building and evaluating agentic workflows across deterministic and model-backed
runtimes.**

It does so through a computational grammar for building, executing, observing,
and evaluating intelligent systems.

Its Python API turns that grammar into explicit, composable abstractions: tools, skills, agents, systems, graphs, environments, evals, contracts, lineage memory and stable human-readable outputs. Runtime and Provider remain separate concepts, so the same computational model supports deterministic execution, OpenAI, AWS Bedrock Runtime and OpenAI-compatible vLLM endpoints through explicit runtime selection.

Use it when agentic workloads need to be observable, testable, portable and ready for repeated execution, not just notebook demos.

Agentic Systems 2.1 keeps explicit traceability between its API,
documentation, tutorials, and tests.

```text
API -> Docs -> Tutorials -> explicit automated or manual evidence
```

Release certification is documented separately from teaching material and the
Studio application. See [Semantic certification](docs/semantic-certification.md)
and the focused [semantic challenges](semantic_challenges/README.md).

Public concepts are defined in the API, explained in the documentation, taught through the canonical tutorials, and checked by explicit release gates.

Release status: `2.1.0` hardens the Provider x Framework architecture with a canonical 20-pair registry, strict versioned schemas, normalized reasoning-safe results, polymorphic adapter contracts and blocking production/Pydantic/POO gates. The 2.1 surface contains 89 stable top-level exports and 467 traced export/member IDs; all 2.0 serialization views remain compatible.

## Installation

```bash
pip install agentic-systems
```

OpenAI Agents is optional and uses a different distribution/import name:

```bash
pip install "agentic-systems[openai-agents]==2.1.0"
# PyPI distribution: openai-agents; Python import: agents
```

For the complete portable Provider/Framework tutorial stack (excluding the
platform-specific vLLM GPU server):

```bash
pip install "agentic-systems[all]==2.1.0"
```

```python
import agentic_systems as toolkit
```

### Install the Agentic Systems skill

The `v2.1.0` GitHub release includes a credential-free skill ZIP whose archive
root is `agentic-systems/`.

```powershell
Expand-Archive .\agentic-systems-skill-2.1.0.zip `
  -DestinationPath "$env:USERPROFILE\.codex\skills" -Force
```

```bash
unzip agentic-systems-skill-2.1.0.zip -d ~/.codex/skills
```

Restart or reload Codex, then invoke `$agentic-systems`. OpenAI Skills upload
surfaces that accept a ZIP can consume the same artifact. Download the
standalone skill, conversational Studio and ADA offline bundle from the
[v2.1.0 release](https://github.com/JacoboGGLeon/agentic_systems/releases/tag/v2.1.0).

Release assets:

- `agentic_systems-2.1.0-py3-none-any.whl`: certified universal Python wheel.
- `agentic_systems-2.1.0.tar.gz`: matching source distribution.
- `agentic-systems-skill-2.1.0.zip`: Codex/OpenAI skill package.
- `agentic-systems-studio-2.1.0.zip`: one portable conversational Agentic System.
- `agentic-systems-2.1.0-ada-offline.zip`: wheel, Studio, tutorials and live evidence for restricted environments.
- `agentic-systems-2.1.0-strands-protocol-challenge.zip`: frozen MCP+A2A/LangGraph semantic gate for local, Colab, SageMaker and ADA execution.
- `final-certification-summary.json`: exact wheel identity and reviewed live evidence inventory.
- `SHA256SUMS-2.1.0.txt`: hashes for the Python and product artifacts.

For an installed-package smoke test and provider notebook setup, follow
[First Run Onboarding](docs/ONBOARDING_FIRST_RUN.md).

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
| Integrations | Native, LangGraph, OpenAI Agents, and Strands execution over explicit Providers. |

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
| `vllm-runtime` | Client path for an existing or explicitly managed OpenAI-compatible vLLM endpoint. |
| `python-runtime` | Local deterministic execution for tools, policies and smoke tests. |
| `auto` | Selects a concrete provider from environment signals before execution. |

For local/Colab GPU serving, 2.1 adds an explicit lifecycle boundary:

```python
artifact = toolkit.model_artifact("unsloth/Qwen3-4B-Instruct-2507")
server = toolkit.model_server(artifact, profile="medium")
endpoint = server.start()       # explicit; construction never starts a process
runtime = server.runtime()      # vllm-runtime bound to the real endpoint/model
server.stop()                   # stops only the process owned by this object
```

The canonical walkthrough and four-Framework attestation are in
`tutorials/providers/03_vllm.ipynb`.

Default `provider="auto"` priority is `bedrock-runtime`, then `openai-runtime`, `vllm-runtime`, and `ollama-runtime`. Override it with `provider_priority=[...]` or `AGENTIC_SYSTEMS_PROVIDER_PRIORITY=...`. Bedrock is considered configured only when both a region and an AWS authentication signal are present. That signal may be the standard AWS credential chain (signed with SigV4) or the native `AWS_BEARER_TOKEN_BEDROCK` API key; both use the same boto3 `bedrock-runtime` Provider and a region alone does not outrank another usable Provider.

Canonical framework facades:

| Framework | Use |
|---|---|
| `langgraph` | LangGraph graph orchestration. |
| `openai-agents` | OpenAI Agents `Runner`, native Tools, handoffs, guardrails, sessions and MCP. |
| `strands` | `strands.Agent`, native Tools/MCP, hooks and lifecycle. |

Providers decide where inference runs. The selected Framework always owns its orchestration loop, and `RunResult.meta["framework_adapter"]` records the adapter that executed. Configuration details live in docs/ONBOARDING_FIRST_RUN.md and the layered tutorials/core, tutorials/providers and tutorials/frameworks paths.

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

agent_step = toolkit.agent_node(
    agent,
    input="input",
    output=lambda result, _state: {"result": result},
    trace=None,
)
graph = toolkit.graph(
    nodes={"agent_step": agent_step},
    edges=[("START", "agent_step"), ("agent_step", "END")],
    engine="portable",
)

state = {
    "input": {"tool": "double", "input": {"value": 21}},
    "history": [],
}

next_state = graph.run(state)
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

## Tutorials

The canonical learning path is layered by responsibility:

| Layer | Purpose | Default execution |
|---|---|---|
| tutorials/core | Agentic Systems grammar and composition | Python Runtime, Native Framework, portable Graph |
| tutorials/providers | Inference boundary | Explicit preflight; external execution when configured |
| tutorials/frameworks | Native orchestration SDK | Real SDK offline; Provider auto is optional |
| tutorials/api | Exact public contract | Generated manifest, documentation and pytest traceability |

Provider notebooks use one public route and choose Run All:

| Provider | Readiness inputs | Notebook |
|---|---|---|
| OpenAI | OPENAI_API_KEY; OPENAI_MODEL optional | tutorials/providers/01_openai.ipynb |
| vLLM | VLLM_BASE_URL and VLLM_MODEL | tutorials/providers/03_vllm.ipynb |
| Bedrock | Region plus SigV4 credentials or AWS_BEARER_TOKEN_BEDROCK | tutorials/providers/02_bedrock.ipynb |
| Ollama | OLLAMA_MODEL; OLLAMA_BASE_URL optional | tutorials/providers/04_ollama.ipynb |

The Framework notebooks execute LangGraph, OpenAI Agents and Strands SDKs for
real with python-runtime; the matrix notebook covers all 20 declared pairs.
Optional RUN_*_LIVE=1 changes only the Provider.
RUN_*_LIVE=0 forces a fully offline validation.

The full ordered inventory contains 21 canonical Python notebooks and lives in
tutorials/README.md. Studio is the single application example; there is no
duplicated tutorial route.

## Documentation

Use the [documentation map](docs/README.md) to choose the user guide,
conceptual model, API reference or current engineering contracts. Version
history is recorded in the [changelog](CHANGELOG.md); published artifact
evidence belongs to GitHub Releases.

## Quality Gate

Current verified status:

```text
Version: 2.1.0
PyPI package: agentic-systems
Tests: run `python -m pytest` for the current count
Core coverage: 100.00%
Coverage scope: Bedrock facade and internal package excluded from core; separately gated at 100%
Canonical notebooks: 17 deterministic executed; 4 Provider notebooks execute their explicit not-run path offline

```

Run validation locally:

```bash
python -m pytest -q -W error::RuntimeWarning
python -m ruff check src tests
python -m pyright --project pyrightconfig.json
python scripts/check_pyright_baseline.py
lint-imports
python scripts/check_architecture.py
python scripts/check_secrets.py
python -m compileall -q src tests tutorials
agentic-systems doctor --json
```

The complete production, Pydantic and POO/polymorphism certification is
documented in [Triple Quality Gate](docs/QUALITY_GATES.md).

For full coverage validation:

```bash
python -m pytest --cov=agentic_systems --cov-report=term-missing -q
python -m pytest tests/providers -q --cov-config=.coveragerc-bedrock --cov=agentic_systems.providers.bedrock_runtime --cov=agentic_systems.providers.bedrock --cov-report=term-missing
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
