# Agentic Systems

<p align="center"><img src="https://raw.githubusercontent.com/JacoboGGLeon/agentic_systems/main/docs/assets/logo_agentic_systems.png" alt="Agentic Systems" width="320"></p>

**Agentic Systems is a Python toolkit for building agentic applications that combine deterministic operations and language-model agents in explicit, inspectable workflows.** Compose capabilities with LangGraph, define contracts with Pydantic, and preserve results, errors, usage and lineage in a shared format—even when agents use different providers and frameworks.

Start with a Python function. Turn it into a Tool, give an Agent a capability,
and compose Agents into a System. Add Context, Memory, episodic execution and
evaluation as the application grows.

**Release 2.1.4** uses one public grammar. Install the SDK with
`pip install agentic-systems==2.1.4`; see [installation](INSTALL.md) for optional
framework/provider extras and Studio. Historical live evidence retains its original
artifact identity; this release uses the explicitly approved payload-equivalence
acceptance described in the release notes.

## Build from the bottom up

### 1. Runtime: choose how a capability executes

```python
import pydantic
import agentic_systems as toolkit

execution = toolkit.runtime(provider="python-runtime")
```

A model-backed runtime also specifies a model and execution controls:

```python
model_execution = toolkit.runtime(
    provider="openai-runtime",
    model="gpt-4.1-mini",
    timeout_s=60,
    max_retries=0,
    max_turns=3,
    max_tool_calls=1,
)
```

Keep credentials outside application code.

| Concept | Responsibility |
|---|---|
| **Provider** | Implements access to Python, OpenAI, Bedrock, Ollama or vLLM. |
| **Runtime** | Configures that access, its connection and execution controls. |
| **Scheduler** | Applies scheduling controls, timeouts and retries through runtime configuration. No separate public Scheduler constructor is needed. |

`run(..., timeout_s=60)` establishes a shared root deadline. A timeout does not
guarantee that a running thread stops or that external effects are rolled back.
[Execution controls and precedence](docs/RUNTIME_SCHEDULER_214.md).

### 2. Tool: implement a concrete operation

Keep arithmetic, validation and business rules in functions you can test.
This Tool calculates a one-percent fee using integer cents:

```python
@toolkit.tool
def calculate_fee(amount: int) -> dict:
    """Calculate a fee using integer cents."""
    return {"amount": amount, "fee": amount // 100}
```

```text
Input: amount=5000 → Process: calculate 1% → Output: amount=5000, fee=50
```

`@toolkit.tool` gives the function a discoverable contract and recorded execution.
Tools can also declare Pydantic input and output models.

### 3. Skill: group capabilities and instructions

```python
fees = toolkit.skill(
    name="fees",
    tools=(calculate_fee,),
    instructions="Calculate fees in integer cents.",
)
```

A Skill declares capabilities and how to use them. The graph defines execution order.

### 4. Agent: organize a capability

An actor-backed Agent executes through a runtime. Start with Python:

```python
fee_operator = toolkit.Agent(
    "fee_operator",
    runtime=execution,
    skills=(fees,),
)
result = fee_operator.run({
    "tool": "calculate_fee",
    "input": {"amount": 5000},
})
assert result.ok and result.data == {"amount": 5000, "fee": 50}
print(result.human_results())
```

An Agent can also organize steps through its own graph:

```python
class Payment(pydantic.BaseModel):
    amount: int = pydantic.Field(gt=0)
    fee: int | None = None

fee_graph = toolkit.Graph(Payment)
fee_graph.add_node("calculate_fee", calculate_fee)
fee_graph.add_edge(toolkit.START, "calculate_fee")
fee_graph.add_edge("calculate_fee", toolkit.END)

fee_agent = toolkit.Agent("fees", graph=fee_graph)
```

An Agent accepts **runtime or graph**, not both. A graph-backed Agent can contain
actor-backed Agents as nodes, so deterministic steps and model calls compose.

### 5. Framework: choose the actor implementation

