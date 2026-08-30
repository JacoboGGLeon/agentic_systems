# Agentic Systems

<p align="center">
  <img src="https://raw.githubusercontent.com/JacoboGGLeon/agentic_systems/main/docs/assets/logo_agentic_systems.png" alt="Agentic Systems logo" width="360" />
</p>

<p align="center">
  <a href="https://github.com/JacoboGGLeon/agentic_systems/releases/tag/v2.1.0"><img src="https://img.shields.io/badge/release-v2.1.0-blue.svg" alt="Agentic Systems 2.1.0 release" /></a>
  <a href="INSTALL.md"><img src="https://img.shields.io/badge/python-%3E%3D3.10-blue.svg" alt="Python >=3.10" /></a>
  <img src="https://img.shields.io/badge/core%20coverage-100%25-brightgreen.svg" alt="Core coverage 100%; Bedrock separately gated" />
  <img src="https://img.shields.io/badge/tests-passing-brightgreen.svg" alt="Tests passing" />
</p>

**Agentic Systems is a computational grammar for building intelligent systems
whose behavior can be inspected, evaluated and moved across runtimes without
losing its evidence.**

It gives deterministic code and language-model reasoning one explicit Python
model:

```text
Tool -> Skill -> Agent -> System
```

The same System can use deterministic Python, OpenAI, a local Ollama model, AWS
Bedrock Runtime or an OpenAI-compatible vLLM endpoint. Provider selection says
where inference runs; Framework selection says who owns the Agent loop. Neither
choice changes the application grammar.

Use Agentic Systems when a prototype must become a system you can explain,
test, operate and evaluate repeatedly. It does not promise identical model
wording, latency or vendor features. It promises one observable execution
contract for answers, Tool evidence, usage, validation, errors and lineage.

Agentic Systems 2.1 keeps explicit traceability between its API,
documentation, tutorials, and tests.

```text
API -> Docs -> Tutorials -> explicit automated or manual evidence
```

Release certification is documented separately from teaching material and the
Studio application. See [Semantic certification](docs/semantic-certification.md)
and the focused [semantic challenges](semantic_challenges/README.md). The
[narrative contract](docs/NARRATIVE_CONTRACT.md) defines how every public
surface must explain the same product without overstating its evidence.

Public concepts are defined in the API, explained in the documentation, taught through the canonical tutorials, and checked by explicit release gates.

Release status: `2.1.0` defines a canonical 5 Provider x 4 Framework registry,
strict versioned schemas, normalized reasoning-safe results and polymorphic
adapter contracts. Its public surface contains 89 stable top-level exports and
467 traced export/member IDs; all 2.0 serialization views remain compatible.

The certified release passed all 20 Provider x Framework routes and 108/108
reviewed semantic episodes across deterministic Python, OpenAI, Ollama, Bedrock
API key, Bedrock IAM in AWS/ADA and vLLM. These are artifact-specific results,
not a claim that every credential, endpoint or model is available in every
environment.

## Installation

Agentic Systems 2.1.0 is currently distributed through the signed GitHub
release assets. PyPI currently serves the earlier 2.0.0 line, so install the
downloaded 2.1 wheel when you need the contracts documented here:

```bash
python -m pip install ./agentic_systems-2.1.0-py3-none-any.whl
```

OpenAI Agents is optional and uses a different distribution/import name:

```bash
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[openai-agents]"
# Dependency distribution: openai-agents; Python import: agents
```

For the complete portable Provider/Framework tutorial stack (excluding the
platform-specific vLLM GPU server):

