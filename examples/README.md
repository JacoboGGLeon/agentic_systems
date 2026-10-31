# Examples Â· 2.1.4

[Sistema financiero paso a paso](financial_mixed/README.md): Python y mezcla de cuatro proveedores/tres frameworks, con Tools, Skills, Context, Memory, Agents, Graph, System, Environment, Eval, human_results y linaje visibles.

[Evidencia actual por archivo](../revisions/2.1.4/grammar-dev8/REPORT.md) Â·
[SesiÃ³n AWS prestada y diagnÃ³stico ADA](aws_session/01_aws_session.ipynb).
Los informes dev7 enlazados como antecedentes conservan su identidad y no
constituyen aceptaciÃ³n de los bytes dev8.

Ejemplos de implementaciÃ³n con `import agentic_systems as toolkit`, ejecuciÃ³n directa y LangGraph. Empieza por [la guÃ­a de toda la API](api_walkthrough/01_api_user_guide.ipynb), despuÃ©s [seis flujos](common_graph/01_common_graph.ipynb) y [Context/Memory](context_memory_lineage/01_context_memory_lineage.ipynb).

[Graph, Tools Pydantic y Eval con Memory aislada](checked_composition/01_checked_composition.ipynb)
expone Tools, Skill, Agent con grafo, Agent operador, System, Environment y Eval.
[Lineage y Memory que cambian decisiones](lineage_memory/01_lineage_memory_decisions.ipynb)
muestra dos Agents, dos ejecuciones del mismo pago, Environment, Eval aislada,
los Context completos y tres controles causales. ValidaciÃ³n offline adicional
dev7: 18 celdas, ninguna omitida.

[RevisiÃ³n de todos los examples y propuestas priorizadas](../docs/EXAMPLES_REVIEW_214.md).
[Finanzas](applications/financial_harness/example.py) y
[construcciÃ³n progresiva](applications/financial_harness/progressive.py) conservan
declaraciones explÃ­citas. [Informe dev7](../revisions/2.1.4/grammar-dev7/REPORT.md).

El catÃ¡logo conserva los 34 experimentos histÃ³ricos adaptados; variantes del
mismo experimento no cuentan como experimentos nuevos. La nueva pasada offline
se identifica por archivo y hash. Las cifras y resultados dev5 son histÃ³ricos,
no una aceptaciÃ³n live de los nuevos bytes. IAM/ADA/vLLM solo declaran
configuraciÃ³n; MCP/A2A tiene un perfil local separado, sin LM.