```python
fee_reasoner = toolkit.Agent(
    "fee_reasoner",
    runtime=model_execution,
    framework=toolkit.framework("openai-agents"),
    skills=(fees,),
    instructions="Use calculate_fee for arithmetic; preserve its result.",
)
```

Defining this Agent does not call a model.

| Actor | Implementation |
|---|---|
| `native` | Agentic Systems' own execution loop. |
| `openai-agents` | OpenAI Agents SDK integration, including supported handoff configuration. |
| `strands` | AWS Strands integration. |

**LangGraph orchestrates. Frameworks implement actors. Providers supply execution.**
`native` is not another name for LangGraph. A System can combine actors from
different frameworks and providers.

### 6. System: coordinate the application

An Agent organizes a capability; a System coordinates application work:

```text
Payment → calculate fee → review evidence → approve or request review
```

Start with one Agent, then add nodes and decisions:

```python
memory = toolkit.Memory(capacity=2)

system_graph = toolkit.Graph(Payment)
system_graph.add_node("fees", fee_agent)
system_graph.add_edge(toolkit.START, "fees")
system_graph.add_edge("fees", toolkit.END)

system = toolkit.System("payments", graph=system_graph, memory=memory)
```

Use `add_conditional_edges` with ordinary Python functions for decisions;
use branches and barriers for parallel work. `toolkit.Graph` exposes LangGraph's
original StateGraph. START, END, Command and Send are original LangGraph objects too.
There is one graph builder and orchestration engine.

### 7. Context, Memory and lineage: give information a clear role

| Piece | Purpose |
|---|---|
| **Pydantic state** | Business data flowing through the graph. |
| **Context** | Domain information, sources and execution observations available to a capability. |
| **Memory** | Bounded episodes retained between executions within the process. |
| **Lineage** | Evidence of actual work and the relationships between executions. |

Tools and graph functions can request Context explicitly:

```python
@toolkit.tool
def calculate_policy_fee(amount: int, *, context: toolkit.Context) -> dict:
    return {"fee": amount * context.data["fee_bps"] // 10000}

policy_graph = toolkit.Graph(Payment)
policy_graph.add_node("fee", calculate_policy_fee)
policy_graph.add_edge(toolkit.START, "fee")
policy_graph.add_edge("fee", toolkit.END)

policy_agent = toolkit.Agent(
    "policy_fees",
    graph=policy_graph,
    context=toolkit.Context({"fee_bps": 100}, sources=("payment-policy-v1",)),
)
```

Lineage can inform another Agent without copying the full trace into state.
Memory lets later executions consult earlier episodes. Neither implies durable
storage or recovery after restarting the process.

### 8. Environment: run episodes and track evolution

```text
Record → observation → System → result → state update → next episode or stop
```

```python
episode_graph = toolkit.Graph(Payment)
episode_graph.add_node("payments", system)
episode_graph.add_edge(toolkit.START, "payments")
episode_graph.add_edge("payments", toolkit.END)

def update(state, record, result):
    return {"processed": state["processed"] + 1}

environment = toolkit.Environment(
    "payment_episodes",
    graph=episode_graph,
    records=({"amount": 5000}, {"amount": 15000}),
    state={"processed": 0},
    update=update,
    max_steps=2,
)
```

Environment supports records, observation, updates and stopping conditions.
Calculate rewards explicitly in update/state/history when needed. It does not
provide an implicit `reward=` API, training loop or complete reinforcement-learning API.

### 9. Eval: check behavior explicitly

```python
def check_fee(result, case):
    return {"ok": result.ok and result.data["fee"] == case["input"]["amount"] // 100}

evaluation = toolkit.Eval(
    "fee_acceptance",
    unit=system,
    cases=({"input": {"amount": 5000}, "expected": {"ok": True}},),
    checks=(check_fee,),
)
```

Eval targets an Agent, System or Environment. Each case receives an isolated view
of toolkit Memory, starting from its initial snapshot. This does not isolate
files, external services or sessions owned by other SDKs.

