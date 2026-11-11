---
name: agentic-systems
description: Design, implement or audit applications using the Agentic Systems 2.1.7 API, LangGraph orchestration, deterministic Tools and portable agent actors.
metadata:
  short-description: Build and validate Agentic Systems 2.1.7 apps
---

# Agentic Systems 2.1.7

Use `import agentic_systems as toolkit`. Target version 2.1.7 and verify installed signatures before writing executable examples.

The SDK bundles this authoring skill. Use `agentic-systems skill install`
to copy it into `.agents/skills/agentic-systems`, or `agentic-systems skill export skill.zip`
for a manual import. These commands do not register a personal ChatGPT skill or install
runtime dependencies. Inspect `agentic-systems skill info` for the installed bundle identity.

## Choose the smallest useful design

1. State the user's input, expected business output and one rejection case.
2. Use a function/Tool for one deterministic operation. Add a Skill for a reusable
   capability group. Use Agent(runtime=...) for actor execution or Agent(graph=...)
   for explicit composition. Add System only for application coordination.
3. Add Environment for records with observation/update/stop; add Eval for acceptance
   cases. They are independent choices, not mandatory layers of every application.
4. Start beginners with [the first Tool](assets/first_tool.py), then explain each
   new declaration through input, operation and output. Use assets/minimal.py only
   for the complete composition lesson; it is not the first five-minute example.
5. For model-selected actions, read [actor recipes](references/actor-recipes.md).
   Preserve the user's provider and actor choice and verify real Tool evidence.
6. Deliver commands from an explicit working directory, prerequisites, expected
   output, a positive and negative check, and the exact verification scope.
   Write repository documentation and notebook narrative in English; explain work
   conversationally in the user's language.

## Construction

Use `import pydantic` and `import agentic_systems as toolkit`. Use an uncompiled `toolkit.Graph(State)` with State declared as `pydantic.BaseModel` for every composed
Agent, System and Environment. Add Tools/functions/Agents/Systems as nodes;
Declare every Tool output channel in the graph state; undeclared channels are
projected away. For parallel Agents, use a per-agent Graph output_schema that
returns only its owned channels, or explicit reducers for shared channels. Then
use edges for sequence, branches plus barriers for parallel work, and
add_conditional_edges with ordinary Python decisions. Do not generate
Sequence, Parallel, flow=, backend= or framework("langgraph").

Agent accepts graph OR runtime, not both. System accepts graph. Environment
accepts graph and records. A graph may contain an Agent(runtime=...).
LangGraph orchestrates; native, openai-agents and strands implement actors;
python-runtime, openai-runtime, bedrock-runtime, ollama-runtime and vllm-runtime
select execution. Preserve these independent responsibilities.

Runtime and scheduler are execution pillars, not orchestration alternatives.
Configure timeout_s, max_retries, backoff_s, max_concurrency, max_turns and
max_tool_calls through runtime. run(timeout_s=...) sets a shared root deadline.
runtime/framework and run options are Pydantic contracts; Agent policy validates too.
Do not introduce Scheduler, Policy or Harness constructors. A System can define
the coordination of a harness; that architecture also includes actors, tools,
context and execution controls. A caller timeout does not kill a running thread.

Keep parsing, arithmetic and policy in deterministic Tools. A Skill declares
Tools/instructions; it does not silently add execution edges. A Python actor
has one Tool; compose multiple operations with Graph. Never describe a
Python fixture as a language-model reasoner or semantic judge.

Graph is the sole public graph name, exposing the original LangGraph StateGraph.
Do not generate toolkit.StateGraph, toolkit.check or a check decorator.
Use toolkit.tool and toolkit.skill factories; toolkit.Tool and toolkit.Skill
constructors are not public API. Constructors
validate local contracts; owner.compile prepares and checks graph structure without
executing business work. Agent organizes a capability; System coordinates the app.
Graph remains a definition: execute through its Agent/System/Environment for RunResult.

Use named functions for teaching nodes. Pydantic Tools with input_schema and one
business parameter receive the model instance; annotate that parameter accordingly.
Use output_schema for validated results. Graph nodes select input_schema fields;
do not add defaults to satisfy missing input. Eval isolates toolkit Memory per case,
including reads/writes through node closures; SDK sessions and external effects
are not isolated. Do not describe Eval as a general sandbox or a side-effect-free run.

## Information and execution

Context holds immutable finite JSON and source identifiers; Memory stores
bounded local episodes. State holds business channels; lineage explains actual
work. Tools request context with `*, context: toolkit.Context`; LangGraph nodes
use the same keyword-only context: toolkit.Context. No clients or credentials in Context or state.

compile prepares without inference. Agent/System run(input); Environment/Eval
run their configured records/cases. arun is the async form. Return RunResult;
check ok/status/errors, invariants and serializable lineage. Pause inside graph
nodes with toolkit.pause; resume on the same compiled object and process.
Completed work is retained, but an interrupted callback restarts. Separate
side effects into nodes or make them idempotent. Do not claim durable recovery.

Environment state, observe(record,state), update(state,record,result) and
stop(state,result) govern episodes. max_steps=None or a positive ceiling;
records/stop/root deadline can terminate earlier. Public reset/step/reward/spaces are
not implemented. Eval explicitly targets Agent, System or Environment and is
fail-fast; independent negative cases retain all decisions. An optional judge
Agent can consume inference. A fixture only tests the judge protocol.

Borrow an externally prepared AWS session through runtime(session=...) only for
Bedrock. It explicitly selects IAM; API key/endpoint and conflicting region are
rejected. The resource stays out of Context, state, Memory, repr and serialized
configuration. Toolkit invocations sharing it are serialized; unrelated external
use is the caller's responsibility. Do not close it or move it across processes.
The separate agentic-systems-ada package offers read-only configuration diagnostics;
it is not installed by all and does not certify AWS/ADA access or repair variables.

## Workflow and evidence

Start with one small declaration and a deterministic input → process → output.
Add contracts, negative controls and a bounded root deadline before external providers.
Read [the conceptual model](references/conceptual-model.md) for architecture,
[project structure](references/project-contract.md) for application layout,
[provider/framework rules](references/provider-framework.md) for SDK options,
and [testing](references/testing.md) for acceptance. Read
[actor recipes](references/actor-recipes.md) before building required-tool actors.

Keep notebooks readable and executable in order. Show actual Tool/Skill/Agent/
System/Environment/Eval declarations relevant to the lesson and its assertions.
Local functions with visible bodies are appropriate. Do not import another
example's run/build/demonstrate/verify to hide the composition being taught.
Expose connection/protocol infrastructure separately when it is not the lesson.
Use the public signatures, not historical aliases or a wall of runtime flags.
Preserve all failed attempts and bind validation to the installed wheel hash.
A successful shared scenario does not certify every example or SDK feature.

Real inference needs explicit authorization and a persistent money/request cap,
including failures, retries, judges and local Ollama. Freeze models/endpoints
before calls; no silent substitution. Unavailable GPU/service/catalog routes
stay pending. Keep credentials outside source, notebooks, manifests and bundles.

For delivery read [distribution](references/release-distribution.md). A wheel
contains the SDK/CLI and this authoring skill. Application
source, notebooks and Studio remain separate artifacts. Never infer permission to publish, send messages or deploy
from permission to build or test.

## Integration boundaries

Declare endpoint and credentials per actor when mixing Ollama local/cloud; native honors explicit connection settings before environment defaults. Keep credentials out of Context and traces. Bedrock/Qwen may omit a required nullable field even with strict schema; fail closed, retain evidence and never invent defaults. This is a documented known limitation, not a passed compatibility case.
