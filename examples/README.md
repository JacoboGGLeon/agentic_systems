# Examples

Ejemplos de la API única **2.1.3**. Elige una tarea, importa `run` y observa el resultado.

```python
from examples.applications.research_synthesis.example import run

result = run()
result.data
```

El resultado también conserva evidencia de su ejecución:

```python
result.ok
result.lineage(name="research").to_dict()
```

Empieza por [los seis flujos](grammar_tour/README.md), continúa con [pedidos](order_fulfillment/README.md) y abre [Studio](agentic_systems_studio/README.md).
[Tutorials](../tutorials/README.md) enseña los conceptos; aquí se muestran implementaciones.

Con el SDK instalado, importa estos ejemplos desde la raíz del repositorio. Son material del repositorio, separado del paquete de PyPI.

Los resultados offline, live y de configuración se indican por separado. Un candidato guardado no es una generación de un modelo.

## Aplicaciones

| Ejemplo | Para qué sirve | Validación actual |
|---|---|---|
| [Generar un proyecto](applications/agentic_systems_creator/README.md) | Crear una aplicación con el scaffolder instalado. | Offline ejecutado |
| [Separar afirmaciones y fuentes](applications/research_synthesis/README.md) | Distinguir afirmaciones con una referencia declarada de las que no la tienen. | Offline ejecutado |
| [Comparar opciones](applications/decision_intelligence/README.md) | Aplicar una regla de puntuación explícita. | Offline ejecutado |
| [Clasificar incidentes](applications/incident_response/README.md) | Convertir eventos en una decisión reproducible. | Offline ejecutado |
| [Inspeccionar código](applications/code_review/README.md) | Revisar sintaxis y anotaciones de retorno con AST. | Offline ejecutado |
| [Perfilar datos](applications/data_quality/README.md) | Detectar duplicados y valores ausentes. | Offline ejecutado |
| [Detectar señales en un prompt](applications/prompt_security/README.md) | Marcar instrucciones sospechosas mediante reglas visibles. | Offline ejecutado |
| [Estructurar tareas](applications/meeting_action_center/README.md) | Convertir notas de formato conocido en tareas. | Offline ejecutado |
| [Calcular margen](applications/quantitative_analysis/README.md) | Sumar importes con Decimal. | Offline ejecutado |
| [Enrutar un ticket](applications/customer_support/README.md) | Asignar un equipo mediante una regla explícita. | Offline ejecutado |
| [Resolver un reembolso](applications/refund_resolution/README.md) | Aplicar una política de negocio pequeña y visible. | Offline ejecutado |
| [Agent y System: seis flujos](applications/unified_grammar/README.md) | Aprender secuencia, paralelo y decisiones con la misma interfaz. | Offline ejecutado |
| [Pedidos con la API única 2.1.3](applications/order_fulfillment_213/README.md) | Seven Agents and Skills coordinate validation, parallel checks and explicit business decisions through the single installed SDK API. | Offline ejecutado |
| [Asignar responsables a evidencia](applications/retired_accountability_otc/README.md) | Mostrar un reemplazo público y sintético del experimento retirado. | Offline ejecutado |
| [Cuatro frameworks juntos](applications/framework_interop/README.md) | Coordinar actores de cuatro SDKs y conservar la evidencia de cada Tool. | Live: escenario probado |
| [Studio](applications/studio/README.md) | Conversar, conservar contexto y usar una calculadora con un proveedor y framework explícitos. | Live: escenario probado |
| [Toda la API: de Tool a Eval](applications/api_walkthrough/README.md) | Recorrer la gramática completa y una aprobación de pedidos con resultados observables. | Live: escenario probado |

## Patrones

