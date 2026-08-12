# Migration From 1.1 To 2.0

Agentic Systems 2.0 keeps the 111 top-level names published by 1.1.3 and adds
only `toolkit.framework`. The resulting top-level inventory has 112 names.

This is a clean major-version boundary. Removed routes do not emit warnings,
silently fall back, or remain available through compatibility modules. Projects
that need the old behavior should stay pinned to `agentic-systems==1.1.3` while
they migrate.

## Framework Semantics

In 1.1, `framework="openai-agents"` and `framework="strands"` recorded intent
but still executed the Provider loop directly. In 2.0 all four canonical
Frameworks execute:

| Framework | 2.0 execution owner |
|---|---|
| `native` | Agentic Systems Provider engine |
| `langgraph` | A compiled LangGraph node |
| `openai-agents` | OpenAI Agents `Runner` |
| `strands` | `strands.Agent` |

String configuration remains valid:

```python
agent = toolkit.agent(
    name="researcher",
    runtime=toolkit.runtime(provider="bedrock-runtime"),
    framework="strands",
)
```

Use `toolkit.framework(...)` when the native SDK needs constructor or run
options:

```python
framework = toolkit.framework(
    "strands",
    agent_kwargs={"tools": [mcp_client], "hooks": [audit_hook]},
    run_kwargs={"structured_output_model": ResearchReport},
)
```

`agent_kwargs` reach the native Agent constructor and `run_kwargs` reach the
native execution call. Unknown options are not filtered; the SDK raises its
normal error. Agentic Systems reserves model/name/instruction keys and clamps
native turn limits to `RunPolicy.max_turns`.

`Agent.prepare()` constructs the SDK object without inference. Inspect
`Agent.native_agent` after preparation and `RunResult.native_result` after
execution. Both native objects are private to the in-memory lifecycle and are
excluded from JSON, traces and lineage.

## Removed Imports And Names

| 1.1 route | 2.0 route |
|---|---|
| `agentic_systems.providers.python_direct` | `agentic_systems.providers.python_runtime` |
| `PythonDirectProvider` | `PythonRuntimeProvider` |
| `PythonDirectEngine` | `PythonRuntimeEngine` |
| `agentic_systems.engines.python_direct` | Removed; Providers own execution |
| `agentic_systems.tools.compat.ToolEvent` | `agentic_systems.tools.ToolEvent` |
| `agentic_systems.tools.compat.Toolkit` | `agentic_systems.tools.Toolkit` |
| `PYTHON_DIRECT_ENGINE` | `PYTHON_RUNTIME_ENGINE` |

`supported_engine_names(include_aliases=...)` becomes
`supported_engine_names()`. Runtime aliases are not returned or accepted.

`RuntimeConfig.coerce(..., engine=...)` becomes
`RuntimeConfig.coerce(..., provider=...)`.

`AgentContract(output_contains=...)` becomes
`AgentContract(expected_output=...)`.

## Removed Bedrock-Specific Framework Bridge

The 1.1 Bedrock methods that directly constructed and ran OpenAI Agents are
replaced by the general Provider x Framework route. The following routes are
removed without aliases or shims:

- `as_openai_runtime_tools`, `create_openai_agent` and
  `openai_runtime_model_provider`.
- `run_openai_agent_sync` and `run_openai_agent`.
- `audit_openai_tool_outputs`, `openai_compact_trace`,
  `validate_expected_tool_outputs` and `print_openai_audit`.
- `BedrockRuntime(..., disable_openai_runtime_tracing=...)`.
- `BedrockRuntimeClient(..., disable_framework_tracing=...)`.

Framework tracing is owned by each native SDK. Configure it through that SDK's
documented environment or tracing API; Agentic Systems no longer exposes a
parallel tracing switch.

```python
agent = toolkit.agent(
    name="researcher",
    runtime=toolkit.runtime(provider="bedrock-runtime"),
    framework=toolkit.framework("openai-agents"),
)
result = agent.run(prompt)
```

Do not combine the old Bedrock bridge with the new adapter. The OpenAI Agents
`Runner` now owns turns, Tools, handoffs and guardrails while the Bedrock model
bridge performs one Converse inference per SDK turn.

## Extras

```bash
pip install "agentic-systems[openai-agents]"
pip install "agentic-systems[strands]"
```

The base installation remains lazy: importing `agentic_systems` does not import
OpenAI, OpenAI Agents, Strands, LangGraph, boto3 or vLLM.

## Migration Checklist

1. Pin production to `1.1.3` while adapting imports and aliases.
2. Replace every declarative Framework assumption with an explicit extra.
3. Move native SDK options into `toolkit.framework(...)`.
4. Replace the Bedrock-specific OpenAI bridge with the general Agent route.
5. Assert `RunResult.meta["framework_adapter"]` equals the requested Framework.
6. Keep serialized persistence on `RunResult`; never serialize native objects.
7. Run the project's tests against `2.0.0a1`, then the release candidate.