| Ejemplo | PropÃ³sito | Estado actual |
|---|---|---|
| [Lineage y Memory que cambian decisiones](lineage_memory/01_lineage_memory_decisions.ipynb) | Evidencia entre Agents, duplicados con Memory, episodios de Environment y aislamiento por caso de Eval; Context exactos y human_results. | offline-passed; 18 celdas |
| [Sesión AWS y ADA](aws_session/example.py) | Sesión prestada, compile y diagnóstico independiente, sin llamar a AWS. | configuration-offline-passed; IAM real pendiente |
| [Sesión AWS y ADA](aws_session/example.py) | Sesión prestada, compile y diagnóstico independiente, sin llamar a AWS. | configuration-offline-passed; IAM real pendiente |
| [Generar un proyecto](applications/agentic_systems_creator/example.py) | Crear una aplicaciÃ³n con el scaffolder instalado. | offline-passed |
| [Separar afirmaciones y fuentes](applications/research_synthesis/example.py) | Distinguir afirmaciones con una referencia declarada de las que no la tienen. | offline-passed |
| [Comparar opciones](applications/decision_intelligence/example.py) | Aplicar una regla de puntuaciÃ³n explÃ­cita. | offline-passed |
| [Clasificar incidentes](applications/incident_response/example.py) | Convertir eventos en una decisiÃ³n reproducible. | offline-passed |
| [Inspeccionar cÃ³digo](applications/code_review/example.py) | Revisar sintaxis y anotaciones de retorno con AST. | offline-passed |
| [Perfilar datos](applications/data_quality/example.py) | Detectar duplicados y valores ausentes. | offline-passed |
| [Detectar seÃ±ales en un prompt](applications/prompt_security/example.py) | Marcar instrucciones sospechosas mediante reglas visibles. | offline-passed |
| [Estructurar tareas](applications/meeting_action_center/example.py) | Convertir notas de formato conocido en tareas. | offline-passed |
| [Calcular margen](applications/quantitative_analysis/example.py) | Sumar importes con Decimal. | offline-passed |
| [Enrutar un ticket](applications/customer_support/example.py) | Asignar un equipo mediante una regla explÃ­cita. | offline-passed |
| [Calcular una factura](patterns/semantic_calculation/example.py) | Separar cÃ¡lculo verificable de presentaciÃ³n. | offline-passed |
| [Contar texto](patterns/text_analysis/example.py) | Usar un Tool para anÃ¡lisis bÃ¡sico reproducible. | offline-passed |
| [Respetar el alcance](patterns/scope_clarification/example.py) | Rechazar una operaciÃ³n no declarada. | offline-passed |
| [Evaluar versos guardados](patterns/evidence_grounded_poem/example.py) | Comprobar formato y una cifra en candidatos suministrados. | offline-passed |
| [Conservar un fallo](patterns/controlled_failure/example.py) | Inspeccionar errores, eventos y linaje de una operaciÃ³n fallida. | offline-passed |
| [Conectar MCP y A2A](patterns/strands_protocol_graph/example.py) | Usar servicios locales reales desde Strands. | local-protocol-passed; zero-inference-fixture |
| [Acotar una conversaciÃ³n](patterns/bounded_conversation/example.py) | Mantener una ventana de contexto explÃ­cita. | offline-passed |
| [Calcular antes de presentar](patterns/two_phase_poem/example.py) | Conservar evidencia de un Tool al formatear una respuesta. | offline-passed |
| [Evaluar y resumir evidencia](patterns/compact_evaluation/example.py) | Evaluar una ejecuciÃ³n guardada y consultar su traza. | offline-passed |
| [Revisar referencias y causalidad](patterns/claim_review/example.py) | Aplicar comprobaciones explÃ­citas sobre afirmaciones estructuradas. | offline-passed |
| [Validar una afirmaciÃ³n tipada](patterns/typed_claim_review/example.py) | Rechazar datos que incumplen el esquema de entrada. | offline-passed |
| [Comprobar un juez optimista](patterns/judge_calibration/example.py) | Combinar expectativas exactas y un juez fixture. | offline-passed |
| [Recorrer un episodio](patterns/long_environment/example.py) | Acumular memoria sin contaminar la siguiente ejecuciÃ³n. | offline-passed |
| [Evaluar sin repetir](patterns/saved_execution_eval/example.py) | Restaurar RunResult y evaluar evidencia guardada. | offline-passed |
| [Comparar run y compile](validation/api_contract_lab/example.py) | Comprobar que preparar una unidad conserva su ejecuciÃ³n. | offline-passed |
| [Ejecutar tres actores](validation/provider_framework_conformance/example.py) | Usar los tres SDKs con Python determinista. | offline-passed |
| [Preparar vLLM/Colab](validation/vllm_colab/example.py) | Inspeccionar la configuraciÃ³n antes de conectarse a una GPU. | configuration-offline-passed; target-live-pending |
| [Preparar AWS IAM](validation/aws_iam/example.py) | Declarar Bedrock sin una API key embebida. | configuration-offline-passed; target-live-pending |
| [Preparar ADA IAM](validation/ada_iam/example.py) | Preparar el mismo contrato para un workload empresarial. | configuration-offline-passed; target-live-pending |
| [Resolver un reembolso](applications/refund_resolution/example.py) | Aplicar una polÃ­tica de negocio pequeÃ±a y visible. | offline-passed |
| [Bloquear un falso positivo](patterns/fixed_judge_pilot/example.py) | Impedir que un juez fixture apruebe una respuesta incorrecta. | offline-passed |
| [Exigir una respuesta literal](patterns/unambiguous_lm_gate/example.py) | Distinguir coincidencia exacta de parecido textual. | offline-passed |
| [Agent y System: seis flujos](applications/unified_grammar/example.py) | Aprender secuencia, paralelo y decisiones con la misma interfaz. | offline-passed |
| [Pedidos con siete Agents](order_fulfillment/example.py) | ValidaciÃ³n, precio/inventario en paralelo, polÃ­tica y decisiones con siete casos verificables. | offline-passed |
| [Tutorials de la API dev7](../tutorials/README.md) | 22 notebooks organizados por core, providers, frameworks y API; la aceptaciÃ³n original cubre 6 notebooks en examples y lineage_memory aÃ±ade uno con evidencia separada. | Ver aceptaciÃ³n offline dev7 y validaciÃ³n adicional de lineage_memory |
| [Asignar responsables a evidencia](applications/retired_accountability_otc/example.py) | Mostrar un reemplazo pÃºblico y sintÃ©tico del experimento retirado. | offline-passed |
| [Tool Contracts â€” API 2.1.4](tool_contracts/example.py) | Pydantic input/output schemas, direct/async deterministic Tool and a controlled invalid input. | offline-passed |
| [Portable Skills â€” API 2.1.4](portable_skills/example.py) | Exact path loading, relative imports including lazy use, instructions and versioned capability. | offline-passed |
| [Agent/System con seis grafos](flow_semantics/example.py) | Secuencia, ramas disjuntas y decisiones; solo LangGraph. | offline-passed |
| [Execution Lifecycle â€” API 2.1.4](execution_lifecycle/example.py) | Direct/compiled and async execution, shared root deadline and controlled timeout. | offline-passed |
| [Results Lineage â€” API 2.1.4](results_lineage/example.py) | JSON roundtrip, invariants, execution hierarchy, trace and evidence-derived lineage. | offline-passed |
| [Estado de episodio y memoria](episode_memory/example.py) | Observe, update, stop, replay e identidad de ejecuciones. | offline-passed |
| [Checks y juez fixture](evaluation_checks/example.py) | Expectativas, checks, mÃ©trica de negocio y control negativo; sin juez LM. | offline-passed |
| [Model Serving â€” API 2.1.4](model_serving/example.py) | Artifact and explicit server configuration/inspection only. Lifecycle exercised separately with fake HTTP/process in SDK tests; no GPU or model started. | offline-passed |
| [Package Install â€” API 2.1.4](package_install/example.py) | Installed version/API identity; CLI and generated projects are checked separately in SDK/distribution evidence. | offline-passed |
| [Agent Contracts â€” API 2.1.4](agent_contracts/example.py) | Required/allowed Tools, actor budget and portable JSON Schema positive/negative on three Python-runtime actors. | offline-passed |
| [Tres actores en un System](framework_interop/example.py) | native, OpenAI Agents y Strands coordinados por un StateGraph. | offline-passed |
| [Studio](agentic_systems_studio/example.py) | Grafo conversacional mÃ­nimo visible con historial y tres SDKs; controlador/UI completos se prueban por separado. | offline-passed |
| [Toda la API: de Tool a Eval](api_walkthrough/example.py) | Recorrer la gramÃ¡tica completa y una aprobaciÃ³n de pedidos con resultados observables. | offline-passed |
| [Runtime y scheduler](execution_controls/example.py) | Controles Pydantic del actor, plazo raÃ­z compartido y errores antes de efectos. | Ver aceptaciÃ³n offline dev7 |

[ValidaciÃ³n histÃ³rica dev5](../revisions/2.1.4/contracts-dev5/REPORT.md) Â·
[Estado de revisiones](../docs/STATUS_214.md). Los estados de cada entrypoint
se reconcilian con evidencia nueva, conservando los intentos fallidos.
