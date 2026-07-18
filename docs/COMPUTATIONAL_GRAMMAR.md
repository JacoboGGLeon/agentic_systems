# Computational Grammar

Status: normative for Agentic Systems 1.1 terminology.

This document defines the computational grammar of Agentic Systems. It names
the concepts users compose and the boundaries implementations must preserve.
It does not introduce a public algebra, DSL, parser, or new runtime object.

Detailed behavioral meaning is defined in [`SEMANTICS.md`](SEMANTICS.md). The
mapping to the 1.0.7 implementation is documented in
[`GRAMMAR_TO_API.md`](GRAMMAR_TO_API.md).

## Normative Language

The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY express requirements in
this document. Requirements apply to public behavior unless a paragraph is
explicitly labeled as an implementation detail.

## Thesis

Agentic Systems is a computational grammar for building, executing, observing,
and verifying intelligent systems.

The grammar organizes the library into nine roles:

```text
Capabilities       executable operations
Knowledge          reusable operational guidance and assets
Actors             entities that choose or perform actions
Execution Contexts runtime conditions under which computation occurs
State              information carried across transitions
Composition        ownership and coordination of parts
Interaction        episodic exchange with an environment
Observation        structured evidence and human projections
Verification       repeatable checks over behavior and evidence
```

The existing learning path remains:

```text
function -> Tool -> Skill -> Agent -> AgenticSystem
                                      |
                                      v
                                    Graph -> Environment -> Eval
```

This path is pedagogical, not a requirement that every system contain every
layer. A Tool can run without a Skill. An Agent can run without a Graph. An Eval
can verify an Agent without requiring a user-created Environment.

## Grammar Layers

### Capability: Tool

A Tool is the smallest named executable capability in the public grammar.

A Tool MUST have stable identity within its composition boundary, a callable
implementation before execution, an inspectable purpose and input contract, and
an output/failure representation compatible with `RunResult` evidence. A Tool
MAY declare explicit Pydantic input and output schemas. A strict Tool MUST reject
output that violates its declared contract. Provider adaptation MUST preserve
its name, schema, and observable result meaning.

A Tool is not an Agent. It does not choose goals, select among capabilities, or
own a conversation loop.

Example:

```python
@toolkit.tool
def add(a: int, b: int) -> dict:
    """Add two integers."""
    return {"result": a + b}
```

Counterexample: wrapping a multi-turn planner as a Tool and treating its hidden
decisions as one atomic, deterministic operation.

### Knowledge: Skill

A Skill is a reusable package of capabilities and operational knowledge. It MAY
contain Tools, prompts, instructions, contracts, policies, metadata, versions,
and external assets.

A Skill MUST remain independent from any one provider. Loading a Skill MAY
materialize filesystem assets, but MUST NOT silently execute a model or start an
agent loop. `Skill` and `LoadedSkill` are two public materialization forms of the
same conceptual role. Their construction and asset lifecycle differ; they MUST
NOT be described as different levels of agency.

A Skill is not a second Agent and does not independently choose actions.

Example: a calculator Skill containing arithmetic Tools and instructions about
when each Tool is appropriate.

Counterexample: a Skill whose constructor calls a provider, mutates remote
state, and returns a final answer.

### Actor: Agent

An Agent is an actor definition that combines identity, instructions,
capabilities, knowledge, contracts, policy, and execution configuration.

An Agent MUST expose the capabilities it may use and MUST produce observable
execution results. It MAY be portable before it is bound to an executable
system. Binding supplies execution ownership; it does not create a new
conceptual actor.

An Agent is not a Provider. Changing the Provider MUST NOT redefine the Agent's
name, instructions, declared capabilities, or contracts.

Example:

```python
agent = toolkit.agent(
    name="calculator",
    instructions="Use arithmetic tools and return evidence.",
    tools=[add],
    runtime=toolkit.runtime(provider="python-runtime"),
)
```

Counterexample: calling an HTTP model client an Agent merely because it returns
generated text.

### Composition Boundary: AgenticSystem

An AgenticSystem is the public composition and governance boundary for shared
Tools, Skills, Agents, runtime defaults, and inspection.

It MUST make registered parts and configuration inspectable. It MUST reject
references to capabilities unavailable in its boundary. It MAY provide factories
for Graphs, Environments, and Evals, but those conveniences do not make those
abstractions internal details of the System.

An AgenticSystem is not synonymous with one Agent. It can contain zero, one, or
many Agents and shared capabilities.

Example: one System registers shared customer Tools and creates separate
research and approval Agents.

Counterexample: a global mutable registry with no inspectable ownership, used by
unrelated Agents through implicit process state.

### State Composition: Graph

A Graph is an explicit state-transition composition. It defines nodes, edges,
entry behavior, terminal behavior, and state exchanged between transitions.

A Graph MUST make transition structure explicit through its public or native
framework representation. A node MAY invoke an Agent or Tool. A framework
adapter MAY compile the Graph to a native object, but MUST NOT hide access to
native behavior required for advanced use.

A Graph is not a Provider and does not by itself imply model execution.

Example: a route node selects a specialist Agent, then a validation node checks
the resulting state.

Counterexample: a function containing undocumented conditionals described as a
Graph while exposing no state or transition structure.

### Interaction: Environment

An Environment is an episodic interaction context. It owns observations,
actions, transitions, rewards, termination, truncation, and episode history.

An Environment MUST make episode boundaries explicit and retain enough
transition evidence for inspection. It MAY use a Graph to implement a
transition. The current `AgenticEnvironment` uses a Gymnasium-shaped step
contract; that return shape remains part of compatibility.