### 10. Compile, execute and inspect

```python
program = system.compile()  # Prepare and validate; no business execution or inference.
result = program.run({"amount": 5000})
assert result.ok
print(result.data)
print(result.human_results())

evidence = result.to_dict()
lineage = result.lineage()
```

| Operation | Meaning |
|---|---|
| `compile()` | Prepare execution and check structure. |
| `run()` | Execute synchronously. |
| `arun()` | Execute through the asynchronous API. |
| `human_results()` | Present input, observed steps, output and errors without inference. |
| `lineage()` | Inspect execution relationships and evidence. |

RunResult records data, errors, usage, Tool events and child executions.
`result.lineage().to_prompt_context()` provides a compact projection for agents;
`result.trace("full")` provides detailed inspection.

**`ok=True` means the declared checks passed. It is not a universal guarantee
that every model statement is true.**

## See the pieces working together

[Open the executed financial notebook](examples/financial_mixed/03_financial_system_native_local.executed.ipynb).
It combines OpenAI/native, Bedrock/Strands, Ollama local/native and Ollama
cloud/OpenAI Agents in one System, with Tools, Skills, Context, Memory,
Environment, reward calculation and Eval. Python and mixed-provider runs
produce the same business results. It transfers no funds.

The [validation report](revisions/2.1.4/ollama-connection-fix/01/live/REPORT.md)
contains RunResults, human_results, lineage, artifact hashes and recorded consumption.
The reference development wheel passed 544 offline tests and this focused online campaign.
Stable acceptance combines fresh offline CI with explicitly approved executable-payload
equivalence, without claiming new stable live inference. These results do not certify
every provider feature or a complete release matrix.

## Learn, scaffold and explore

- [Install the matching SDK and Studio](INSTALL.md).
- [Tutorials: core, providers, frameworks and API](tutorials/README.md).
- [Examples and their validation status](examples/README.md).
- [Full API walkthrough](examples/api_walkthrough/01_api_user_guide.ipynb).
- [Lineage and Memory that change decisions](examples/lineage_memory/01_lineage_memory_decisions.ipynb).
- [API contracts and signatures](docs/API_214_SURFACE.md).
- [Studio](examples/agentic_systems_studio/README.md) and the [Codex/ChatGPT skill](skills/agentic-systems/SKILL.md).

`agentic-systems new my_project` scaffolds an application using the same grammar.
Studio and the skill are separate deliverables from the SDK wheel.

## AWS sessions and optional ADA integration

`toolkit.runtime(provider="bedrock-runtime", model=..., session=supplied_session)`
borrows a session prepared by your platform and explicitly selects IAM.
Conflicting API-key, endpoint or region settings are rejected. The session stays
outside serialized state, Context, Memory and evidence, and the toolkit does not
close it. Toolkit invocations sharing it are serialized; external use remains
the owner's responsibility. The resource cannot be moved across processes.

[Session example](examples/aws_session/01_aws_session.ipynb) ·
[Independent ADA package](integrations/ada/README.md).
The optional diagnostic package is not included in `all`; its offline diagnostics
do not resolve credentials or certify real AWS/ADA access.

## Validation boundaries and known limitations

Bedrock/Qwen has reproducibly omitted an obligatory `amount` key when its value
was `null`, despite a strict schema. The received Tool arguments already lack
the key before local validation. Agentic Systems rejects them; it does not insert
defaults or invent values. This is a **known integration limitation**, not a PASS
for that scenario. [Reproduction and evidence](revisions/2.1.4/problem-fixes/01/REPORT.md).

vLLM GPU, AWS IAM and ADA IAM remain pending their environments. Configuration
support, offline tests and live validation are reported separately. SDK integrations
do not promise universal feature parity. Memory and pause/resume remain local to
the process; durable recovery is not implemented.

[Current status](docs/STATUS_214.md) · [Known issues](docs/OPEN_ISSUES_214.md).
