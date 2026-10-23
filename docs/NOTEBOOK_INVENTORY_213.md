# Inventario exhaustivo de notebooks 2.1.3

Se encontraron **42 notebooks: 13 vigentes y 29 históricos/generados**. Se incluyen las copias históricas, sin contarlas como ejemplos adicionales vigentes.

La gramática directa se obtiene del AST de las celdas. Las referencias compartidas recorren archivos importados del proyecto; pueden incluir funciones que ese notebook no ejecuta. La ejecución offline exige coincidencia del hash del source. Los nombres de proveedor/framework son configuración declarada, no evidencia live.

[JSON completo](notebook_inventory_213.json) · [Llamadas, métodos y parámetros usados](notebook_parameters_213.csv) · [Informe de cierre](../revisions/2.1.3/closeout-evidence/REPORT.md)

## Tutorials vigentes

| Notebook | Gramática directa | Observada en RunResult | Referencias en módulos importados (no equivale a enseñanza) | Providers/frameworks declarados | Estado |
|---|---|---|---|---|---|
| [tutorials/00_api.ipynb](../tutorials/00_api.ipynb) | Action, Agent, RunResult | Action, Agent, RunResult | — | Dinámico/no declarado | Offline: pasa |
| [tutorials/01_tools_skills.ipynb](../tutorials/01_tools_skills.ipynb) | Action, Agent, RunResult, load_skill, skill, tool | Action, Agent, RunResult, skill, tool | Action, Agent, Environment, Eval, Graph, Parallel, RunResult, Sequence, System, __version__, framework, load_skill, model_artifact, model_server, runtime, skill, tool | Dinámico/no declarado | Offline: pasa |
| [tutorials/02_agent_flows.ipynb](../tutorials/02_agent_flows.ipynb) | Action, Agent, Graph, Parallel, RunResult, Sequence, skill, tool | Action, Agent, Graph, Parallel, RunResult, Sequence, skill, tool | — | langgraph, native | Offline: pasa |
| [tutorials/03_system_flows.ipynb](../tutorials/03_system_flows.ipynb) | Action, Agent, Graph, Parallel, RunResult, Sequence, System, skill, tool | Action, Agent, Graph, Parallel, RunResult, Sequence, System, skill, tool | — | langgraph, native | Offline: pasa |
| [tutorials/04_environment.ipynb](../tutorials/04_environment.ipynb) | Action, Agent, Environment, RunResult, Sequence, System, skill, tool | Action, Agent, Environment, RunResult, Sequence, System, skill, tool | Action, Agent, Environment, Eval, Graph, Parallel, RunResult, Sequence, System, __version__, framework, model_artifact, model_server, runtime, skill, tool | Dinámico/no declarado | Offline: pasa |
| [tutorials/05_eval.ipynb](../tutorials/05_eval.ipynb) | Action, Agent, Eval, RunResult, Sequence, skill, tool | Action, Agent, Environment, Eval, RunResult, Sequence, skill, tool | Action, Agent, Environment, Eval, Graph, Parallel, RunResult, Sequence, System, __version__, framework, model_artifact, model_server, runtime, skill, tool | Dinámico/no declarado | Offline: pasa |
| [tutorials/06_runtime_framework.ipynb](../tutorials/06_runtime_framework.ipynb) | Action, Agent, RunResult, framework, runtime, skill, tool | Agent, RunResult, framework, runtime, skill, tool | — | bedrock-runtime, ollama-runtime, openai-runtime, python-runtime, vllm-runtime, langgraph, native, openai-agents, strands | Offline: pasa |
| [tutorials/07_results_limits.ipynb](../tutorials/07_results_limits.ipynb) | Action, Agent, Limits, RunResult, Sequence, skill, tool | Action, Agent, RunResult, Sequence, skill, tool | — | Dinámico/no declarado | Offline: pasa |
| [tutorials/08_model_serving.ipynb](../tutorials/08_model_serving.ipynb) | model_artifact, model_server | Sin ejecución de unidades observada | Action, Agent, Environment, Eval, Graph, Parallel, RunResult, Sequence, System, __version__, framework, model_artifact, model_server, runtime, skill, tool | Dinámico/no declarado | Offline: pasa |
| [tutorials/09_order_challenge.ipynb](../tutorials/09_order_challenge.ipynb) | Sin llamadas directas al SDK | Action, Agent, Environment, Eval, Graph, Parallel, RunResult, Sequence, System, skill, tool | Action, Agent, Environment, Eval, Graph, Parallel, RunResult, Sequence, System, __version__, framework, model_artifact, model_server, runtime, skill, tool | langgraph, native | Offline: pasa |
| [tutorials/10_contracts_judges.ipynb](../tutorials/10_contracts_judges.ipynb) | Sin llamadas directas al SDK | Action, Agent, Environment, Eval, RunResult, framework, runtime, skill, tool | Action, Agent, Environment, Eval, Graph, Parallel, RunResult, Sequence, System, __version__, framework, model_artifact, model_server, runtime, skill, tool | Dinámico/no declarado | Offline: pasa |