An Environment is not a static dataset. Records can seed episodes, but
interaction and state transition make the object an Environment.

Example: each record becomes an observation, an Agent action updates state, and
a reward function scores the transition.

Counterexample: iterating over a dataframe and calling the loop an Environment
without observations, transitions, termination, or history.

### Verification: Eval

An Eval is a repeatable verification procedure over cases, execution results,
transitions, or evidence.

An Eval MUST declare what is checked and produce an inspectable report. It MUST
distinguish execution failure from assertion failure when evidence permits that
distinction. It SHOULD be deterministic when its subject and evaluator are
deterministic.

An Eval is not a demonstration and not a screenshot of a successful run.

Example: execute fixed inputs, validate required Tool evidence, and aggregate
case-level pass/fail results in `EvalReport`.

Counterexample: manually reading one notebook output and declaring the Agent
verified.

## Transverse Contracts

### RunResult

`RunResult` is the stable execution envelope for Tool and Agent execution. It
separates the user-facing answer from reusable evidence and operational facts.
Producers MUST use its fields consistently. Consumers MUST prefer structured
fields over parsing rendered text. Graph, Environment, and Eval boundaries MAY
project or contain RunResults rather than returning one directly.

### Contracts and Policies

A Contract declares required behavior or evidence. A Policy constrains how an
execution may proceed. Contracts answer "what must be true"; policies answer
"what execution is allowed to do." Validation MUST be observable. A failed
contract MUST NOT be silently converted to a successful result.

### Runtime

A Runtime is a declarative execution selection and its resolved operational
configuration. It connects an actor definition to a Provider while carrying
safe, inspectable configuration. `provider="auto"` MAY choose a Provider from
environment signals, but resolution MUST become explicit before or in the
execution record.

### Provider

A Provider decides where and through which backend Tool or model execution
happens. Providers include `python-runtime`, `bedrock-runtime`, `openai-runtime`,
and `vllm-runtime`.

A Provider MUST adapt to core contracts. It MUST NOT redefine Tool, Agent, or
RunResult semantics. Provider-specific metadata MAY be added without making
portable consumers depend on it.

### Framework

A Framework is an external composition or orchestration system adapted by an
integration. LangGraph, OpenAI Agents-style integration, and Strands are
framework identities; they are not Providers.

A Framework adapter MUST preserve core contracts and SHOULD expose its native
object for framework-specific capabilities.

### Scheduler

A Scheduler applies operational limits such as timeouts, retries, Tool-call
budgets, turn budgets, concurrency, and backoff. Scheduler behavior MUST remain
observable in execution metadata or failures. A retry MUST NOT erase evidence of
a failed attempt when it affects the final result or contract.

### Lineage Memory

Lineage Memory is a compact, provider-neutral explanation of what happened, how
it happened, and why the result is supported. It is derived from evidence and is
not a replacement for raw evidence.

### Human Output

Human Output is a projection of structured execution evidence for people. It
MUST NOT become the source of truth or contradict the underlying result.

### Diagnostics

Diagnostics inspect package, runtime, registry, and configuration health without
performing domain work. They MUST avoid exposing secrets and SHOULD avoid model
execution unless a command explicitly promises a smoke run.

### Chain

A Chain is sequential non-agentic composition. It applies ordered steps without
autonomous capability selection. It is intentionally weaker than Agent and Graph
and remains useful for deterministic or direct model pipelines.

## Execution Context

Execution Context is a conceptual role, not a public class in 1.1. It is the
resolved set of conditions relevant to one execution, including input, mode,
actor/system binding, runtime and Provider, optional Framework, contracts,
policy, scheduler limits, state, and correlation metadata.

Implementations MAY represent these conditions across existing objects. They
MUST NOT require users to construct a new `ExecutionContext` object in 1.1.

## Legal Composition

The grammar permits these compositions:

- a Tool executes directly;
- a Skill packages Tools and operational knowledge;
- an Agent uses Tools and Skills;
- an Agent binds to one AgenticSystem for an execution;
- an AgenticSystem owns shared Tools, Skills, and Agents;
- a Graph node invokes a Tool, Agent, Chain, or deterministic function;
- an Environment uses a Graph or invokable transition;
- an Eval verifies Agent or Environment behavior;
- RunResult, lineage, and human output observe supported boundaries.

The grammar rejects these interpretations:

- Provider is a subtype of Agent;
- Framework defines the meaning of Tool or RunResult;
- Skill is an autonomous actor;
- rendered output is execution evidence;
- implicit fallback equals successful Provider substitution;
- registration in one System makes a Tool globally available;
- every composition must return the same Python type.

## Provider-Independent Model

The conceptual model ends before provider SDK calls and framework-native
compilation begin. Core definitions MUST be expressible without importing
optional provider or framework packages.

```text
Conceptual model        Adapter boundary       External mechanism
Tool/Agent/Contract  -> Provider adapter    -> model or local execution
Graph/State          -> Framework adapter   -> native graph runtime
RunResult/Evidence   <- normalization       <- provider/framework payload
```

Provider and Framework implementations MAY differ operationally. Their adapters
MUST preserve the concepts and observable contracts defined here.

## Extension Rule

A proposed public abstraction SHOULD be added only when:

1. It has semantics not already owned by an existing abstraction.
2. Its identity and lifecycle can be stated precisely.
3. It composes without hidden global state.
4. Its Provider/Framework independence is clear.
5. Its result, evidence, and failure behavior are testable.
6. Its backward compatibility cost is justified.

Otherwise, it SHOULD be an internal adapter, helper, or extension of an existing
abstraction.
