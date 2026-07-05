# Agentic Systems

<p align="center">
  <img src="https://raw.githubusercontent.com/JacoboGGLeon/agentic_systems/main/docs/assets/logo_agentic_systems.png" alt="Agentic Systems logo" width="360" />
</p>
<p align="center">
  <a href="https://pypi.org/project/agentic-systems/"><img src="https://img.shields.io/pypi/v/agentic-systems.svg" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/agentic-systems/"><img src="https://img.shields.io/pypi/pyversions/agentic-systems.svg" alt="Python versions" /></a>
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen.svg" alt="Coverage 100%" />
  <img src="https://img.shields.io/badge/tests-304%20passed%2C%200%20skipped-brightgreen.svg" alt="Tests 304 passed, 0 skipped" />
</p>
Agentic Systems is a Python library for building, running and evaluating
auditable agentic systems with tools, skills, agents, systems, graphs,
environments, evals, contracts, lineage memory and stable human output. It is
built for industrial agentic workloads: deterministic and language-model-based execution, explicit
runtime selection, observable provider diagnostics and repeatable evaluation
contracts for large volumes of agentic computation.

Install from PyPI:

```bash
pip install agentic-systems
```

Use the public facade as the stable entry point:

```python
import agentic_systems as toolkit
```

Agentic Systems exposes five practical routes:

```text
toolkit       top-level public facade for normal user code
primitives    Tool, Skill, Agent, RunResult, contracts, runtime and lineage
providers     execution backends: python-runtime, openai-runtime, bedrock-runtime, vllm-runtime or auto
system        AgenticSystem as the native composition layer
integrations  bridges to external agent frameworks such as LangGraph, Strands and OpenAI Agents
```

The recommended path is to start with `toolkit`, choose a provider with
`toolkit.runtime(provider=...)`, use primitives when you need fine control, move
to `AgenticSystem` when you need a complete auditable system, and use
integrations only when an external framework should own orchestration. Providers
can cross with either native systems or integrations: the framework owns the
loop, while the provider decides where inference or deterministic execution runs.

Agentic Systems supports two agent styles:

```text
deterministic agents  execute explicit tools and local Python policies with python-runtime
reasoning agents      use language-model providers such as openai-runtime, bedrock-runtime or vllm-runtime
```

Both styles share the same lifecycle: tools expose executable capabilities,
agents transform context into actions, systems/graphs coordinate agents,
environments run episodes, and evals validate behavior with empirical evidence.

## Quality Gate

Current verified test status is documented in [`docs/PYTEST_COVERAGE_REPORT.md`](docs/PYTEST_COVERAGE_REPORT.md):

```text
304 passed, 0 skipped
Coverage: 100.00%
TOTAL statements: 5290
TOTAL missing: 0
```

## What It Exposes

```text
Tool        executable capability
Skill       package of tools, instructions, contracts and assets
Agent       deterministic or reasoning unit that turns context into actions
System      workspace that registers and composes tools, skills and agents
Graph       state + nodes + edges orchestration
Environment episodic execution with reward and history
Eval        empirical validation and scoring over cases or episodes
```

Cross-cutting APIs:

```text
runtime/provider     python-runtime, openai-runtime, bedrock-runtime, vllm-runtime or auto
scheduler            execution budgets, retries, turns, timeouts and concurrency
contracts/policies   expected tools, strictness, repair and finalization rules
Lineage Memory       traceability, context, memory and audit trail
RunResult            stable execution envelope and final answer
human_result         readable output for users, notebooks and reviews
CLI diagnostics      doctor, runtime, API inventory and contact
```

## Providers And Integrations

Canonical providers:

```text
python-runtime     deterministic local execution for tools and policies
openai-runtime    native OpenAI language-model provider
bedrock-runtime   AWS Bedrock Runtime language-model provider
vllm-runtime      OpenAI-compatible vLLM provider for local or Colab GPU inference
auto              environment-based provider selection
```

Optional integrations:

```text
LangGraph       graph orchestration framework
Strands         external agent framework integration
OpenAI Agents   OpenAI Agents-style framework integration
```

