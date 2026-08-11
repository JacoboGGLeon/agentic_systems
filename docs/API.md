# API - Agentic Systems

This document is the complete public API reference. For an installation path,
conceptual introduction or executable learning sequence, start with the
[documentation map](README.md). Tutorials teach the same API step by step;
source modules implement it.

## Import Rule

Use one import in notebooks, examples and user code:

```python
import agentic_systems as toolkit
```

Avoid importing from internal modules unless you are maintaining the library.
The curated public names live in `agentic_systems.api`.

## API Tiers

| Tier | Purpose |
|---|---|
| `RECOMMENDED_API` | Names to teach first and use by default. |
| `ADVANCED_API` | Public names for systems, environments, evals, engines and notebook utilities. |
| `PUBLIC_API` | Complete top-level importable surface. |

Canonical user code starts with one compositional grammar:

```python
toolkit.tool(...)
toolkit.skill(...)
toolkit.agent(...)
toolkit.system(...)
toolkit.graph(...)
toolkit.environment(...)
toolkit.eval(...)
```

These canonical constructors are the teaching path. Their class counterparts
(`Tool`, `Skill`, `Agent`, `AgenticSystem`, `AgenticEnvironment`, `Evaluator`)
remain public for typing, extension and advanced lifecycle control. Runtime,
contracts, results, lineage and rendering support the grammar without becoming
alternative construction paths.

`toolkit.system(...)` is provider-agnostic: provider and model routing belong to
`toolkit.runtime(...)`, not to the system factory.

## Runtime And Providers

Runtime configuration is explicit and inspectable:

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
| `python-runtime` | Local deterministic execution for tools and smoke tests. |
| `auto` | Selects one concrete provider from environment signals before execution. |

Canonical framework identities describe orchestration intent or an implemented
integration. They are not model providers:

| Framework | Use |
|---|---|
| `langgraph` | LangGraph graph orchestration. |
| `openai-agents` | Style-only identity over the selected runtime; no OpenAI Agents SDK adapter is included. |
| `strands` | Declarative compatibility identity; no Strands SDK adapter is included. |

Do not pass provider names as `framework`: runtime providers are selected with `provider=...`, while frameworks are selected with `framework=...`.
Use `framework="openai-agents"` to retain the existing style label and
let `runtime(provider="auto")` or `runtime(provider="openai-runtime")` select the
backend. This does not invoke the OpenAI Agents SDK.

Best practice: keep `provider="auto"` at the boundary where code moves between
local, vLLM, OpenAI and AWS environments. Use `runtime.describe()` in notebooks and
CLI diagnostics to make the selected provider visible. `describe()` performs a
dry resolution from environment variables; it does not execute models.

OpenAI runtime reads configuration from the environment or `.env`:

```text
OPENAI_API_KEY
OPENAI_MODEL
OPENAI_BASE_URL
```

vLLM runtime reads configuration from the environment or `.env`:

```text
VLLM_BASE_URL
VLLM_MODEL
VLLM_API_KEY
```

`vllm-runtime` is an OpenAI-compatible client path. It expects a running vLLM
server, usually at `http://127.0.0.1:8000/v1`, and uses the OpenAI SDK client.
Install `agentic-systems[openai]` when Agentic Systems only connects to an
existing endpoint. Install `agentic-systems[vllm]` only when the
same supported Linux environment also hosts the vLLM server. The server remains
external infrastructure; Agentic Systems never starts it implicitly.

Bedrock runtime reads configuration from the environment or `.env`:

```text
BEDROCK_MODEL_ID
AWS_REGION
AWS_DEFAULT_REGION
AWS_PROFILE
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
```

`runtime.describe()` shows safe configuration flags in `configuration.openai`,
`configuration.vllm` and `configuration.bedrock`. It never prints API keys,
secret keys or session tokens. Bedrock execution still uses the normal boto3/AWS
credential chain.

Integration-specific args stay owned by the selected framework. Agentic Systems
keeps a thin facade: `runtime(...)` selects provider/backend, `framework=...`
selects integration identity, and native framework options should be passed to
the concrete integration helper/factory that owns them. The library does not
reinterpret framework-specific behavior.

## Tools

A tool is the smallest executable capability. It should accept typed arguments
and return a dictionary.

