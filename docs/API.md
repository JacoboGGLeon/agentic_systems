# API - Agentic Systems

This document describes the public API as a stable product surface. Tutorials
teach the same API step by step; source modules implement it.

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

Recommended user code should start with:

```text
agent
runtime
scheduler
output_schema
final_answer
normalize_output
tool
Tool
Agent
RunResult
LineageMemory
LineageStep
lineage_memory
AgentContract
ContractPolicySpec
RunPolicy
validate_contract_policy
RuntimeConfig
SchedulerConfig
OutputSchema
human_result
human_results
load_skill
Skill
LoadedSkill
expect
core
providers
integrations
```

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
| `python-runtime` | Local deterministic execution for tools and smoke tests. |
| `openai-runtime` | Direct OpenAI provider path. |
| `bedrock-runtime` | AWS Bedrock Runtime provider path. |
| `vllm-runtime` | OpenAI-compatible vLLM provider path for local or Colab GPU inference. |
| `auto` | Selects one concrete provider from environment signals before execution. |

Canonical frameworks are orchestration/integration facades. They are not model
providers:

| Framework | Use |
|---|---|
| `langgraph` | LangGraph graph orchestration. |
| `openai-agents` | OpenAI Agents-style integration facade over the selected runtime. |
| `strands` | Strands integration facade over the selected runtime. |

Do not use `framework="openai-runtime"`: `openai-runtime` is a provider/engine.
Use `framework="openai-agents"` when the integration is OpenAI Agents-style and
let `runtime(provider="auto")` or `runtime(provider="openai-runtime")` select the
backend.

Best practice: keep `provider="auto"` at the boundary where code moves between
local, vLLM, OpenAI and AWS environments. Use `runtime.describe()` in notebooks and
CLI diagnostics to make the selected provider visible. `describe()` performs a
dry resolution from environment variables; it does not execute models.

OpenAI runtime reads configuration from the environment or `.env`:

```text
OPENAI_API_KEY
AGENTIC_SYSTEMS_OPENAI_MODEL_ID
OPENAI_MODEL_ID
OPENAI_MODEL
OPENAI_BASE_URL
OPENAI_ORG_ID
OPENAI_PROJECT
```

vLLM runtime reads configuration from the environment or `.env`:

```text
VLLM_BASE_URL
VLLM_API_BASE
AGENTIC_SYSTEMS_VLLM_BASE_URL
VLLM_MODEL_ID
VLLM_MODEL
AGENTIC_SYSTEMS_VLLM_MODEL_ID
VLLM_API_KEY
AGENTIC_SYSTEMS_VLLM_API_KEY
```

`vllm-runtime` is an OpenAI-compatible client path. It expects a running vLLM
server, usually at `http://127.0.0.1:8000/v1`, and uses the OpenAI SDK client.
Install `agentic-systems[openai]` for the client dependency. Install and run
`vllm` separately in GPU environments such as Colab.

`runtime.describe()` shows safe configuration flags in `configuration.openai`
and `configuration.vllm`. It never prints API keys.

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
skill = toolkit.Skill(
    name="calculator_skill",
    description="Arithmetic tools and instructions.",
    tools=[add],
    prompts={"instructions": "Use arithmetic tools and return a structured answer."},
)

agent = toolkit.agent(name="skill_agent", instructions=skill.instructions, skills=[skill])
```

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

result = agent.run({"tool": "add", "input": {"a": 2, "b": 3}}, mode="eval")
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
toolkit.human_results([result], pretty=False)
```

`print_human_result` and `print_human_results` remain public aliases, but new
docs and notebooks should prefer `human_result` and `human_results`.

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
system = toolkit.AgenticSystem(model="local-python", runtime=runtime)

@system.tool
def multiply(a: int, b: int) -> dict:
    return {"result": a * b}

agent = system.agent(name="system_agent", instructions="Use registered tools.")
inspection = system.inspect()
inspection.raise_if_errors()
```

Public system names:

```text
AgenticSystem
PublicToolRegistry
```

## Graph Integrations

Graph APIs coordinate state, nodes and edges. They do not replace tools, agents
or systems.

```python
node = toolkit.agent_node(agent, input_mapper=..., output_mapper=...)
graph = toolkit.graph(state=..., nodes=[...], edges=[...])
```

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
observation, info = env.reset()
observation, reward, terminated, truncated, info = env.step(action=None)

report = toolkit.run_eval(agent, cases)
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

## Tutorials API Coverage

Tutorials are the canonical learning path:

| Notebook | API focus |
|---|---|
| `00_runtime_api.ipynb` | `runtime`, `scheduler`, `RuntimeConfig.describe`, provider auto y engines canonicos. |
| `00_runtime_bedrock_provider_api.ipynb` | `bedrock-runtime`, AWS diagnostics, Converse and embeddings smoke. |
| `00_runtime_openai_provider_api.ipynb` | `openai-runtime`, OpenAI config and native provider smoke. |
| `00_runtime_vllm_provider_api.ipynb` | `vllm-runtime`, OpenAI-compatible vLLM config and optional Colab/GPU smoke. |
| `00_runtime_scheduler_api.ipynb` | `scheduler`, limits, retry and timeout behavior. |
| `01_tool_api.ipynb` | `tool`, `Tool`, contracts and direct tool execution. |
| `02_skill_api.ipynb` | `Skill`, skill validation and skill-backed agents. |
| `03_agent_api.ipynb` | `agent`, `Agent`, contracts, policies and `RunResult`. |
| `04_human_result_api.ipynb` | `final_answer`, `normalize_output`, `human_result`. |
| `05_lineage_memory_api.ipynb` | `LineageMemory`, prompt context and trace explanation. |
| `06_integrations_strands_api.ipynb` | Strands integration facade. |
| `07_integrations_openai_runtime_api.ipynb` | native OpenAI runtime path. |
| `08_system_api.ipynb` | `AgenticSystem`, registry, inspect and deterministic pipeline. |
| `09_graph_api.ipynb` | `agent_node`, `graph`, state and node orchestration. |
| `10_environment_eval_api.ipynb` | `AgenticEnvironment`, rewards, `run_eval`, reports. |
| `11_multi_agentic_system_api.ipynb` | Multi-agent native system with deterministic and optional LM agents. |
| `12_multi_agentic_graph_api.ipynb` | Multi-agent graph with state, nodes and local fallback. |
| `13_single_agentic_system_api.ipynb` | End-to-end single-agent system path. |
| `14_multi_agentic_system_api.ipynb` | End-to-end multi-agent system path. |

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

This section is the documentation checksum for the public surface exported by `agentic_systems.PUBLIC_API`. If a symbol is added to the source API, it must appear here and have narrative coverage in the sections above.

```text
agent
runtime
scheduler
load_skill
default_model_id
default_region
AgenticSystem
PublicToolRegistry
Agent
Tool
tool
expect
human_result
human_results
print_human_result
print_human_results
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
RuntimeConfig
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