| Ejemplo | Para qué sirve | Validación actual |
|---|---|---|
| [Calcular una factura](patterns/semantic_calculation/README.md) | Separar cálculo verificable de presentación. | Offline ejecutado |
| [Contar texto](patterns/text_analysis/README.md) | Usar un Tool para análisis básico reproducible. | Offline ejecutado |
| [Respetar el alcance](patterns/scope_clarification/README.md) | Rechazar una operación no declarada. | Offline ejecutado |
| [Evaluar versos guardados](patterns/evidence_grounded_poem/README.md) | Comprobar formato y una cifra en candidatos suministrados. | Offline ejecutado |
| [Conservar un fallo](patterns/controlled_failure/README.md) | Inspeccionar errores, eventos y linaje de una operación fallida. | Offline ejecutado |
| [Conectar MCP y A2A](patterns/strands_protocol_graph/README.md) | Usar servicios locales reales desde Strands. | Offline ejecutado |
| [Acotar una conversación](patterns/bounded_conversation/README.md) | Mantener una ventana de contexto explícita. | Offline ejecutado |
| [Calcular antes de presentar](patterns/two_phase_poem/README.md) | Conservar evidencia de un Tool al formatear una respuesta. | Offline ejecutado |
| [Evaluar y resumir evidencia](patterns/compact_evaluation/README.md) | Evaluar una ejecución guardada y consultar su traza. | Offline ejecutado |
| [Revisar referencias y causalidad](patterns/claim_review/README.md) | Aplicar comprobaciones explícitas sobre afirmaciones estructuradas. | Offline ejecutado |
| [Validar una afirmación tipada](patterns/typed_claim_review/README.md) | Rechazar datos que incumplen el esquema de entrada. | Offline ejecutado |
| [Comprobar un juez optimista](patterns/judge_calibration/README.md) | Combinar expectativas exactas y un juez fixture. | Offline ejecutado |
| [Recorrer un episodio](patterns/long_environment/README.md) | Acumular memoria sin contaminar la siguiente ejecución. | Offline ejecutado |
| [Evaluar sin repetir](patterns/saved_execution_eval/README.md) | Restaurar RunResult y evaluar evidencia guardada. | Offline ejecutado |
| [Bloquear un falso positivo](patterns/fixed_judge_pilot/README.md) | Impedir que un juez fixture apruebe una respuesta incorrecta. | Offline ejecutado |
| [Exigir una respuesta literal](patterns/unambiguous_lm_gate/README.md) | Distinguir coincidencia exacta de parecido textual. | Offline ejecutado |
| [Tutoriales de la API única 2.1.3](patterns/api_213_tutorials/README.md) | Teach every public 2.1.3 symbol through ten offline notebooks using only import agentic_systems. | Offline ejecutado |
| [Tool Contracts — API 2.1.3](patterns/tool_contracts/README.md) | Pydantic input/output schemas, direct/async deterministic Tool and a controlled invalid input. | Offline ejecutado |
| [Portable Skills — API 2.1.3](patterns/portable_skills/README.md) | Exact path loading, relative imports including lazy use, instructions and versioned capability. | Offline ejecutado |
| [Flow Semantics — API 2.1.3](patterns/flow_semantics/README.md) | Six Agent/System × flow forms, each on native and real LangGraph, direct and compiled. | Offline ejecutado |
| [Execution Lifecycle — API 2.1.3](patterns/execution_lifecycle/README.md) | Direct/compiled and async execution, shared action limits and controlled exhaustion. | Offline ejecutado |
| [Results Lineage — API 2.1.3](patterns/results_lineage/README.md) | JSON roundtrip, invariants, execution hierarchy, trace and evidence-derived lineage. | Offline ejecutado |
| [Episode Memory — API 2.1.3](patterns/episode_memory/README.md) | Record-to-record memory, observe/update/stop, deterministic replay and native/LangGraph. | Offline ejecutado |
| [Evaluation Checks — API 2.1.3](patterns/evaluation_checks/README.md) | Exact expected, custom checks, reward metrics, explicit fixture judge and negative control. No semantic model validation. | Offline ejecutado |
| [Model Serving — API 2.1.3](patterns/model_serving/README.md) | Artifact and explicit server configuration/inspection only. Lifecycle exercised separately with fake HTTP/process in SDK tests; no GPU or model started. | Offline ejecutado |
| [Package Install — API 2.1.3](patterns/package_install/README.md) | Installed version/API identity; CLI and generated projects are checked separately in SDK/distribution evidence. | Offline ejecutado |
| [Agent Contracts — API 2.1.3](patterns/agent_contracts/README.md) | Required/allowed Tools, actor budget and portable JSON Schema positive/negative on four Python Runtime frameworks. | Offline ejecutado |

## Integraciones y contratos

| Ejemplo | Para qué sirve | Validación actual |
|---|---|---|
| [Comparar run y compile](validation/api_contract_lab/README.md) | Comprobar que preparar una unidad conserva su ejecución. | Offline ejecutado |
| [Ejecutar cuatro frameworks](validation/provider_framework_conformance/README.md) | Usar los cuatro SDKs con Python determinista. | Offline ejecutado |
| [Preparar vLLM/Colab](validation/vllm_colab/README.md) | Inspeccionar la configuración antes de conectarse a una GPU. | Configuración; entorno pendiente |
| [Preparar AWS IAM](validation/aws_iam/README.md) | Declarar Bedrock sin una API key embebida. | Configuración; entorno pendiente |
| [Preparar ADA IAM](validation/ada_iam/README.md) | Preparar el mismo contrato para un workload empresarial. | Configuración; entorno pendiente |

[Resultados y límites de esta campaña](../revisions/2.1.3/closeout-evidence/REPORT.md).
[RunResult y Lineage Memory de cada ejemplo y notebook](../docs/RUNRESULTS_LINEAGE_213.md): resultados observados y evidencia de cómo se obtuvieron.
[Inventario exhaustivo de notebooks y gramática](../docs/NOTEBOOK_INVENTORY_213.md).
[Catálogo completo y evidencia anterior](catalog.json).

vLLM/Colab, AWS IAM y ADA IAM conservan la ejecución en su entorno como pendiente.

Mantenimiento del catálogo y validadores: [guía de desarrollo](../docs/VALIDATION_213.md).