## Examples vigentes

| Notebook | Gramática directa | Observada en RunResult | Referencias en módulos importados (no equivale a enseñanza) | Providers/frameworks declarados | Estado |
|---|---|---|---|---|---|
| [examples/agentic_systems_studio/notebooks/01_studio.ipynb](../examples/agentic_systems_studio/notebooks/01_studio.ipynb) | Sin llamadas directas al SDK | Action, Agent, RunResult, Sequence, System, framework, runtime, skill, tool | Action, Agent, Limits, RunResult, Sequence, System, __version__, framework, runtime, skill, tool | Dinámico/no declarado | Offline: pasa |
| [examples/api_walkthrough/01_api_user_guide.ipynb](../examples/api_walkthrough/01_api_user_guide.ipynb) | Action, Agent, Environment, Eval, Graph, Limits, Parallel, RunResult, Sequence, System, __version__, framework, load_skill, model_artifact, model_server, runtime, skill, tool | Action, Agent, Environment, Eval, Graph, Parallel, RunResult, Sequence, System, framework, runtime, skill, tool | — | openai-runtime, python-runtime, langgraph, native, openai-agents | Offline: pasa |

## Históricos y generados anteriores

| Notebook | Gramática directa | Observada en RunResult | Referencias en módulos importados (no equivale a enseñanza) | Providers/frameworks declarados | Estado |
|---|---|---|---|---|---|
| [examples/history/2.1.2/studio/notebooks/00_conversational_system.ipynb](../examples/history/2.1.2/studio/notebooks/00_conversational_system.ipynb) | Sin llamadas directas al SDK; anteriores: human_result, show_json | Sin ejecución de unidades observada | Action, Agent, Limits, RunResult, Sequence, System, __version__, framework, runtime, skill, tool | Dinámico/no declarado | Historia; no reejecutado |
| [examples/history/2.1.2/studio/notebooks/01_launch_studio.ipynb](../examples/history/2.1.2/studio/notebooks/01_launch_studio.ipynb) | Sin llamadas directas al SDK | Sin ejecución de unidades observada | Action, Agent, Limits, RunResult, Sequence, System, __version__, framework, runtime, skill, tool | Dinámico/no declarado | Historia; no reejecutado |
| [examples/history/2.1.2/studio-generated-original/creator-proof/notebooks/00_walkthrough.ipynb](../examples/history/2.1.2/studio-generated-original/creator-proof/notebooks/00_walkthrough.ipynb) | Sin llamadas directas al SDK | Sin ejecución de unidades observada | — | Dinámico/no declarado | Historia; no reejecutado |
| [examples/history/2.1.2/studio-generated-original/incident_response_application/notebooks/00_walkthrough.ipynb](../examples/history/2.1.2/studio-generated-original/incident_response_application/notebooks/00_walkthrough.ipynb) | Sin llamadas directas al SDK | Sin ejecución de unidades observada | — | Dinámico/no declarado | Historia; no reejecutado |
| [examples/history/2.1.2/studio-notebooks-original/00_conversational_system.ipynb](../examples/history/2.1.2/studio-notebooks-original/00_conversational_system.ipynb) | Sin llamadas directas al SDK; anteriores: human_result, show_json | Sin ejecución de unidades observada | Action, Agent, Limits, RunResult, Sequence, System, __version__, framework, runtime, skill, tool | Dinámico/no declarado | Historia; no reejecutado |
| [examples/history/2.1.2/studio-notebooks-original/01_launch_studio.ipynb](../examples/history/2.1.2/studio-notebooks-original/01_launch_studio.ipynb) | Sin llamadas directas al SDK | Sin ejecución de unidades observada | Action, Agent, Limits, RunResult, Sequence, System, __version__, framework, runtime, skill, tool | Dinámico/no declarado | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/api/14_api_contract_matrix.ipynb](../examples/history/2.1.2/tutorials/api/14_api_contract_matrix.ipynb) | Sin llamadas directas al SDK; anteriores: api_contract, exercise_api, show | Sin ejecución de unidades observada | — | Dinámico/no declarado | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/core/00_runtime_scheduler.ipynb](../examples/history/2.1.2/tutorials/core/00_runtime_scheduler.ipynb) | RunResult, runtime, tool; anteriores: __all__, human_result, run_result_output, scheduler, show_json, system | Sin ejecución de unidades observada | — | python-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/core/01_tool.ipynb](../examples/history/2.1.2/tutorials/core/01_tool.ipynb) | __version__, tool; anteriores: AgentContract, ContractPolicySpec, RunPolicy, Tool, __all__, human_result, show_json | Sin ejecución de unidades observada | — | Dinámico/no declarado | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/core/02_skills.ipynb](../examples/history/2.1.2/tutorials/core/02_skills.ipynb) | __version__, load_skill, runtime, skill, tool; anteriores: AgentContract, RunPolicy, Skill, __all__, agent, human_result, show_json | Sin ejecución de unidades observada | — | python-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/core/03_agent.ipynb](../examples/history/2.1.2/tutorials/core/03_agent.ipynb) | runtime, tool; anteriores: AgentContract, ContractPolicySpec, RunPolicy, __all__, agent, agent_output, human_result, scheduler, show_json | Sin ejecución de unidades observada | — | python-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/core/04_results_lineage.ipynb](../examples/history/2.1.2/tutorials/core/04_results_lineage.ipynb) | __version__, runtime, tool; anteriores: AgentContract, RunPolicy, __all__, agent_output, compose_result, human_result, run_result_output, run_result_summary, run_result_view, show, show_json, system | Sin ejecución de unidades observada | — | python-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/core/05_system.ipynb](../examples/history/2.1.2/tutorials/core/05_system.ipynb) | __version__, runtime, skill; anteriores: AgentContract, ToolSet, __all__, human_result, show, show_json, system, toolset | Sin ejecución de unidades observada | — | python-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/core/06_graph_native.ipynb](../examples/history/2.1.2/tutorials/core/06_graph_native.ipynb) | __version__, runtime, tool; anteriores: __all__, agent_node, agent_output, compose_result, graph, human_result, show, show_json, system | Sin ejecución de unidades observada | — | python-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/core/07_environment_eval.ipynb](../examples/history/2.1.2/tutorials/core/07_environment_eval.ipynb) | __version__, runtime, tool; anteriores: AgentContract, RunPolicy, __all__, agent_output, build_agent_step_graph, environment, environment_summary, eval, eval_report_summary, human_result, show, show_json, system | Sin ejecución de unidades observada | — | python-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/core/08_single_agentic_system.ipynb](../examples/history/2.1.2/tutorials/core/08_single_agentic_system.ipynb) | runtime, tool; anteriores: AgentContract, RunPolicy, __all__, eval, eval_report_summary, human_result, show_json, system | Sin ejecución de unidades observada | — | python-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/core/09_multi_agentic_system.ipynb](../examples/history/2.1.2/tutorials/core/09_multi_agentic_system.ipynb) | runtime, tool; anteriores: AgentContract, SequentialPlan, __all__, agent_output, human_result, show_json, system | Sin ejecución de unidades observada | — | python-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/core/10_multi_agent_graph.ipynb](../examples/history/2.1.2/tutorials/core/10_multi_agent_graph.ipynb) | runtime, tool; anteriores: __all__, agent_node, agent_output, compose_result, graph, human_result, show_json, system | Sin ejecución de unidades observada | — | python-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/frameworks/00_langgraph.ipynb](../examples/history/2.1.2/tutorials/frameworks/00_langgraph.ipynb) | framework, runtime, tool; anteriores: AgentContract, RunPolicy, __all__, agent, graph, human_result, integrations, show, show_json | Sin ejecución de unidades observada | — | python-runtime, langgraph | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/frameworks/01_openai_agents.ipynb](../examples/history/2.1.2/tutorials/frameworks/01_openai_agents.ipynb) | framework, runtime, tool; anteriores: AgentContract, RunPolicy, __all__, agent, dependency_target, human_result, integrations, show_json | Sin ejecución de unidades observada | — | python-runtime, openai-agents | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/frameworks/02_aws_strands.ipynb](../examples/history/2.1.2/tutorials/frameworks/02_aws_strands.ipynb) | framework, runtime, tool; anteriores: AgentContract, RunPolicy, __all__, agent, human_result, integrations, run_result_output, show_json | Sin ejecución de unidades observada | — | python-runtime, strands | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/frameworks/03_provider_framework_matrix.ipynb](../examples/history/2.1.2/tutorials/frameworks/03_provider_framework_matrix.ipynb) | RunResult, framework, runtime, tool; anteriores: compatibility_matrix, compatibility_report, human_result, show, system | Sin ejecución de unidades observada | — | python-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/providers/00_auto.ipynb](../examples/history/2.1.2/tutorials/providers/00_auto.ipynb) | runtime; anteriores: providers, scheduler, show_json | Sin ejecución de unidades observada | — | Dinámico/no declarado | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/providers/01_openai.ipynb](../examples/history/2.1.2/tutorials/providers/01_openai.ipynb) | RunResult, __version__, runtime, tool; anteriores: AgentContract, RunPolicy, __all__, __name__, human_result, openai_environment_snapshot, run_result_output, scheduler, show_json, system | Sin ejecución de unidades observada | — | openai-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/providers/02_bedrock.ipynb](../examples/history/2.1.2/tutorials/providers/02_bedrock.ipynb) | RunResult, __version__, runtime, tool; anteriores: AgentContract, RunPolicy, __all__, __name__, aws_environment_snapshot, boto3_session_snapshot, human_result, run_result_output, scheduler, show_json, system | Sin ejecución de unidades observada | — | bedrock-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/providers/03_vllm.ipynb](../examples/history/2.1.2/tutorials/providers/03_vllm.ipynb) | RunResult, model_artifact, model_server, runtime, tool; anteriores: AgentContract, RunPolicy, human_result, run_result_output, show_json, system, vllm_environment_snapshot | Sin ejecución de unidades observada | — | vllm-runtime | Historia; no reejecutado |
| [examples/history/2.1.2/tutorials/providers/04_ollama.ipynb](../examples/history/2.1.2/tutorials/providers/04_ollama.ipynb) | RunResult, __version__, runtime, tool; anteriores: AgentContract, RunPolicy, __all__, __name__, human_result, ollama_environment_snapshot, run_result_output, scheduler, show_json, system | Sin ejecución de unidades observada | — | ollama-runtime | Historia; no reejecutado |
| [examples/history/prototype-213/00_walkthrough.ipynb](../examples/history/prototype-213/00_walkthrough.ipynb) | RunResult, __version__, skill, tool; anteriores: __all__, __file__ | Sin ejecución de unidades observada | — | langgraph, native | Historia; no reejecutado |
| [examples/history/prototype-213/evidence/executed-walkthrough.ipynb](../examples/history/prototype-213/evidence/executed-walkthrough.ipynb) | RunResult, __version__, skill, tool; anteriores: __all__, __file__ | Sin ejecución de unidades observada | — | langgraph, native | Historia; no reejecutado |