```bash
python -m pip install "./agentic_systems-2.1.0-py3-none-any.whl[all]"
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
- Can the same Agent run with deterministic Python, OpenAI, Ollama, Bedrock or vLLM?
- Can deterministic tools and language-model reasoning share one execution contract?

Agentic Systems represents those concerns as a computational grammar: runtime, tools, contracts, result envelopes, lineage, environments, eval reports and human output are first-class concepts in the same API.

## A Grammar You Can Execute

The grammar is not a diagram placed on top of another agent framework. Each
concept is a public Python object with its own contracts, execution boundary and
evidence.

| Property | What the library provides |
|---|---|
| Modular | Tools, Skills, Agents, Systems, Graphs, Environments and Evals can be built, inspected and tested independently. |
| Composable | An Agent may own an internal pipeline; a System owns the external plan; a Graph makes state and routing explicit. |
| Portable | Provider and Framework are independent choices, so application composition is not coupled to one model vendor or orchestration SDK. |
| Integrable | Native, LangGraph, OpenAI Agents and Strands retain their real execution loops and advanced capabilities behind an explicit adapter boundary. |
| Observable | Every executable boundary returns normalized results, Tool evidence, usage when supplied by the SDK, validation, errors and lineage. |
| Evaluable | The same Agent or System can be exercised directly or through Environment episodes and deterministic or judge-backed Evals. |
| Extensible | Typed Tools, runtime Skills, execution plans and Framework kwargs add capability without inventing a second application model. |

This creates a useful separation:

```text
Stable application grammar
        -> choose where inference runs (Provider)
        -> choose who owns the loop (Framework)
        -> keep one observable result contract
```

## Two Operating Patterns

The grammar supports two common operating patterns without splitting the
application into unrelated implementations.

```text
Fast path:
user -> online Agent -> live Tool/Agent collaboration -> answer

Deliberative path:
user -> client Agent -> offline System/Graph -> augmented evidence -> answer
```

The fast path favors an interactive response and may delegate through A2A. The
deliberative path favors bounded processing, durable evidence and later reuse,
and may expose capabilities through MCP. These are execution plans, not separate
APIs: Tools, Skills, Agents, Systems, `RunResult`, lineage and evals keep the
same meaning in both.

## What You Can Build

| Layer | What it gives you |
|---|---|
| Tools | Typed executable capabilities with structured results. |
| Skills | Packaged tools, instructions, contracts, assets and metadata. |
| Agents | Context transformed into actions through deterministic or LM-backed execution. |
| Systems | An application boundary for identities, runtime defaults, entrypoints, execution plans, inspection and hierarchical lineage. |
| Graphs | Portable-native or Framework-native state, nodes and edges for explicit routing and orchestration. |
| Environments | Episodic execution over records, transitions, rewards and history. |
| Evals | Repeatable validation cases with pass/fail reporting. |
| Lineage Memory | Human-readable explanation of what happened and why. |
| Integrations | Native, LangGraph, OpenAI Agents and Strands execution without rewriting the application grammar. |

## Core Model

The public model has two orthogonal dimensions:

```text
Computation: Tool -> Skill -> Agent -> System
Time:        Environment -> Episode -> Step
```

A Graph can express a System's topology. Eval can measure an Agent or System
directly, or observe it across Environment episodes. Runtime, Provider,
Framework, contracts, lineage and human output remain transverse contracts;
they support the grammar instead of becoming extra stages in it.

The grammar does not hide complexity. It gives each kind of complexity an
explicit owner, so the resulting system remains inspectable and portable.

## Runtime And Providers

Runtime and Scheduler solve two different parts of execution:

```text
Runtime   -> where and through which Provider execution happens
Scheduler -> the operational budget allowed for that execution

Runtime + Scheduler = resolved route + bounded execution
```

The Runtime carries Provider selection, model, region, endpoint and Provider
priority. Construction is declarative: it does not call a model. With
`provider="auto"`, resolution chooses one configured Provider and makes that
choice inspectable before or in the resulting execution evidence.

The Scheduler carries operational limits shared by runtime adapters:

| Limit | Meaning |
|---|---|
| `timeout_s` | Maximum wall-clock budget for a scheduled attempt. |
| `max_retries` | Number of retries permitted after a classified failure. |
| `backoff_s` | Delay between permitted retries. |
| `max_turns` | Upper bound for an Agent interaction loop. |
| `max_tool_calls` | Upper bound for Tool executions. |
| `max_concurrency` | Declared concurrency budget; synchronous local calls may still execute one at a time. |

The Scheduler does not select a Provider, change the Agent's meaning or make a
remote model deterministic. Agent behavior such as temperature, Tool choice,
repair and strictness belongs to `RunPolicy`; business success belongs to
Contracts and Evals.

Both objects are explicit and inspectable:

```python
scheduler = toolkit.scheduler(
    timeout_s=30,
    max_retries=0,
    max_turns=4,
    max_tool_calls=2,
)
runtime = toolkit.runtime(provider="auto", scheduler=scheduler)

