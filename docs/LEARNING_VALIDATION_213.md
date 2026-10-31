> **Histórico: no es la guía de la API 2.1.4.dev3.** Conserva propuestas/resultados de su versión original. Para implementar, usa [la API vigente](API_214.md).

# Validación de tutorials y examples · 2.1.3

Campaña independiente, posterior al release. Se usa el wheel **publicado 2.1.3** instalado sin modo editable. La documentación y las fuentes didácticas pueden mejorar; no se reemplazan los artefactos publicados ni la evidencia original.

**Wheel SHA-256:** `b09785bc75faa97d15b4cf4c1fc25b18741319ce1b8024641c9597930115b283`.

Examples: **49/49** programas offline. Notebooks: **21/21** con sus secciones offline verificadas. Las celdas omitidas se indican por notebook. Rutas live de notebooks: **12/12**.

Presupuesto autorizado: USD 10 y 300 llamadas. Registradas **192 llamadas** y **USD 7.965028 reservados**. Las reservas son cotas conservadoras, no facturación. Se incluyen fallos, reintentos y Ollama; no se descuenta ningún intento.

[RunResult y Lineage Memory por unidad](RUNRESULTS_LINEAGE_213.md) · [Inventario de gramática](NOTEBOOK_INVENTORY_213.md) · [Evidencia original publicada](../revisions/2.1.3/closeout-evidence/REPORT.md)

## Modelos y endpoints

| Provider | Modelo | Endpoint |
|---|---|---|
| openai-runtime | `gpt-4.1-mini` | `https://api.openai.com/v1` |
| ollama-runtime | `gemma4:31b-cloud` | `https://ollama.com/v1` |
| bedrock-runtime | `qwen.qwen3-32b-v1:0` | `https://bedrock-runtime.us-east-2.amazonaws.com` |

Python Runtime es el control determinista. Bedrock usa bearer/API key; no se infiere validación IAM de este resultado.

## Notebooks vigentes

| Notebook | Offline | Live / servicio local / interfaz | Evidencia |
|---|---|---|---|
| [examples/agentic_systems_studio/notebooks/01_studio.ipynb](../examples/agentic_systems_studio/notebooks/01_studio.ipynb) | Pasa; 1 celdas de otro perfil omitidas | Servicios/UI: pasa | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T045931211639/00-01_studio.ipynb) |
| [examples/api_walkthrough/01_api_user_guide.ipynb](../examples/api_walkthrough/01_api_user_guide.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/01-01_api_user_guide.ipynb) |
| [tutorials/api/01_runtime_framework.ipynb](../tutorials/api/01_runtime_framework.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/02-01_runtime_framework.ipynb) |
| [tutorials/api/02_contracts_judges.ipynb](../tutorials/api/02_contracts_judges.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/03-02_contracts_judges.ipynb) |
| [tutorials/core/00_start.ipynb](../tutorials/core/00_start.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/04-00_start.ipynb) |
| [tutorials/core/01_tools_skills.ipynb](../tutorials/core/01_tools_skills.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/05-01_tools_skills.ipynb) |
| [tutorials/core/02_agent_flows.ipynb](../tutorials/core/02_agent_flows.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/06-02_agent_flows.ipynb) |
| [tutorials/core/03_system_flows.ipynb](../tutorials/core/03_system_flows.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/07-03_system_flows.ipynb) |
| [tutorials/core/04_environment.ipynb](../tutorials/core/04_environment.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/08-04_environment.ipynb) |
| [tutorials/core/05_eval.ipynb](../tutorials/core/05_eval.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/09-05_eval.ipynb) |
| [tutorials/core/06_results_limits.ipynb](../tutorials/core/06_results_limits.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/10-06_results_limits.ipynb) |
| [tutorials/core/07_order_challenge.ipynb](../tutorials/core/07_order_challenge.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T050537279678/00-07_order_challenge.ipynb) |
| [tutorials/frameworks/01_langgraph.ipynb](../tutorials/frameworks/01_langgraph.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/12-01_langgraph.ipynb) |
| [tutorials/frameworks/02_openai_agents.ipynb](../tutorials/frameworks/02_openai_agents.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/13-02_openai_agents.ipynb) |
| [tutorials/frameworks/03_strands.ipynb](../tutorials/frameworks/03_strands.ipynb) | Pasa; 1 celdas de otro perfil omitidas | Servicios/UI: pasa | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/14-03_strands.ipynb) |
| [tutorials/frameworks/04_interoperability.ipynb](../tutorials/frameworks/04_interoperability.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T045158828527/00-04_interoperability.ipynb) |
| [tutorials/providers/00_python.ipynb](../tutorials/providers/00_python.ipynb) | Pasa | Sin inferencia; alcance del notebook | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/16-00_python.ipynb) |
| [tutorials/providers/01_openai.ipynb](../tutorials/providers/01_openai.ipynb) | Pasa; 2 celdas de otro perfil omitidas | 4/4 frameworks live | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/17-01_openai.ipynb) |
| [tutorials/providers/02_ollama.ipynb](../tutorials/providers/02_ollama.ipynb) | Pasa; 2 celdas de otro perfil omitidas | 4/4 frameworks live | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/18-02_ollama.ipynb) |
| [tutorials/providers/03_bedrock.ipynb](../tutorials/providers/03_bedrock.ipynb) | Pasa; 2 celdas de otro perfil omitidas | 4/4 frameworks live | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/19-03_bedrock.ipynb) |
| [tutorials/providers/04_vllm_serving.ipynb](../tutorials/providers/04_vllm_serving.ipynb) | Pasa | No requiere inferencia; configuración GPU pendiente | [Copia ejecutada](../revisions/2.1.3/learning-evidence-elevated/executed-notebooks/20261023T044738543256/20-04_vllm_serving.ipynb) |