## Cobertura por palabra de la API

| Elemento | Notebooks con referencia directa | Con referencia en archivos compartidos |
|---|---:|---:|
| `tool` | 8 | 7 |
| `skill` | 8 | 7 |
| `load_skill` | 2 | 1 |
| `Action` | 9 | 7 |
| `Agent` | 9 | 7 |
| `System` | 3 | 7 |
| `Sequence` | 6 | 7 |
| `Parallel` | 3 | 6 |
| `Graph` | 3 | 6 |
| `Environment` | 2 | 6 |
| `Eval` | 2 | 6 |
| `Limits` | 2 | 1 |
| `RunResult` | 9 | 7 |
| `runtime` | 2 | 7 |
| `framework` | 2 | 7 |
| `model_artifact` | 2 | 6 |
| `model_server` | 2 | 6 |
| `__version__` | 1 | 7 |

El JSON conserva la lista inversa por elemento, miembros, keywords por llamada, aliases, errores de parseo, hashes y módulos compartidos. El CSV permite filtrar cada método y parámetro usado. Esta cobertura no implica enseñar cada valor posible de los parámetros.

## Límites y pendientes

- Dynamic getattr, generated code, runtime dispatch and environment values may not be statically resolved.
- Literal provider/framework strings indicate declared configuration or mentions, not successful inference.
- Stored outputs in historical notebooks are not a new acceptance attestation.
- Current code uses toolkit; historical notebook imports and outputs are preserved.

vLLM/Colab, AWS IAM y ADA IAM mantienen la validación en su entorno como pendiente. OpenAI, Ollama y Bedrock API key se contrastan con los cuatro frameworks en la campaña externa. El notebook de usuario permanece seguro de ejecutar offline.
