# Examples · 2.1.4.dev7

Ejemplos de implementación con `import agentic_systems as toolkit`, ejecución directa y LangGraph. Empieza por [la guía de toda la API](api_walkthrough/01_api_user_guide.ipynb), después [seis flujos](common_graph/01_common_graph.ipynb) y [Context/Memory](context_memory_lineage/01_context_memory_lineage.ipynb).

[Graph, Tools Pydantic y Eval con Memory aislada](checked_composition/01_checked_composition.ipynb)
expone Tools, Skill, Agent con grafo, Agent operador, System, Environment y Eval.
[Lineage y Memory que cambian decisiones](lineage_memory/01_lineage_memory_decisions.ipynb)
muestra dos Agents, dos ejecuciones del mismo pago, Environment, Eval aislada,
los Context completos y tres controles causales. Validación offline adicional
dev7: 18 celdas, ninguna omitida.

[Revisión de todos los examples y propuestas priorizadas](../docs/EXAMPLES_REVIEW_214.md).
[Finanzas](applications/financial_harness/example.py) y
[construcción progresiva](applications/financial_harness/progressive.py) conservan
declaraciones explícitas. [Informe dev7](../revisions/2.1.4/grammar-dev7/REPORT.md).

El catálogo conserva los 34 experimentos históricos adaptados; variantes del
mismo experimento no cuentan como experimentos nuevos. La nueva pasada offline
se identifica por archivo y hash. Las cifras y resultados dev5 son históricos,
no una aceptación live de los nuevos bytes. IAM/ADA/vLLM solo declaran
configuración; MCP/A2A tiene un perfil local separado, sin LM.