## Proveedores × frameworks: ejecución de las celdas originales

| Provider notebook | native | LangGraph | OpenAI Agents | Strands |
|---|---|---|---|---|
| 01_openai | Pasa | Pasa | Pasa | Pasa |
| 02_ollama | Pasa | Pasa | Pasa | Pasa |
| 03_bedrock | Pasa | Pasa | Pasa | Pasa |

Input: pedir `certify(37)`. Proceso: el modelo debe invocar la Tool con el entero exacto; se exigen eventos reales, invariantes y RunResult serializable. Output: evidencia de certify y lineage. El arnés solo parametriza el framework en una copia de validación; no sustituye modelo, proveedor, actor ni respuesta.

## Aplicaciones y capacidades específicas

| Grupo | Pasan / planificados | Input → proceso → output |
|---|---:|---|
| [features](../revisions/2.1.3/learning-evidence-elevated/features.json) | 15/15 | Transferencia a especialista y petición bloqueada → handoff/guardrail/sesión; MCP/A2A locales → evidencia remota; checkpoint → pausa/reanudación; cuatro actores → recorrido exacto. |
| [integrated](../revisions/2.1.3/learning-evidence-elevated/integrated.json) | 16/16 | Pedidos de 200 y 1500 → cotización, decisión y Tool approve/review, Environment y Eval sobre la ejecución observada → approved/manual_review y memoria approved=1. |
| [studio](../revisions/2.1.3/learning-evidence-elevated/studio.json) | 16/16 | Proyecto LINTERNA y cálculo 17×19 → tres turnos con historial y calculadora → nombre conservado y 323. |
| [studio-ui](../revisions/2.1.3/learning-evidence-elevated/studio-ui.json) | 12/12 | Seleccionar provider/framework y enviar 17×19 en widgets reales → chat y Tool safe_calculate → 323 y RunResult correcto. |

Los grupos incluyen controles Python sin inferencia. Son escenarios definidos, no una garantía sobre cualquier conversación o modelo. El juez fixture valida el protocolo y los oráculos exactos comprueban aritmética, herramientas y memoria; esta campaña no declara un benchmark semántico general.

## Cada example ejecutable