```python
@toolkit.tool
def add(a: int, b: int) -> dict:
    """Add two integers."""
    return {"result": a + b}
```

Production tools should have stable names, docstrings and predictable payloads.
Use `Tool`, `tool`, `validate_tool_expectation`, `ToolExpectationValue` and
`toolkit.expect` when contracts need to be explicit.

## Skills

A skill packages tools, instructions, assets and metadata.

```python
skill = toolkit.skill(
    name="calculator_skill",
    description="Arithmetic tools and instructions.",
    tools=[add],
    prompts={"instructions": "Use arithmetic tools and return a structured answer."},
)

agent = toolkit.agent(name="skill_agent", instructions=skill.instructions, skills=[skill])
```

Compose packages without executing them:

```python
combined = toolkit.Skill.compose(skill_a, skill_b, name="combined")
report = combined.composition()
```

Different Tool, prompt, contract or policy definitions with the same identity fail
by default. Pass `on_conflict="keep"` or `on_conflict="replace"` only when
the precedence is intentional.

Public skill names:

```text
Skill
SkillManifest
LoadedSkill
load_skill
```

## Agents

An agent turns instructions, runtime, tools and skills into an executable unit.

```python
agent = toolkit.agent(
    name="calculator",
    instructions="Use the available tools and return a structured answer.",
    tools=[add],
    runtime=runtime,
)

result = agent.run({"tool": "add", "input": {"a": 2, "b": 3}})
```

Use `agent.run(...)` for sync execution and `agent.arun(...)` for async provider
flows. Use `AgentContract`, `RunPolicy` and `ContractPolicySpec` before runtime
calls when tool usage must be constrained.

### RunPolicy Parameters

`RunPolicy` is the execution contract for agent loops. It should be declared near the agent definition, not hidden inside a notebook cell.

| Parameter | Meaning | Recommended tutorial use |
|---|---|---|
| `max_turns` | Maximum internal turns before the run must stop. | Keep small, usually `4` to `8`. |
| `max_tool_calls` | Maximum tool calls allowed during the run. | Set when the expected path is tool-based. |
| `max_tokens` | Provider token budget when supported. | Use for LM providers; leave `None` for deterministic Python. |
| `temperature` | LM randomness. | Use `0.0` for reproducible tutorials. |
| `tool_choice` | Tool selection strategy, usually `auto`. | Use `auto` unless teaching forced tool use. |
| `repair` | Whether invalid outputs/tool calls may be repaired. | Keep `True` for robust user flows. |
| `max_repairs` | Maximum repair attempts. | Use `1` or `2`; higher values hide failures. |
| `finalize` | Finalization behavior when the loop reaches limits. | Use `on_max_turns` for evaluable LM runs. |
| `trace` | Trace detail level. | Use `compact` in tutorials and `debug` for diagnosis. |
| `strict` | Whether contract validation is strict. | Use `True` for public examples and tests. |

## Results And Human Output

`RunResult` is the stable execution envelope.

```text
result.final       user-facing answer dictionary
result.data        reusable evidence payload
result.text        text fallback
result.tool_events executed tool events
result.usage       runtime usage metadata
result.validation  contract validation
result.errors      structured errors
```

Render user-facing output with:

```python
toolkit.human_result(result, pretty=False)
toolkit.human_result([result_a, result_b], pretty=False)
```

`human_result` is intentionally polymorphic: pass one result for one execution or a list of RunResult-like objects for a batch. There is no separate plural public API.

## Final Answer

Final answers are dictionaries. The helpers normalize arbitrary payloads:

```python
toolkit.normalize_output({"a": 1})    # {"a": 1}
toolkit.normalize_output([{"a": 1}])  # {"rows": [{"a": 1}]}
toolkit.normalize_output([1, 2])      # {"items": [1, 2]}
toolkit.normalize_output("ok")        # {"value": "ok"}
```

Use an output schema when the user requested fields:

```python
schema = toolkit.output_schema(["procedure", "final_result"])
answer = toolkit.final_answer({"procedure": ["2 + 3"], "final_result": 5}, schema=schema)
```