| Ejemplo | Propósito | Estado actual |
|---|---|---|
| [Lineage y Memory que cambian decisiones](lineage_memory/01_lineage_memory_decisions.ipynb) | Evidencia entre Agents, duplicados con Memory, episodios de Environment y aislamiento por caso de Eval; Context exactos y human_results. | offline-passed; 18 celdas |
| [Generar un proyecto](applications/agentic_systems_creator/example.py) | Crear una aplicación con el scaffolder instalado. | offline-passed |
| [Separar afirmaciones y fuentes](applications/research_synthesis/example.py) | Distinguir afirmaciones con una referencia declarada de las que no la tienen. | offline-passed |
| [Comparar opciones](applications/decision_intelligence/example.py) | Aplicar una regla de puntuación explícita. | offline-passed |
| [Clasificar incidentes](applications/incident_response/example.py) | Convertir eventos en una decisión reproducible. | offline-passed |
| [Inspeccionar código](applications/code_review/example.py) | Revisar sintaxis y anotaciones de retorno con AST. | offline-passed |
| [Perfilar datos](applications/data_quality/example.py) | Detectar duplicados y valores ausentes. | offline-passed |
| [Detectar señales en un prompt](applications/prompt_security/example.py) | Marcar instrucciones sospechosas mediante reglas visibles. | offline-passed |
| [Estructurar tareas](applications/meeting_action_center/example.py) | Convertir notas de formato conocido en tareas. | offline-passed |
| [Calcular margen](applications/quantitative_analysis/example.py) | Sumar importes con Decimal. | offline-passed |
| [Enrutar un ticket](applications/customer_support/example.py) | Asignar un equipo mediante una regla explícita. | offline-passed |
| [Calcular una factura](patterns/semantic_calculation/example.py) | Separar cálculo verificable de presentación. | offline-passed |
| [Contar texto](patterns/text_analysis/example.py) | Usar un Tool para análisis básico reproducible. | offline-passed |
| [Respetar el alcance](patterns/scope_clarification/example.py) | Rechazar una operación no declarada. | offline-passed |
| [Evaluar versos guardados](patterns/evidence_grounded_poem/example.py) | Comprobar formato y una cifra en candidatos suministrados. | offline-passed |
| [Conservar un fallo](patterns/controlled_failure/example.py) | Inspeccionar errores, eventos y linaje de una operación fallida. | offline-passed |
| [Conectar MCP y A2A](patterns/strands_protocol_graph/example.py) | Usar servicios locales reales desde Strands. | local-protocol-passed; zero-inference-fixture |
| [Acotar una conversación](patterns/bounded_conversation/example.py) | Mantener una ventana de contexto explícita. | offline-passed |
| [Calcular antes de presentar](patterns/two_phase_poem/example.py) | Conservar evidencia de un Tool al formatear una respuesta. | offline-passed |
| [Evaluar y resumir evidencia](patterns/compact_evaluation/example.py) | Evaluar una ejecución guardada y consultar su traza. | offline-passed |
| [Revisar referencias y causalidad](patterns/claim_review/example.py) | Aplicar comprobaciones explícitas sobre afirmaciones estructuradas. | offline-passed |
| [Validar una afirmación tipada](patterns/typed_claim_review/example.py) | Rechazar datos que incumplen el esquema de entrada. | offline-passed |
| [Comprobar un juez optimista](patterns/judge_calibration/example.py) | Combinar expectativas exactas y un juez fixture. | offline-passed |
| [Recorrer un episodio](patterns/long_environment/example.py) | Acumular memoria sin contaminar la siguiente ejecución. | offline-passed |
| [Evaluar sin repetir](patterns/saved_execution_eval/example.py) | Restaurar RunResult y evaluar evidencia guardada. | offline-passed |
| [Comparar run y compile](validation/api_contract_lab/example.py) | Comprobar que preparar una unidad conserva su ejecución. | offline-passed |
| [Ejecutar tres actores](validation/provider_framework_conformance/example.py) | Usar los tres SDKs con Python determinista. | offline-passed |
| [Preparar vLLM/Colab](validation/vllm_colab/example.py) | Inspeccionar la configuración antes de conectarse a una GPU. | configuration-offline-passed; target-live-pending |
| [Preparar AWS IAM](validation/aws_iam/example.py) | Declarar Bedrock sin una API key embebida. | configuration-offline-passed; target-live-pending |
| [Preparar ADA IAM](validation/ada_iam/example.py) | Preparar el mismo contrato para un workload empresarial. | configuration-offline-passed; target-live-pending |
| [Resolver un reembolso](applications/refund_resolution/example.py) | Aplicar una política de negocio pequeña y visible. | offline-passed |
| [Bloquear un falso positivo](patterns/fixed_judge_pilot/example.py) | Impedir que un juez fixture apruebe una respuesta incorrecta. | offline-passed |
| [Exigir una respuesta literal](patterns/unambiguous_lm_gate/example.py) | Distinguir coincidencia exacta de parecido textual. | offline-passed |
| [Agent y System: seis flujos](applications/unified_grammar/example.py) | Aprender secuencia, paralelo y decisiones con la misma interfaz. | offline-passed |
| [Pedidos con siete Agents](order_fulfillment/example.py) | Validación, precio/inventario en paralelo, política y decisiones con siete casos verificables. | offline-passed |
| [Tutorials de la API dev7](../tutorials/README.md) | 22 notebooks organizados por core, providers, frameworks y API; la aceptación original cubre 6 notebooks en examples y lineage_memory añade uno con evidencia separada. | Ver aceptación offline dev7 y validación adicional de lineage_memory |
| [Asignar responsables a evidencia](applications/retired_accountability_otc/example.py) | Mostrar un reemplazo público y sintético del experimento retirado. | offline-passed |
| [Tool Contracts — API 2.1.4.dev7](tool_contracts/example.py) | Pydantic input/output schemas, direct/async deterministic Tool and a controlled invalid input. | offline-passed |
| [Portable Skills — API 2.1.4.dev7](portable_skills/example.py) | Exact path loading, relative imports including lazy use, instructions and versioned capability. | offline-passed |
| [Agent/System con seis grafos](flow_semantics/example.py) | Secuencia, ramas disjuntas y decisiones; solo LangGraph. | offline-passed |
| [Execution Lifecycle — API 2.1.4.dev7](execution_lifecycle/example.py) | Direct/compiled and async execution, shared root deadline and controlled timeout. | offline-passed |
| [Results Lineage — API 2.1.4.dev7](results_lineage/example.py) | JSON roundtrip, invariants, execution hierarchy, trace and evidence-derived lineage. | offline-passed |
| [Estado de episodio y memoria](episode_memory/example.py) | Observe, update, stop, replay e identidad de ejecuciones. | offline-passed |
| [Checks y juez fixture](evaluation_checks/example.py) | Expectativas, checks, métrica de negocio y control negativo; sin juez LM. | offline-passed |
| [Model Serving — API 2.1.4.dev7](model_serving/example.py) | Artifact and explicit server configuration/inspection only. Lifecycle exercised separately with fake HTTP/process in SDK tests; no GPU or model started. | offline-passed |
| [Package Install — API 2.1.4.dev7](package_install/example.py) | Installed version/API identity; CLI and generated projects are checked separately in SDK/distribution evidence. | offline-passed |
| [Agent Contracts — API 2.1.4.dev7](agent_contracts/example.py) | Required/allowed Tools, actor budget and portable JSON Schema positive/negative on three Python-runtime actors. | offline-passed |
| [Tres actores en un System](framework_interop/example.py) | native, OpenAI Agents y Strands coordinados por un StateGraph. | offline-passed |
| [Studio](agentic_systems_studio/example.py) | Grafo conversacional mínimo visible con historial y tres SDKs; controlador/UI completos se prueban por separado. | offline-passed |
| [Toda la API: de Tool a Eval](api_walkthrough/example.py) | Recorrer la gramática completa y una aprobación de pedidos con resultados observables. | offline-passed |
| [Runtime y scheduler](execution_controls/example.py) | Controles Pydantic del actor, plazo raíz compartido y errores antes de efectos. | Ver aceptación offline dev7 |

[Validación histórica dev5](../revisions/2.1.4/contracts-dev5/REPORT.md) ·
[Estado de revisiones](../docs/STATUS_214.md). Los estados de cada entrypoint
se reconcilian con evidencia nueva, conservando los intentos fallidos.