| Fuente | Resultado | Input → proceso → output y RunResult/lineage |
|---|---|---|
| [examples/agent_contracts](../examples/agent_contracts/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/agent_contracts/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/agent_contracts/runresults.json) |
| [examples/api_walkthrough](../examples/api_walkthrough/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/api_walkthrough/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/api_walkthrough/runresults.json) |
| [examples/applications/agentic_systems_creator](../examples/applications/agentic_systems_creator/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/agentic_systems_creator/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/agentic_systems_creator/runresults.json) |
| [examples/applications/code_review](../examples/applications/code_review/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/code_review/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/code_review/runresults.json) |
| [examples/applications/customer_support](../examples/applications/customer_support/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/customer_support/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/customer_support/runresults.json) |
| [examples/applications/data_quality](../examples/applications/data_quality/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/data_quality/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/data_quality/runresults.json) |
| [examples/applications/decision_intelligence](../examples/applications/decision_intelligence/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/decision_intelligence/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/decision_intelligence/runresults.json) |
| [examples/applications/incident_response](../examples/applications/incident_response/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/incident_response/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/incident_response/runresults.json) |
| [examples/applications/meeting_action_center](../examples/applications/meeting_action_center/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/meeting_action_center/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/meeting_action_center/runresults.json) |
| [examples/applications/prompt_security](../examples/applications/prompt_security/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/prompt_security/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/prompt_security/runresults.json) |
| [examples/applications/quantitative_analysis](../examples/applications/quantitative_analysis/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/quantitative_analysis/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/quantitative_analysis/runresults.json) |
| [examples/applications/refund_resolution](../examples/applications/refund_resolution/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/refund_resolution/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/refund_resolution/runresults.json) |
| [examples/applications/research_synthesis](../examples/applications/research_synthesis/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/research_synthesis/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/research_synthesis/runresults.json) |
| [examples/applications/retired_accountability_otc](../examples/applications/retired_accountability_otc/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/retired_accountability_otc/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/retired_accountability_otc/runresults.json) |
| [examples/applications/unified_grammar](../examples/applications/unified_grammar/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/unified_grammar/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/applications/unified_grammar/runresults.json) |
| [examples/episode_memory](../examples/episode_memory/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/episode_memory/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/episode_memory/runresults.json) |
| [examples/evaluation_checks](../examples/evaluation_checks/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/evaluation_checks/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/evaluation_checks/runresults.json) |
| [examples/execution_lifecycle](../examples/execution_lifecycle/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/execution_lifecycle/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/execution_lifecycle/runresults.json) |
| [examples/flow_semantics](../examples/flow_semantics/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/flow_semantics/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/flow_semantics/runresults.json) |
| [examples/framework_interop](../examples/framework_interop/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/framework_interop/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/framework_interop/runresults.json) |
| [examples/grammar_tour](../examples/grammar_tour/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/grammar_tour/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/grammar_tour/runresults.json) |
| [examples/model_serving](../examples/model_serving/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/model_serving/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/model_serving/runresults.json) |
| [examples/order_fulfillment](../examples/order_fulfillment/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/order_fulfillment/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/order_fulfillment/runresults.json) |
| [examples/package_install](../examples/package_install/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/package_install/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/package_install/runresults.json) |
| [examples/patterns/bounded_conversation](../examples/patterns/bounded_conversation/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/bounded_conversation/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/bounded_conversation/runresults.json) |
| [examples/patterns/claim_review](../examples/patterns/claim_review/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/claim_review/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/claim_review/runresults.json) |
| [examples/patterns/compact_evaluation](../examples/patterns/compact_evaluation/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/compact_evaluation/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/compact_evaluation/runresults.json) |
| [examples/patterns/controlled_failure](../examples/patterns/controlled_failure/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/controlled_failure/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/controlled_failure/runresults.json) |
| [examples/patterns/evidence_grounded_poem](../examples/patterns/evidence_grounded_poem/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/evidence_grounded_poem/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/evidence_grounded_poem/runresults.json) |
| [examples/patterns/fixed_judge_pilot](../examples/patterns/fixed_judge_pilot/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/fixed_judge_pilot/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/fixed_judge_pilot/runresults.json) |
| [examples/patterns/judge_calibration](../examples/patterns/judge_calibration/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/judge_calibration/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/judge_calibration/runresults.json) |
| [examples/patterns/long_environment](../examples/patterns/long_environment/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/long_environment/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/long_environment/runresults.json) |
| [examples/patterns/saved_execution_eval](../examples/patterns/saved_execution_eval/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/saved_execution_eval/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/saved_execution_eval/runresults.json) |
| [examples/patterns/scope_clarification](../examples/patterns/scope_clarification/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/scope_clarification/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/scope_clarification/runresults.json) |
| [examples/patterns/semantic_calculation](../examples/patterns/semantic_calculation/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/semantic_calculation/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/semantic_calculation/runresults.json) |
| [examples/patterns/strands_protocol_graph](../examples/patterns/strands_protocol_graph/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/strands_protocol_graph/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/strands_protocol_graph/runresults.json) |
| [examples/patterns/text_analysis](../examples/patterns/text_analysis/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/text_analysis/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/text_analysis/runresults.json) |
| [examples/patterns/two_phase_poem](../examples/patterns/two_phase_poem/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/two_phase_poem/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/two_phase_poem/runresults.json) |
| [examples/patterns/typed_claim_review](../examples/patterns/typed_claim_review/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/typed_claim_review/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/typed_claim_review/runresults.json) |
| [examples/patterns/unambiguous_lm_gate](../examples/patterns/unambiguous_lm_gate/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/unambiguous_lm_gate/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/patterns/unambiguous_lm_gate/runresults.json) |
| [examples/portable_skills](../examples/portable_skills/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/portable_skills/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/portable_skills/runresults.json) |
| [examples/provider_framework_conformance](../examples/provider_framework_conformance/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/provider_framework_conformance/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/provider_framework_conformance/runresults.json) |
| [examples/results_lineage](../examples/results_lineage/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/results_lineage/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/results_lineage/runresults.json) |
| [examples/tool_contracts](../examples/tool_contracts/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/tool_contracts/run.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/tool_contracts/runresults.json) |
| [examples/validation/ada_iam](../examples/validation/ada_iam/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/validation/ada_iam/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/validation/ada_iam/runresults.json) |
| [examples/validation/api_contract_lab](../examples/validation/api_contract_lab/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/validation/api_contract_lab/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/validation/api_contract_lab/runresults.json) |
| [examples/validation/aws_iam](../examples/validation/aws_iam/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/validation/aws_iam/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/validation/aws_iam/runresults.json) |
| [examples/validation/provider_framework_conformance](../examples/validation/provider_framework_conformance/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/validation/provider_framework_conformance/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/validation/provider_framework_conformance/runresults.json) |
| [examples/validation/vllm_colab](../examples/validation/vllm_colab/example.py) | Pasa offline | [Informe completo](../revisions/2.1.3/learning-evidence-elevated/example-results/validation/vllm_colab/current.json) · [RunResult/lineage](../revisions/2.1.3/learning-evidence-elevated/example-results/validation/vllm_colab/runresults.json) |