toolkit.show(runtime.describe())
```

Canonical providers:

| Provider | Use |
|---|---|
| `python-runtime` | Local deterministic execution for tools, policies and smoke tests. |
| `openai-runtime` | Direct OpenAI model execution. |
| `ollama-runtime` | Local model execution through Ollama's OpenAI-compatible endpoint. |
| `bedrock-runtime` | AWS Bedrock Runtime through API-key or AWS credential-chain/IAM authentication. |
| `vllm-runtime` | An existing or explicitly managed OpenAI-compatible vLLM endpoint. |

`auto` is a selection mode, not a sixth Provider. It resolves one configured
Provider before execution and reports which route won and why. Readiness and
certification remain distinct:

```text
declared -> configured -> ready -> executed -> semantically certified
```

For a local Ollama route, install Ollama and the model outside Agentic Systems,
then configure the endpoint and model in the nearest `.env`:

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
OLLAMA_MODEL=qwen3:4b-instruct-2507-q4_K_M
RUN_OLLAMA_LIVE=1
```

The model value is illustrative and must name a model already available to the
configured Ollama server. Agentic Systems does not install Ollama, download the
model or start that process.

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
| `native` | Agentic Systems' portable Agent loop and contract boundary. |
| `langgraph` | LangGraph graph orchestration. |
| `openai-agents` | OpenAI Agents `Runner`, native Tools, handoffs, guardrails, sessions and MCP. |
| `strands` | `strands.Agent`, native Tools/MCP, hooks and lifecycle. |

Providers decide where inference runs. The selected Framework always owns its orchestration loop, and `RunResult.meta["framework_adapter"]` records the adapter that executed. Configuration details live in docs/ONBOARDING_FIRST_RUN.md and the layered tutorials/core, tutorials/providers and tutorials/frameworks paths.

## From Zero-to-Hero

The examples are cumulative. Each step introduces one grammatical primitive,
then reuses it in the layers that follow:

```text
Computation: Tool -> Skill -> Agent -> System
Composition: Agent pipeline | System execution plan | Graph topology
Time:        Environment -> Episode -> Step
Evidence:    Eval observes Agent, System or Episode behavior
```

### 1. Deterministic Tool

Start with the smallest executable unit: one typed Tool.

The Tool owns an operation and its JSON-friendly contract. It is the source of
truth for arithmetic, parsing, validation, policy enforcement and other work
that should be explicit and repeatable. A Tool does not interpret a user
request or own an execution loop; those responsibilities arrive with Agent.

```text
validated input -> typed Tool -> structured evidence
```

```python
import agentic_systems as toolkit

@toolkit.tool
def add(a: int, b: int) -> dict:
    """Add two integers."""
    return {"result": a + b}

add.check().raise_if_failed()
toolkit.show(add.info(), title="Tool contract")
```

The function remains ordinary Python, while the decorator adds a portable
contract that Agents, Skills and Systems can inspect and execute.

