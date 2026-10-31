# Examples: evidencia offline por archivo · 2.1.4.dev7

57 entrypoints correctos y 7 notebooks con perfil offline correcto. Cada hash de código coincide con la evidencia. Cero inferencia.

MCP/A2A no se repitió: requiere su perfil local separado. Studio conserva una celda local omitida. No se validaron proveedores online ni todos los controles UI.

## Entrypoints

| Archivo | Estado |
|---|---|
| examples/agent_contracts/example.py | offline-passed |
| examples/agentic_systems_studio/example.py | offline-passed |
| examples/api_walkthrough/example.py | offline-passed |
| examples/applications/agentic_systems_creator/example.py | offline-passed |
| examples/applications/code_review/example.py | offline-passed |
| examples/applications/customer_support/example.py | offline-passed |
| examples/applications/data_quality/example.py | offline-passed |
| examples/applications/decision_intelligence/example.py | offline-passed |
| examples/applications/financial_harness/example.py | offline-passed |
| examples/applications/incident_response/example.py | offline-passed |
| examples/applications/meeting_action_center/example.py | offline-passed |
| examples/applications/prompt_security/example.py | offline-passed |
| examples/applications/quantitative_analysis/example.py | offline-passed |
| examples/applications/refund_resolution/example.py | offline-passed |
| examples/applications/research_synthesis/example.py | offline-passed |
| examples/applications/retired_accountability_otc/example.py | offline-passed |
| examples/applications/unified_grammar/example.py | offline-passed |
| examples/checked_composition/example.py | offline-passed |
| examples/episode_memory/example.py | offline-passed |
| examples/evaluation_checks/example.py | offline-passed |
| examples/execution_controls/example.py | offline-passed |
| examples/execution_lifecycle/example.py | offline-passed |
| examples/flow_semantics/example.py | offline-passed |
| examples/framework_interop/example.py | offline-passed |
| examples/grammar_tour/example.py | offline-passed |
| examples/lineage_memory/example.py | offline-passed |
| examples/model_serving/example.py | offline-passed |
| examples/order_fulfillment/example.py | offline-passed |
| examples/package_install/example.py | offline-passed |
| examples/patterns/bounded_conversation/example.py | offline-passed |
| examples/patterns/claim_review/example.py | offline-passed |
| examples/patterns/compact_evaluation/example.py | offline-passed |
| examples/patterns/controlled_failure/example.py | offline-passed |
| examples/patterns/evidence_grounded_poem/example.py | offline-passed |
| examples/patterns/fixed_judge_pilot/example.py | offline-passed |
| examples/patterns/judge_calibration/example.py | offline-passed |
| examples/patterns/long_environment/example.py | offline-passed |
| examples/patterns/saved_execution_eval/example.py | offline-passed |
| examples/patterns/scope_clarification/example.py | offline-passed |
| examples/patterns/semantic_calculation/example.py | offline-passed |
| examples/patterns/strands_protocol_graph/example.py | separate-local-protocol-profile |
| examples/patterns/text_analysis/example.py | offline-passed |
| examples/patterns/two_phase_poem/example.py | offline-passed |
| examples/patterns/typed_claim_review/example.py | offline-passed |
| examples/patterns/unambiguous_lm_gate/example.py | offline-passed |
| examples/portable_skills/example.py | offline-passed |
| examples/provider_framework_conformance/example.py | offline-passed |
| examples/results_lineage/example.py | offline-passed |
| examples/tool_contracts/example.py | offline-passed |
| examples/unified_grammar/example.py | offline-passed |
| examples/validation/ada_iam/example.py | offline-passed |
| examples/validation/api_contract_lab/example.py | offline-passed |
| examples/validation/aws_iam/example.py | offline-passed |
| examples/validation/provider_framework_conformance/example.py | offline-passed |
| examples/validation/vllm_colab/example.py | offline-passed |
| examples/common_graph/application.py | offline-passed |
| examples/api_214/application.py | offline-passed |
| examples/context_memory_lineage/application.py | offline-passed |

## Notebooks

| Archivo | Celdas ejecutadas | Omitidas |
|---|---:|---:|
| examples/agentic_systems_studio/notebooks/01_studio.ipynb | 8 | 1 |
| examples/api_214/01_api.ipynb | 6 | 0 |
| examples/api_walkthrough/01_api_user_guide.ipynb | 7 | 0 |
| examples/checked_composition/01_checked_composition.ipynb | 5 | 0 |
| examples/common_graph/01_common_graph.ipynb | 16 | 0 |
| examples/context_memory_lineage/01_context_memory_lineage.ipynb | 9 | 0 |
| examples/lineage_memory/01_lineage_memory_decisions.ipynb | 18 | 0 |

## Alcance de la revisión estática

inventory.json enumera cada .py, .md e .ipynb activo, su hash, atributos públicos, importaciones entre ejemplos y errores de sintaxis. Excluye history/evidence/build/dist/cachés. Los archivos de infraestructura y tests de Studio se inspeccionan estáticamente; eso no implica ejecutarlos todos.

before/ conserva los textos previos a las correcciones editoriales. Las pasadas 01/02/03 permanecen separadas. El código del SDK y el wheel no se modificaron.
