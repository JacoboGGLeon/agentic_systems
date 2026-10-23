# Superficie efectiva 2.1.3

Generada desde el SDK instalado con `scripts/inventory_current_213.py`.

Incluye las firmas, campos y métodos soportados; los tipos retornados no tienen otro constructor público.

| Entrada / miembro | Tipo | Parámetros | Tutorial | Ejemplo |
|---|---|---|---|---|
| `tool` | function | `function=None, name=None, description=None, input_schema=None, output_schema=None, metadata=None` | 01 | examples/tool_contracts/example.py |
| `skill` | function | `name, description='', tools=(), instructions='', version='0.1.0', metadata=None` | 01 | examples/portable_skills/example.py |
| `load_skill` | function | `path` | 01 | examples/portable_skills/example.py |
| `Action` | constructor | `name, target, input=identity` | 02 | examples/flow_semantics/example.py |
| `Agent` | constructor | `name, flow=None, backend='native', skills=(), runtime=None, framework=None, instructions='', contract=None, policy=None` | 02,06,10 | examples/agent_contracts/example.py |
| `System` | constructor | `name, flow=None, backend='native'` | 03 | examples/flow_semantics/example.py |
| `Sequence` | constructor | `steps, name='sequence'` | 02,03 | examples/flow_semantics/example.py |
| `Parallel` | constructor | `steps, join, name='parallel'` | 02,03 | examples/flow_semantics/example.py |
| `Graph` | constructor | `nodes, edges, start, max_visits=20, name='graph'` | 02,03 | examples/flow_semantics/example.py |
| `Environment` | constructor | `name, unit, records, max_steps=None, memory=None, observe=None, update=None, stop=None` | 04 | examples/episode_memory/example.py |
| `Eval` | constructor | `name, unit, cases, checks=(), judge=None, rubric=None` | 05,10 | examples/evaluation_checks/example.py |
| `Limits` | constructor | `max_actions=100, timeout_s=10` | 07 | examples/execution_lifecycle/example.py |
| `RunResult` | constructor | `text='', final=<factory>, data=<factory>, ok=True, messages=(), tool_events=(), raw_responses=(), usage=<factory>, engine='python-runtime', model='', mode='default', trace_schema_version='agentic_systems.trace.v1', validation=None, errors=(), meta=<factory>, execution_id=<factory>, parent_execution_id=None, children=()` | 07 | examples/results_lineage/example.py |
| `runtime` | function | `provider, model=None, region=None, endpoint=None, api_key=None, timeout_s=60.0, max_retries=0, max_tool_calls=5, max_turns=6, max_tokens=None, backoff_s=0.0, max_concurrency=1` | 06 | examples/provider_framework_conformance/example.py |
| `framework` | function | `name, agent_kwargs=None, run_kwargs=None` | 06 | examples/provider_framework_conformance/example.py |
| `model_artifact` | function | `model, base_model=None, adapter_path=None, tokenizer=None, revision=None, quantization=None, metadata=None` | 08 | examples/model_serving/example.py |
| `model_server` | function | `artifact, profile='fast', served_model_name=None, host='127.0.0.1', port=8000, tool_call_parser='hermes', reasoning_parser=None, enable_auto_tool_choice=True, api_key='vllm', startup_timeout_s=600.0, log_path='vllm-server.log', binary='vllm', extra_args=(), gpu_memory_utilization=None, max_model_len=None, max_num_seqs=None` | 08 | examples/model_serving/example.py |
| `Tool.arun` | method | `input=None` | 01 | examples/tool_contracts/example.py |
| `Tool.inspect` | method | `` | 01 | examples/tool_contracts/example.py |
| `Tool.run` | method | `input=None` | 01 | examples/tool_contracts/example.py |
| `Tool.name` | field | `` | 01 | examples/tool_contracts/example.py |
| `Tool.description` | field | `` | 01 | examples/tool_contracts/example.py |
| `Tool.metadata` | field | `` | 01 | examples/tool_contracts/example.py |
| `Skill.inspect` | method | `` | 01 | examples/portable_skills/example.py |
| `Skill.name` | field | `` | 01 | examples/portable_skills/example.py |
| `Skill.tools` | field | `` | 01 | examples/portable_skills/example.py |
| `Skill.instructions` | field | `` | 01 | examples/portable_skills/example.py |
| `Skill.description` | field | `` | 01 | examples/portable_skills/example.py |
| `Skill.version` | field | `` | 01 | examples/portable_skills/example.py |
| `Skill.metadata` | field | `` | 01 | examples/portable_skills/example.py |
| `Runtime.inspect` | method | `` | 06 | examples/provider_framework_conformance/example.py |
| `Runtime.provider` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Runtime.model` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Runtime.region` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Runtime.endpoint` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Runtime.timeout_s` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Runtime.max_retries` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Runtime.max_tool_calls` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Runtime.max_turns` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Runtime.max_tokens` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Runtime.backoff_s` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Runtime.max_concurrency` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Framework.inspect` | method | `` | 06 | examples/provider_framework_conformance/example.py |
| `Framework.name` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Framework.agent_kwargs` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Framework.run_kwargs` | field | `` | 06 | examples/provider_framework_conformance/example.py |
| `Artifact.inspect` | method | `` | 08 | examples/model_serving/example.py |
| `Artifact.model` | field | `` | 08 | examples/model_serving/example.py |
| `Artifact.base_model` | field | `` | 08 | examples/model_serving/example.py |
| `Artifact.adapter_path` | field | `` | 08 | examples/model_serving/example.py |
| `Artifact.tokenizer` | field | `` | 08 | examples/model_serving/example.py |
| `Artifact.revision` | field | `` | 08 | examples/model_serving/example.py |
| `Artifact.quantization` | field | `` | 08 | examples/model_serving/example.py |
| `Artifact.metadata` | field | `` | 08 | examples/model_serving/example.py |
| `Server.command` | property | `` | 08 | examples/model_serving/example.py |
| `Server.endpoint` | property | `` | 08 | examples/model_serving/example.py |
| `Server.health` | method | `` | 08 | examples/model_serving/example.py |
| `Server.inspect` | method | `` | 08 | examples/model_serving/example.py |
| `Server.start` | method | `` | 08 | examples/model_serving/example.py |
| `Server.stop` | method | `` | 08 | examples/model_serving/example.py |
| `Compiled.arun` | method | `input=None, limits=Limits(max_actions=100, timeout_s=10)` | 07 | examples/execution_lifecycle/example.py |
| `Compiled.inspect` | method | `` | 07 | examples/execution_lifecycle/example.py |
| `Compiled.run` | method | `input=None, limits=Limits(max_actions=100, timeout_s=10)` | 07 | examples/execution_lifecycle/example.py |
| `Captured.arun` | method | `limits=Limits(max_actions=100, timeout_s=10)` | 04,05 | examples/episode_memory/example.py |
| `Captured.inspect` | method | `` | 04,05 | examples/episode_memory/example.py |
| `Captured.run` | method | `limits=Limits(max_actions=100, timeout_s=10)` | 04,05 | examples/episode_memory/example.py |
| `Lineage.explain` | method | `` | 07 | examples/results_lineage/example.py |
| `Lineage.to_dict` | method | `` | 07 | examples/results_lineage/example.py |
| `Lineage.to_prompt_context` | method | `max_chars=1600` | 07 | examples/results_lineage/example.py |
| `Lineage.name` | field | `` | 07 | examples/results_lineage/example.py |
| `Lineage.question` | field | `` | 07 | examples/results_lineage/example.py |
| `Lineage.goal` | field | `` | 07 | examples/results_lineage/example.py |
| `Lineage.answer` | field | `` | 07 | examples/results_lineage/example.py |
| `Lineage.ok` | field | `` | 07 | examples/results_lineage/example.py |
| `Lineage.steps` | field | `` | 07 | examples/results_lineage/example.py |
| `Lineage.usage` | field | `` | 07 | examples/results_lineage/example.py |
| `Lineage.validation` | field | `` | 07 | examples/results_lineage/example.py |
| `Lineage.tags` | field | `` | 07 | examples/results_lineage/example.py |
| `Lineage.metadata` | field | `` | 07 | examples/results_lineage/example.py |
| `Lineage.schema_version` | field | `` | 07 | examples/results_lineage/example.py |
| `Validation.to_dict` | method | `` | 07 | examples/results_lineage/example.py |
| `Validation.ok` | field | `` | 07 | examples/results_lineage/example.py |
| `Validation.issues` | field | `` | 07 | examples/results_lineage/example.py |
| `Event.id` | field | `` | 07 | examples/results_lineage/example.py |
| `Event.name` | field | `` | 07 | examples/results_lineage/example.py |
| `Event.input` | field | `` | 07 | examples/results_lineage/example.py |
| `Event.output` | field | `` | 07 | examples/results_lineage/example.py |
| `Event.ok` | field | `` | 07 | examples/results_lineage/example.py |
| `Event.error` | field | `` | 07 | examples/results_lineage/example.py |
| `Event.duration_ms` | field | `` | 07 | examples/results_lineage/example.py |
| `Event.meta` | field | `` | 07 | examples/results_lineage/example.py |
| `Endpoint.url` | field | `` | 08 | examples/model_serving/example.py |
| `Endpoint.model` | field | `` | 08 | examples/model_serving/example.py |
| `Endpoint.backend` | field | `` | 08 | examples/model_serving/example.py |
| `Endpoint.api_key_configured` | field | `` | 08 | examples/model_serving/example.py |
| `Endpoint.pid` | field | `` | 08 | examples/model_serving/example.py |
| `Endpoint.owned` | field | `` | 08 | examples/model_serving/example.py |
| `Health.status` | field | `` | 08 | examples/model_serving/example.py |
| `Health.endpoint` | field | `` | 08 | examples/model_serving/example.py |
| `Health.detail` | field | `` | 08 | examples/model_serving/example.py |
| `Action.name` | field | `` | 02 | examples/flow_semantics/example.py |
| `Action.target` | field | `` | 02 | examples/flow_semantics/example.py |
| `Action.input` | field | `` | 02 | examples/flow_semantics/example.py |
| `Agent.arun` | method | `input=None, limits=Limits(max_actions=100, timeout_s=10)` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.compile` | method | `` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.inspect` | method | `` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.run` | method | `input=None, limits=Limits(max_actions=100, timeout_s=10)` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.name` | field | `` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.flow` | field | `` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.backend` | field | `` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.kind` | field | `` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.skills` | field | `` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.runtime` | field | `` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.framework` | field | `` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.instructions` | field | `` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.contract` | field | `` | 02,06,10 | examples/agent_contracts/example.py |
| `Agent.policy` | field | `` | 02,06,10 | examples/agent_contracts/example.py |
| `System.arun` | method | `input=None, limits=Limits(max_actions=100, timeout_s=10)` | 03 | examples/flow_semantics/example.py |
| `System.compile` | method | `` | 03 | examples/flow_semantics/example.py |
| `System.inspect` | method | `` | 03 | examples/flow_semantics/example.py |
| `System.run` | method | `input=None, limits=Limits(max_actions=100, timeout_s=10)` | 03 | examples/flow_semantics/example.py |
| `System.name` | field | `` | 03 | examples/flow_semantics/example.py |
| `System.flow` | field | `` | 03 | examples/flow_semantics/example.py |
| `System.backend` | field | `` | 03 | examples/flow_semantics/example.py |
| `System.kind` | field | `` | 03 | examples/flow_semantics/example.py |
| `Sequence.steps` | field | `` | 02,03 | examples/flow_semantics/example.py |
| `Sequence.name` | field | `` | 02,03 | examples/flow_semantics/example.py |
| `Parallel.steps` | field | `` | 02,03 | examples/flow_semantics/example.py |
| `Parallel.join` | field | `` | 02,03 | examples/flow_semantics/example.py |
| `Parallel.name` | field | `` | 02,03 | examples/flow_semantics/example.py |
| `Graph.nodes` | field | `` | 02,03 | examples/flow_semantics/example.py |
| `Graph.edges` | field | `` | 02,03 | examples/flow_semantics/example.py |
| `Graph.start` | field | `` | 02,03 | examples/flow_semantics/example.py |
| `Graph.max_visits` | field | `` | 02,03 | examples/flow_semantics/example.py |
| `Graph.name` | field | `` | 02,03 | examples/flow_semantics/example.py |
| `Environment.arun` | method | `limits=Limits(max_actions=100, timeout_s=10)` | 04 | examples/episode_memory/example.py |
| `Environment.compile` | method | `` | 04 | examples/episode_memory/example.py |
| `Environment.inspect` | method | `` | 04 | examples/episode_memory/example.py |
| `Environment.run` | method | `limits=Limits(max_actions=100, timeout_s=10)` | 04 | examples/episode_memory/example.py |
| `Environment.name` | field | `` | 04 | examples/episode_memory/example.py |
| `Environment.unit` | field | `` | 04 | examples/episode_memory/example.py |
| `Environment.records` | field | `` | 04 | examples/episode_memory/example.py |
| `Environment.max_steps` | field | `` | 04 | examples/episode_memory/example.py |
| `Environment.memory` | field | `` | 04 | examples/episode_memory/example.py |
| `Environment.observe` | field | `` | 04 | examples/episode_memory/example.py |
| `Environment.update` | field | `` | 04 | examples/episode_memory/example.py |
| `Environment.stop` | field | `` | 04 | examples/episode_memory/example.py |
| `Eval.arun` | method | `limits=Limits(max_actions=100, timeout_s=10)` | 05,10 | examples/evaluation_checks/example.py |
| `Eval.compile` | method | `` | 05,10 | examples/evaluation_checks/example.py |
| `Eval.inspect` | method | `` | 05,10 | examples/evaluation_checks/example.py |
| `Eval.run` | method | `limits=Limits(max_actions=100, timeout_s=10)` | 05,10 | examples/evaluation_checks/example.py |
| `Eval.name` | field | `` | 05,10 | examples/evaluation_checks/example.py |
| `Eval.unit` | field | `` | 05,10 | examples/evaluation_checks/example.py |
| `Eval.cases` | field | `` | 05,10 | examples/evaluation_checks/example.py |
| `Eval.checks` | field | `` | 05,10 | examples/evaluation_checks/example.py |
| `Eval.judge` | field | `` | 05,10 | examples/evaluation_checks/example.py |
| `Eval.rubric` | field | `` | 05,10 | examples/evaluation_checks/example.py |
| `Limits.max_actions` | field | `` | 07 | examples/execution_lifecycle/example.py |
| `Limits.timeout_s` | field | `` | 07 | examples/execution_lifecycle/example.py |
| `RunResult.check_invariants` | method | `` | 07 | examples/results_lineage/example.py |
| `RunResult.lineage` | method | `name='run', question=None, goal='', tags=None, metadata=None, max_tool_rows=3` | 07 | examples/results_lineage/example.py |
| `RunResult.to_dict` | method | `` | 07 | examples/results_lineage/example.py |
| `RunResult.trace` | method | `mode='compact'` | 07 | examples/results_lineage/example.py |
| `RunResult.walk` | method | `` | 07 | examples/results_lineage/example.py |
| `RunResult.text` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.final` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.data` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.ok` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.messages` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.tool_events` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.raw_responses` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.usage` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.engine` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.model` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.mode` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.trace_schema_version` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.validation` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.errors` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.meta` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.execution_id` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.parent_execution_id` | field | `` | 07 | examples/results_lineage/example.py |
| `RunResult.children` | field | `` | 07 | examples/results_lineage/example.py |
| `CLI.version` | command | `` | 00 | examples/package_install/example.py |
| `CLI.api` | command | `` | 00 | examples/package_install/example.py |
| `CLI.doctor` | command | `` | 00 | examples/package_install/example.py |
| `CLI.new` | command | `destination` | 00 | examples/package_install/example.py |

[Tipos, defaults, modos de argumentos y enlaces de pruebas](api_213_contract.json).
La evidencia de estas familias de contratos es offline. La [campaña externa](../revisions/2.1.3/framework-evidence/REPORT.md) documenta por separado sus modelos y escenarios live. GPU, IAM y opciones arbitrarias de SDK externos no quedan acreditados por este inventario.