Los 34 experimentos anteriores se ejecutaron como adaptaciones actuales. Los casos con entradas suministradas, respuestas guardadas o jueces fixture conservan ese alcance; ejecutar su código no transforma esa evidencia en generación live. Los fallos controlados forman parte de los contratos esperados.

## Checks adicionales

| Suite | Tests | Fallos / errores |
|---|---:|---:|
| [tests.xml](../revisions/2.1.3/learning-evidence-elevated/tests.xml) | 180 | 0 |
| [studio-tests.xml](../revisions/2.1.3/learning-evidence-elevated/studio-tests.xml) | 14 | 0 |
| [integrity-tests.xml](../revisions/2.1.3/learning-evidence-elevated/integrity-tests.xml) | 13 | 0 |
| [business-tests.xml](../revisions/2.1.3/learning-evidence-elevated/business-tests.xml) | 2 | 0 |
| [learning-tests.xml](../revisions/2.1.3/learning-evidence-elevated/learning-tests.xml) | 17 | 0 |

## Incidencias y correcciones didácticas

- La primera ejecución restringida no pudo completar kernels/subprocesos y protocolos locales. Se repitió con acceso al transporte local; no hubo inferencia en ese intento.
- Se corrigió el orden de una celda de Skills al retirar un import auxiliar. Se conserva la copia fallida.
- Las variables existentes usan también *_MODEL: los notebooks aceptan *_MODEL_ID o *_MODEL para el mismo modelo explícito. Los intentos previos fallaron antes del transporte y consumieron cero llamadas.
- El recorrido con cuatro SDKs declara 180 s para incluir su preparación en un kernel frío; se conserva el intento que agotó el plazo de 10 s.
- La captura distingue el ejemplo canónico y la adaptación con el mismo nombre en directorios separados. No se atribuye la evidencia de uno al otro.

- La comprobación estática de nombres detectó una referencia de runtime que no pertenecía al challenge offline. Se retiró esa opción incompleta y se reejecutó la lección; no cambió el SDK.
- Un intento del arnés local encontró un directorio temporal bloqueado por Windows después de completar MCP/A2A. El arnés conserva ahora sus directorios de trabajo; se verificaron apertura y cierre de Studio. Los errores de fixtures restringidos también se conservaron antes de repetirlos en un directorio permitido.

## Límites y procedencia

- vLLM/Colab GPU, AWS IAM y ADA IAM: ejecución en su entorno pendiente. Sus ejemplos solo validan configuración y contratos offline.
- No se modificó el código del SDK o Studio publicado. No se creó otra versión, tag ni publicación.
- La copia original de la documentación y notebooks aprobados se conserva en published-learning-source.zip y se verifica contra el manifiesto original. La aceptación de este material usa hashes actuales separados.
- Los intentos y las copias ejecutadas permanecen en los directorios de evidencia; no se borra un fallo para mostrar solo el intento posterior.

Generado: 2026-10-23T05:06:43.503400+00:00.