Public output names include `OutputSchema`, `AgenticOutput`, `RuntimeInfo`,
`UsageInfo`, `OutputToolEvent`, `OutputValidation`, `TraceEvent`,
`GraphStateOutput`, `EpisodeResult`, `FINAL_ANSWER_SCHEMA_VERSION`,
`AGENTIC_OUTPUT_SCHEMA_VERSION`, `OUTPUT_SCHEMA_VERSION` and
`AGENT_OUTPUT_SCHEMA_VERSION`.

## Lineage Memory

Lineage Memory explains what happened, how it happened and why the answer is
supported.

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

## System

`AgenticSystem` is the native system and composition factory. It registers tools,
skills, agents, runtime and contracts.

```python
system = toolkit.system(runtime=runtime)

@system.tool
def multiply(a: int, b: int) -> dict:
    return {"result": a * b}

agent = system.agent(name="system_agent", instructions="Use registered tools.")
inspection = system.inspect()
inspection.raise_if_errors()
structured = inspection.to_dict()
human = inspection.human_text()
composition = system.composition()
```

Tool and Skill registration rejects different definitions with an occupied name.
`system.tool(...)`, `system.skill(...)`, and Toolkit registration accept explicit
`on_conflict="keep"` or `on_conflict="replace"` policies. Composition decisions
and selected sources are included in inspection.

Public system names:

```text
AgenticSystem
InspectReport
PublicToolRegistry
```

### Static Inspection

`AgenticSystem.inspect()` returns an `InspectReport` without executing models or
Tools. The report supports its dictionary interface and exposes stable
structured sections for entities, relationships, contracts, Providers,
Frameworks, capabilities, conflicts, limits, degradation risks, and actionable
diagnostics. Use `to_dict()` for JSON serialization and `human_text()` for the
stable human view. `raise_if_errors()` turns configuration errors into a gate.
The schema is `agentic_systems.inspect.v1`.

Inspection may read registries, signatures, schemas, local validation and
declarative Provider or Framework profiles. It must not call a Tool or Agent,
hydrate SDK clients, probe credentials, compile Graphs, perform discovery or
make network/model calls. Structured output must survive a JSON round trip;
relationships and diagnostics remain deterministically ordered.

### Execution Context

Execution Context is a conceptual resolution view, not a public object. Runtime
selection remains in `RuntimeConfig`, composition remains in `AgenticSystem`,
per-run limits remain in `RunPolicy`, and state/evidence remain in their Graph,
Environment, and `RunResult` owners. Do not import or construct
`ExecutionContext`; no such public symbol exists in the 1.1 line. See
[Computational Model](COMPUTATIONAL_MODEL.md).

## Graph Integrations

Graph APIs coordinate state, nodes and edges. They do not replace tools, agents
or systems.

```python
node = toolkit.agent_node(agent, input=..., output=...)
graph = toolkit.graph(
    state=dict,
    nodes={"inspect": node},
    edges=[("START", "inspect"), ("inspect", "END")],
    engine="auto",
)
```

The default `engine="auto"` uses LangGraph when installed and falls back to the
dependency-free portable backend. Use `engine="portable"` for deterministic
core-only execution or `engine="langgraph"` when the native SDK is required.
The portable backend supports sequential and conditional routes and rejects
parallel branches explicitly instead of emulating framework behavior.

Public graph names:

```text
agent_node
graph
```

LangGraph remains optional. The core package must import without LangGraph.

## Environment And Evals

Environments execute episodes. Evals score cases.

```python
env = toolkit.AgenticEnvironment(records=records, transition_fn=transition, reward_fn=reward)
observation, info = env.reset(seed=17)
observation, reward, terminated, truncated, info = env.step(action=None)

report = toolkit.run_eval(
    agent,
    cases,
    determinism="seeded",
    seed=17,
    reproducibility_conditions=["same fixtures and provider configuration"],
)
```

Public names:

```text
AgenticEnvironment
EnvironmentTransition
AgentStepGraph
DynamicAgentRouterGraph
PlannedAgentGraph
build_agent_step_graph
build_dynamic_agent_router_graph
build_planned_agent_graph
environment_lineage
EvalCaseResult
EvalReport
EvalReproducibility
Evaluator
run_eval
```

## Engines

Engine names are public constants and helpers:

```text
BEDROCK_RUNTIME_ENGINE
OPENAI_RUNTIME_ENGINE
PYTHON_RUNTIME_ENGINE
VLLM_RUNTIME_ENGINE
SUPPORTED_ENGINES
canonical_engine_name
supported_engine_names
```

Do not build new user code against `agentic_systems.engines.*` modules. Use
`runtime(provider=...)`, providers and the constants above.

## Providers And Bedrock Primitive

Provider namespaces are public for explicit provider work:

```text
core
providers
integrations
BedrockRuntimeClient
DEFAULT_EMBEDDING_MODEL_ID
```

Use `BedrockRuntimeClient` only when you need direct Bedrock Runtime primitives.
Most user code should use `toolkit.runtime(provider="bedrock-runtime")`, `toolkit.runtime(provider="openai-runtime")`, `toolkit.runtime(provider="vllm-runtime")` or `toolkit.runtime(provider="auto")`.

## Notebook Utilities

Notebook utilities are public because tutorials use them, but they are not the
first layer to teach:

```text
configure_notebook_environment
show_json
show
compare
compose_result
mask_sensitive
aws_environment_snapshot
boto3_session_snapshot
vllm_environment_snapshot
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

Use `compose_result(...)` when a notebook combines several real executions into
one visible result, for example deterministic tools plus an optional LM review.
It preserves real engine names, framework metadata, usage and tool events so
tutorials do not hand-build `RunResult(...)` envelopes.

## CLI

The package exposes a small diagnostics CLI:

```bash
agentic-systems version
agentic-systems doctor --json
agentic-systems runtime --provider auto --json
agentic-systems api --tier public --json
agentic-systems public-api --all --json
```

The CLI is for inspection and packaging smoke tests. It should not contain
business logic.

See `docs/CLI.md` for command details.

## Provider Notebook Run All Contract

Provider notebooks are top-to-bottom programs. Live execution is enabled by
default, but an external call occurs only after public readiness diagnostics
confirm usable configuration. Missing infrastructure produces an actionable
skip and no fabricated `RunResult`. The `RUN_*_LIVE=0` variables are explicit
opt-outs for demos, CI, and offline validation.

## Tutorials API Coverage

Tutorials are the canonical learning path:

| Notebook | API focus |
|---|---|
| `00_runtime_api.ipynb` | Runtime, scheduler, provider profiles and dry provider resolution. |
| `00_runtime_bedrock_provider_api.ipynb` | Bedrock readiness and the canonical `runtime -> system -> agent -> RunResult` route. |
| `00_runtime_openai_provider_api.ipynb` | OpenAI readiness and the canonical `runtime -> system -> agent -> RunResult` route. |
| `00_runtime_vllm_provider_api.ipynb` | vLLM endpoint readiness and the canonical `runtime -> system -> agent -> RunResult` route. |
| `00_runtime_scheduler_api.ipynb` | `scheduler`, limits, retry and timeout behavior. |
| `01_tool_api.ipynb` | `tool`, `Tool`, contracts and direct tool execution. |
| `02_skill_api.ipynb` | `Skill`, skill validation and skill-backed agents. |
| `03_agent_api.ipynb` | `agent`, `Agent`, contracts, policies and `RunResult`. |
| `04_human_result_api.ipynb` | One real `RunResult` projected through human, output, summary and view APIs. |
| `05_lineage_memory_api.ipynb` | Lineage and composition derived from real `RunResult` evidence. |
| `06_integrations_strands_api.ipynb` | Strands declarative identity executed over a readiness-resolved Provider. |
| `07_integrations_openai_runtime_api.ipynb` | OpenAI Agents-style identity executed over the selected runtime. |
| `08_system_api.ipynb` | AgenticSystem fundamentals: ownership, registration, Skills, Agents and static inspection. |
| `09_graph_api.ipynb` | Graph state and agent nodes through `engine="auto"`, including the portable backend. |
| `10_environment_eval_api.ipynb` | Real Agent episodes, independent oracle rewards, reproducibility and Evals. |
| `11_single_agentic_system_api.ipynb` | End-to-end System, Agent and Eval with a selectable provider. |
| `12_multi_agentic_system_api.ipynb` | Two real Agent runs composed from their `RunResult` evidence. |
| `13_multi_agentic_graph_api.ipynb` | Multiple real Agents orchestrated through the public Graph API. |

## Documentation Rules

Good API documentation in this repo follows these rules:

```text
1. Show the stable import first.
2. Document the minimal object model before advanced helpers.
3. Include small runnable examples.
4. Name return values and failure behavior.
5. Keep optional dependencies explicit.
6. Link docs to tutorials without duplicating notebook code.
7. Do not document historical compatibility as the recommended path.
```

## Complete Public API Index

This section is the documentation checksum for `agentic_systems.__all__`. The maintainer inventory is `agentic_systems.api.PUBLIC_API`; it is not a top-level runtime attribute. If a symbol is added to the source API, it must appear here and have narrative coverage above.

```text
skill
agent
system
environment
eval
runtime
scheduler
load_skill
default_model_id
default_region
AgenticSystem
InspectReport
PublicToolRegistry
Agent
Tool
tool
expect
human_result
Skill
SkillManifest
LoadedSkill
AgentContract
ContractPolicySpec
RunPolicy
ToolExpectationValue
ValidationIssue
ValidationResult
normalize_tool_expectation
validate_contract_policy
validate_tool_expectation
RunResult
LineageMemory
LineageStep
lineage_memory
LINEAGE_SCHEMA_VERSION
AUTO_PROVIDER_ENV_VAR
DEFAULT_AUTO_PROVIDER_PRIORITY
RuntimeConfig
normalize_provider_priority
resolve_auto_provider
SchedulerConfig
OutputSchema
FINAL_ANSWER_SCHEMA_VERSION
final_answer
normalize_output
output_schema
AgenticOutput
RuntimeInfo
UsageInfo
OutputToolEvent
OutputValidation
TraceEvent
GraphStateOutput
EpisodeResult
BedrockRuntimeClient
DEFAULT_EMBEDDING_MODEL_ID
Chain
ChainStep
BEDROCK_RUNTIME_ENGINE
OPENAI_RUNTIME_ENGINE
PYTHON_RUNTIME_ENGINE
VLLM_RUNTIME_ENGINE
SUPPORTED_ENGINES
canonical_engine_name
supported_engine_names
agent_node
graph
EvalCaseResult
EvalReport
EvalReproducibility
Evaluator
run_eval
AgenticEnvironment
EnvironmentTransition
AgentStepGraph
DynamicAgentRouterGraph
PlannedAgentGraph
build_agent_step_graph
build_dynamic_agent_router_graph
build_planned_agent_graph
environment_lineage
AGENT_OUTPUT_SCHEMA_VERSION
OUTPUT_SCHEMA_VERSION
AGENTIC_OUTPUT_SCHEMA_VERSION
agent_output
agent_output_mapper
make_agent_output_mapper
configure_notebook_environment
show_json
show
compare
compose_result
mask_sensitive
aws_environment_snapshot
boto3_session_snapshot
vllm_environment_snapshot
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
TRACE_SCHEMA_VERSION
core
providers
integrations
__version__
```

## Provider Conformance API

The advanced `agentic_systems.providers` namespace exposes the Runtime/Provider
substitution contract:

```python
from agentic_systems.providers import (
    evaluate_provider_conformance,
    provider_profile,
    provider_profiles,
)

profile = provider_profile("python-runtime")
profile.check(["offline_execution"]).raise_if_failed()
```

`ProviderProfile.check` validates required and requested capabilities.
`evaluate_provider_conformance` applies the common observable suite to one
successful and one failed `RunResult`. Adapter classes expose the same profile
through `profile()`.

## Framework Boundary API

The advanced `agentic_systems.integrations` namespace exposes framework and
Graph boundary inspection without importing optional SDKs:

```python
from agentic_systems.integrations import (
    describe_graph_boundary,
    evaluate_framework_projection,
    framework_profile,
)

profile = framework_profile("langgraph")
profile.check(require_adapter=True).raise_if_failed()
```

`framework_profile("openai-agents")` reports `style-only` and
`framework_profile("strands")` reports `declarative-only`. Only LangGraph has an
implemented external adapter in the current 1.1 line.

`describe_graph_boundary(...)` distinguishes portable Agentic Systems Graphs
from framework-native wrappers. `evaluate_framework_projection(...)` verifies
that a serialized RunResult stored under an explicit `result_key` preserves the
central result contract.