[API: Tools](docs/API.md#tools) ·
[Notebook: Core 01 - Tool](tutorials/core/01_tool.ipynb)

### 2. Runtime Skill

A Skill is the modularity boundary for a reusable capability. It packages
Tools together with instructions, contracts, assets and metadata, so the same
capability can travel across Agents, Systems, Providers and Frameworks without
copying configuration.

```text
Tool answers:  what can execute?
Skill answers: what belongs together and how should an Agent use it?
```

A Skill does not replace an Agent and does not reason by itself. It is a
governed runtime module that an Agent consumes. Use a raw Tool when one
function is enough; use a Skill when the capability needs shared instructions,
multiple Tools, schemas, assets, provenance or policy.

```python
calculator_skill = toolkit.skill(
    name="calculator",
    description="Verified arithmetic capabilities.",
    tools=[add],
    prompts={"instructions": "Use arithmetic tools as evidence."},
)

calculator_skill.check().raise_if_failed()
toolkit.show(calculator_skill.info(), title="Skill contract")

calculation = {"a": 20, "b": 22}
structured_request = {"tool": "add", "input": calculation}
natural_request = "Add 20 and 22 using the calculator Skill."
```

The rest of this walkthrough reuses `calculator_skill`; the capability is
defined once and composed many times.

[API: Skills](docs/API.md#skills) ·
[Notebook: Core 02 - Skills](tutorials/core/02_skills.ipynb)

### 3. Deterministic Agent

An Agent turns context into actions through an internal pipeline. Here,
`python-runtime` executes the already-defined Skill without a language model,
which makes this path fast, offline and repeatable.

```text
structured input -> Agent -> Skill -> typed Tool -> normalized RunResult
```

```python
calculator_agent = toolkit.agent(
    name="calculator",
    instructions=calculator_skill.instructions,
    skills=[calculator_skill],
    runtime=toolkit.runtime(provider="python-runtime"),
)

agent_pipeline = calculator_agent.pipeline(name="calculator_pipeline")
toolkit.show(agent_pipeline.inspect(), title="Deterministic Agent pipeline")

result = agent_pipeline.run(structured_request)
toolkit.human_result(result)
```

This first complete execution provides structured Tool events, validation,
errors and human output. It deliberately does not ask a model to interpret
natural language: correctness comes from executable code and explicit input.

[API: Agent and `Agent.pipeline`](docs/API.md#agents) ·
[Notebook: Core 03 - Agent](tutorials/core/03_agent.ipynb)

### 4. Provider-Backed Agent

Now keep the Tool and Agent declaration while changing where interpretation
and generation happen. A Provider-backed Agent can understand a natural
language request, decide how to use the Tool and verbalize its evidence.

```text
natural language -> Provider-backed Agent -> deterministic Tool -> final answer
```

This separation is fundamental: the model may reason about the request, but it
does not become the source of truth for arithmetic or business rules. The Tool
still produces the evidence. Moving from OpenAI to Ollama, Bedrock or vLLM
changes the inference boundary, not the application grammar.

```python
runtime = toolkit.runtime(provider="auto")
toolkit.show(runtime.describe(), title="Resolved Provider")

calculator_agent = toolkit.agent(
    name="calculator",
    instructions=calculator_skill.instructions,
    skills=[calculator_skill],
    runtime=runtime,
)

result = calculator_agent.run(natural_request)
toolkit.human_result(result, pretty=False, show_lineage=True)
```

`provider="auto"` resolves one configured Provider before execution and
records the selected route. Production and certification flows can select a
Provider explicitly when fallback or environmental ambiguity is unacceptable.
This is the first step in the walkthrough that invokes a language model when
`auto` resolves OpenAI, Ollama, Bedrock or vLLM; the preceding
`python-runtime` execution is deliberately deterministic.

[API: Runtime and Provider selection](docs/API.md#runtime-and-providers) ·
[OpenAI notebook](tutorials/providers/01_openai.ipynb) ·
[Ollama notebook](tutorials/providers/04_ollama.ipynb) ·
[Bedrock notebook](tutorials/providers/02_bedrock.ipynb) ·
[vLLM notebook](tutorials/providers/03_vllm.ipynb)

### 5. System

A Tool exposes one capability. A Skill makes capabilities reusable. An Agent
owns one computation pipeline. A **System** turns those parts into one
inspectable application boundary.

The earlier examples can execute an Agent directly. Creating a System adds the
properties an application needs as it grows:

- one place for Runtime and Framework defaults;
- scoped Tool, Skill and Agent registries with explicit conflict decisions and
  provenance;
- named entrypoints instead of executing every registered Agent;
- static inspection before any model or Tool is called;
- an internal pipeline for each Agent through `agent.pipeline(...)`;
- an external execution plan through `system.compile(execution=...)`, using a
  sequential, parallel or custom plan;
- hierarchical `RunResult` children and lineage across the composed execution.

```text
Direct Agent:
input -> Agent pipeline -> RunResult

Composed System:
input -> System entrypoint -> Agent(s) -> Tool/Skill evidence
                         -> hierarchical RunResult
```

```python
system = toolkit.system(runtime=runtime)
system.skill(calculator_skill)
calculator_agent = calculator_agent.bind(system)

inspection = system.inspect()
inspection.raise_if_errors()
toolkit.show(inspection.to_dict(), title="Static inspection")
print(inspection.human_text())

system_pipeline = system.compile(
    name="calculator_system_pipeline",
    entrypoint=calculator_agent,
)
toolkit.show(system_pipeline.inspect(), title="System execution plan")

result = system_pipeline.run(structured_request)
toolkit.human_result(result)
```

System and Graph are presented side by side because both are first-class
composition surfaces, but they answer different questions:

```text
System owns: identities + runtime + capabilities + execution boundary
Graph owns:  state + nodes + edges + routing topology
```

The two pipeline views are deliberately distinct:

```text
Agent pipeline  -> internal stages owned by one Agent
System pipeline -> external execution plan across selected entrypoints
```

A System may use a Graph as its orchestration structure. The System remains the
application boundary; the Graph remains the explicit route through that
application.

[API: System and static inspection](docs/API.md#system) ·
[Notebook: Core 05 - System](tutorials/core/05_system.ipynb)

### 6. Graph

Graphs coordinate state, nodes and edges. They do not replace Tools, Skills,
Agents or Systems; they make routing and transition topology explicit.

Use a Graph when the route is part of the application contract: conditional
branches, loops, fan-out/fan-in, shared state or dynamic Agent selection. For a
simple ordered sequence, an Agent pipeline or System execution plan is usually
the smaller abstraction.

```text
System: composition and ownership
Graph:  state transitions and routing
```

`toolkit.graph(engine="portable")` creates the dependency-free Agentic Systems
native Graph used below. `engine="auto"` may select native LangGraph when it is
installed, while the public boundary continues to expose the chosen graph kind
instead of hiding it. This is why Graph sits beside System in the API: System
owns composition; Graph owns orchestration topology.

`system.inspect()` and `graph.inspect()` are parallel, non-executing views, not
identical reports. System inspection validates registered identities,
capabilities and contracts; Graph inspection exposes the selected boundary,
native backend and available routing topology.

```python
def graph_input(state):
    if "input" in state:
        return state["input"]
    return state["row"]["input"]

agent_step = toolkit.agent_node(
    calculator_agent,
    input=graph_input,
    output=lambda result, _state: {"result": result},
    trace=None,
)
graph = toolkit.graph(
    nodes={"agent_step": agent_step},
    edges=[("START", "agent_step"), ("agent_step", "END")],
    engine="portable",
    name="calculator_graph",
)

toolkit.show(graph.inspect(), title="Native Graph inspection")

state = {
    "input": structured_request,
    "history": [],
}

next_state = graph.run(state)
toolkit.show(next_state, title="Graph state")
```

[API: native Graph and `GraphApp.inspect`](docs/API.md#graph-integrations) ·
[Notebook: Core 06 - Native Graph](tutorials/core/06_graph_native.ipynb)

### 7. Environment

Agent and System define computation. Graph makes routing topology explicit.
Environment adds time.

An Environment supplies records, resets, steps, rewards and history. It turns
the System's computation into Episodes that can be operated, observed,
persisted and replayed under explicit conditions.

```text
Time:       Environment -> Episode -> Step
Each Step:  System or Graph -> Agent -> Tool evidence
Capability: Skill supplies governed Tools and instructions to the Agent
```

Environment is not an Eval harness disguised as an abstraction. It is the
runtime boundary for any application whose state evolves: conversations,
queues, batch records, simulations, control loops and iterative workflows. An
application may use an Environment in production without running an Eval at
all; the same episode history can later become evaluation evidence.

The example continues with the same System, Agent, Skill and Graph. Nothing is
redeclared merely to add time to the application.

```python
records = [
    {"input": structured_request},
]

def reward_fn(state, row, action, env) -> float:
    return float(state["result"].ok)

environment = system.environment(
    records,
    graph=graph,
    reward_fn=reward_fn,
    name="calculator_environment",
)

observation, info = environment.reset(seed=0)
observation, reward, terminated, truncated, info = environment.step()

toolkit.show(toolkit.environment_summary(environment), title="Environment summary")
```

The reward reads the normalized `RunResult` produced by the Graph. It does not
branch on dictionaries, SDK response classes or Provider-specific payloads.
That is the role of the facade: the common path stays inside Agentic Systems,
while native Framework objects remain available when an advanced application
explicitly needs them.

The Environment owns episode progression, while the System still owns the
application identities, capabilities and execution boundary. This separation
lets either layer evolve without collapsing orchestration, state and evidence
into one object.

[API: Environment](docs/API.md#environment) ·
[Notebook: Core 07 - Environment and Eval](tutorials/core/07_environment_eval.ipynb)

### 8. Evals

Eval adds empirical verification. It asks whether an Agent or System satisfies
declared cases, whether execution happened directly or through recorded
episodes. Environment is useful without Eval, and Eval is useful without
Environment; combining them is a choice, not a requirement.

```text
Agent/System/episode evidence -> deterministic expectations -> optional judge
                              -> evaluation report
```

Deterministic expectations remain authoritative. A judge can assess semantic
quality, clarity or groundedness, but it cannot turn a deterministic failure
into a pass. Use Evals to compare behavior across versions, Providers,
Frameworks and release candidates without reducing success to `ok=True`.

```python
cases = [
    {
        "name": "add_20_22",
        "input": structured_request,
        "expected": {
            "must_call": ["add"],
            "expected_tool_outputs": {"add": {"result": 42}},
        },
    }
]

report = system.eval(calculator_agent, cases)
toolkit.human_result(report)
report.raise_if_failed()
```

The report is evidence, not merely an `ok=True` flag: each case retains input,
observed result, deterministic validation, score, optional judge evidence and
execution lineage.

[API: Evals](docs/API.md#evals) ·
[Notebook: Core 07 - Environment and Eval](tutorials/core/07_environment_eval.ipynb)

### 9. Results, Lineage And Human Output

`RunResult` is the portability boundary of the library. Every executable
boundary returns the same public envelope for answer, reusable data, Tool
evidence, usage, validation and errors, even when the underlying Provider or
Framework returns a different native object.

```text
Provider/Framework-specific execution
        -> normalized RunResult
        -> human output + machine evidence + lineage
```

The normalized view does not fabricate parity. Usage fields remain absent when
an SDK does not provide them, and native Framework results remain available for
advanced inspection. Application code can consume the stable fields below.

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

`human_result` is the readable projection of the evidence, not a replacement
for the structured result. It keeps the selected Provider, Framework, model,
usage, Tool calls, validation and final answer visible without exposing private
reasoning.

```python
toolkit.human_result(result, pretty=False, show_lineage=True)
toolkit.human_result([result_a, result_b], pretty=False)
```

Use output schemas when the expected response fields matter:

```python
schema = toolkit.output_schema(["procedure", "final_result"])
answer = toolkit.final_answer(
    {"procedure": ["20 + 22"], "final_result": 42},
    schema=schema,
)
```

Lineage Memory explains what happened, how it happened and why the result is
supported. For composed Systems it follows parent and child `RunResult`
relationships, so orchestration does not erase the Agent or Tool that actually
produced the evidence.

```python
memory = result.lineage(
    name="calculator.run",
    question="What is 20 + 22?",
    goal="Explain the answer from tool evidence.",
)

toolkit.show(memory)
memory.to_prompt_context(max_chars=1200)
```

[API: Results and Lineage Memory](docs/API.md#results-and-human-output) ·
[Notebook: Core 04 - Results and Lineage](tutorials/core/04_results_lineage.ipynb)

## Integrations

Use integrations when an external framework should own orchestration while Agentic Systems keeps the same tools, runtime, contracts, lineage and human output conventions.

Three independent choices are easy to conflate:

| Choice | Question it answers | Examples |
|---|---|---|
| **Provider** | Who performs model or deterministic execution? | `openai-runtime`, `bedrock-runtime`, `ollama-runtime`, `vllm-runtime`, `python-runtime` |
| **Framework** | Who owns the Agent loop and native lifecycle? | `native`, `langgraph`, `openai-agents`, `strands` |
| **Graph** | What application topology and state transitions should run? | nodes, edges, branches and routing declared with `toolkit.graph(...)` |

```text
Provider  -> who generates or executes
Framework -> who controls the Agent loop
Graph     -> what application topology runs
```

These axes compose; they are not aliases. `provider="langgraph"` is invalid
because LangGraph is a Framework, while `framework="openai-runtime"` is invalid
because OpenAI Runtime is a Provider. Choosing one does not silently choose the
other.

This is not a lowest-common-denominator wrapper. The adapter boundary preserves
the selected Framework's native object and accepts its explicit constructor and
run kwargs. OpenAI Agents keeps handoffs, guardrails, sessions and MCP; Strands
keeps Tools, MCP, hooks and A2A lifecycle; and the `native` Framework keeps the
dependency-free portable path.

When an Agent selects `framework="langgraph"`, Agentic Systems constructs a
minimal one-node `StateGraph` so LangGraph genuinely owns that Agent invocation.
It does **not** invent business routing. Declare a Graph explicitly with
`toolkit.graph(..., engine="langgraph")` when nodes, branches and state
transitions are part of the application contract.

```text
Agent loop owner: native | LangGraph | OpenAI Agents | Strands
System:          composes one or more Agents and their execution plan

Each route
        -> explicit Provider
        -> normalized RunResult
        -> inspectable lineage
```

```python
runtime = toolkit.runtime(provider="auto")

calculator_agent = toolkit.agent(
    name="calculator",
    instructions=calculator_skill.instructions,
    skills=[calculator_skill],
    runtime=runtime,
    framework="openai-agents",
)

result = calculator_agent.run(natural_request)
toolkit.human_result(result, show_lineage=True)
```

The same Agent can instead use LangGraph as its loop owner:

```python
langgraph_agent = toolkit.agent(
    name="calculator",
    instructions=calculator_skill.instructions,
    skills=[calculator_skill],
    runtime=toolkit.runtime(provider="auto"),
    framework="langgraph",
)

result = langgraph_agent.run(natural_request)
toolkit.human_result(result, show_lineage=True)
```

That call creates the adapter Graph automatically. An explicit application
Graph remains a separate design decision, demonstrated in
[Core 06 - Native Graph](tutorials/core/06_graph_native.ipynb) and the
[LangGraph notebook](tutorials/frameworks/00_langgraph.ipynb).

Integration-specific arguments stay owned by the selected framework. Agentic Systems keeps a thin facade; it does not reinterpret or hide framework-specific behavior.

[LangGraph notebook](tutorials/frameworks/00_langgraph.ipynb) ·
[OpenAI Agents notebook](tutorials/frameworks/01_openai_agents.ipynb) ·
[Strands notebook](tutorials/frameworks/02_aws_strands.ipynb) ·
[Provider x Framework matrix](tutorials/frameworks/03_provider_framework_matrix.ipynb)

## Studio reference application

[Agentic Systems Studio](examples/agentic_systems_studio/README.md) is the
installable conversational reference application. It lives under `examples/`
because it consumes the public grammar; Streamlit is not a dependency of the
core runtime. The notebook and UI build the same System and return the same
normalized `RunResult`.

Studio reads one canonical `.env`, discovers configured inference routes and
lets the user choose a Provider and Framework for the current session. Managed
credentials stay with the host. `python-runtime` is also available as an
explicit deterministic Hello World control and is never presented as an LM.

```text
python -m pip install -e .
python -m pip install -e examples/agentic_systems_studio[ui,notebook]
python -m streamlit run examples/agentic_systems_studio/app.py
```

OpenAI, Ollama and Bedrock need only their provider settings in `.env` or the
managed environment. vLLM uses the same Studio contract after its OpenAI-compatible
model server has been started.

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
real with python-runtime. The matrix notebook declares all 20 declared pairs
and executes only the routes explicitly authorized by their `RUN_*_LIVE`
gates; published semantic attestations remain the release evidence.
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