`provider="auto"` is explicit selection mode. Use `runtime.describe()` or the
CLI to see what the current environment selects before executing a model. The
current priority is `vllm-runtime`, then `openai-runtime`, then
`bedrock-runtime`.

OpenAI runtime reads `OPENAI_API_KEY`, `AGENTIC_SYSTEMS_OPENAI_MODEL_ID`,
`OPENAI_MODEL_ID`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, `OPENAI_ORG_ID` and
`OPENAI_PROJECT` from the environment or `.env`. Diagnostics show safe flags,
not secret values.

vLLM runtime reads `VLLM_BASE_URL`, `VLLM_API_BASE`,
`AGENTIC_SYSTEMS_VLLM_BASE_URL`, `VLLM_MODEL_ID`, `VLLM_MODEL`,
`AGENTIC_SYSTEMS_VLLM_MODEL_ID`, `VLLM_API_KEY` and
`AGENTIC_SYSTEMS_VLLM_API_KEY`. It talks to a running vLLM OpenAI-compatible
server; the package does not start or install the GPU server by default.

Bedrock runtime reads `AGENTIC_SYSTEMS_MODEL_ID`, `OTC_MODEL_ID`,
`BEDROCK_MODEL_ID`, `AWS_REGION`, `AWS_DEFAULT_REGION`, `AWS_PROFILE`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN` from the
environment or `.env`. Diagnostics show region/profile/credential availability
flags, never secret values. Actual execution still uses the normal boto3/AWS
credential chain.

Integration-specific args stay owned by the selected framework. Agentic Systems
keeps a thin facade: pass provider/runtime config through `runtime(...)`, pass
framework identity through `framework="langgraph"`, `framework="strands"` or
`framework="openai-agents"`, and pass native framework options to the concrete
integration helper/factory that owns them. The library does not reinterpret or
hide framework-specific behavior.

## Quick Start

### Route 1: Toolkit And Primitives

Use this when you want direct control over tools, agents, provider/runtime and results.

```python
import agentic_systems as toolkit

@toolkit.tool
def add(a: int, b: int) -> dict:
    return {"result": a + b}

runtime = toolkit.runtime(provider="python-runtime")
agent = toolkit.agent(name="calc", tools=[add], runtime=runtime)

result = agent.run({"tool": "add", "input": {"a": 2, "b": 3}}, mode="eval")
toolkit.human_result(result)
```

### Route 2: Native System

Use this when you want a complete Agentic Systems workspace that registers and
composes tools, skills and agents under one auditable system boundary. The
system still receives a provider through `toolkit.runtime(...)`.

```python
import agentic_systems as toolkit

system = toolkit.AgenticSystem(model="python-runtime", runtime=toolkit.runtime(provider="python-runtime"))

@system.tool
def add(a: int, b: int) -> dict:
    return {"result": a + b}

agent = system.agent(name="calc", instructions="Use the registered calculator tools.")
result = agent.run({"tool": "add", "input": {"a": 2, "b": 3}}, mode="eval")

toolkit.human_result(result)
```

### Route 3: Environment And Evals

Use an environment when execution is episodic: each record becomes a step, the
system graph updates state, a reward function scores the transition, and history
keeps auditable evidence. Use evals when you want batch validation over declared
cases with pass/fail statistics.

```python
import agentic_systems as toolkit

runtime = toolkit.runtime(provider="python-runtime")
system = toolkit.AgenticSystem(model="python-runtime", runtime=runtime)

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

### Route 4: Integrations

Use integrations when LangGraph, Strands or OpenAI Agents should own the outer
framework loop while Agentic Systems keeps the same tools, provider/runtime,
contracts, lineage and human output conventions.

```python
runtime = toolkit.runtime(provider="auto")
agent = toolkit.agent(
    name="portable_agent",
    runtime=runtime,
    framework="openai-agents",
)
```

## CLI

```bash
agentic-systems version
agentic-systems contact
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

## Contact

Author: Jacobo Gerardo González León

E-Mail 1: jacobogerardo.gonzalez@bbva.com

E-Mail 2: jacoboggleon@gmail.com

LinkedIn: https://www.linkedin.com/in/jacoboggleon/

Github Repo: https://www.github.com/JacoboGGLeon/agentic_systems
