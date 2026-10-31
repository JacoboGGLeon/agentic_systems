# Contratos y aprendizaje explícito · 2.1.4.dev5

Candidata local sin publicar. LangGraph orquesta; runtime y scheduler conservan el control del actor. Pydantic valida configuración y estados. Se eliminaron imports de constructores ocultos en la enseñanza, sin añadir vocabulario raíz.

Wheel SHA-256: `0e8e84221c8caee96b7a9d14f5dc056c62e42a0b651a55bf54e7499d6c865dec`. [Wheel](builds/02/agentic_systems-2.1.4.dev5-py3-none-any.whl) · [sdist](builds/02/agentic_systems-2.1.4.dev5.tar.gz) · [Hashes](builds/02/hashes.json).

Offline: **299 pruebas**, **27/27 notebooks**, **54/54 entrypoints** y **1 perfil MCP/A2A local sin LM**. [JUnit](offline-junit.xml) · [Ejemplos](examples-offline.json) · [Visibilidad](visibility-after.json).

Vocabulario propio ejercitado: **17/17**. La cifra no acredita cada parámetro ni todas las rutas.

## Online: resultados de cada escenario

Todos se vinculan al mismo wheel. Los primeros fallos de autenticación Bedrock y todos los intentos permanecen en el [resumen](summary.json). La tabla usa el intento más reciente del mismo caso/ruta/actor; no sustituye un caso por otro.

| Escenario | Ruta | Actor | Resultado |
| --- | --- | --- | --- |
| provider-notebook | openai-runtime | native | PASS |
| provider-notebook | openai-runtime | openai-agents | PASS |
| provider-notebook | openai-runtime | strands | PASS |
| provider-notebook | bedrock-runtime | native | PASS |
| provider-notebook | bedrock-runtime | openai-agents | PASS |
| provider-notebook | bedrock-runtime | strands | PASS |
| provider-notebook | ollama-gpu | native | PASS |
| provider-notebook | ollama-gpu | openai-agents | PASS |
| provider-notebook | ollama-gpu | strands | PASS |
| provider-notebook | ollama-cloud | native | PASS |
| provider-notebook | ollama-cloud | openai-agents | PASS |
| provider-notebook | ollama-cloud | strands | PASS |
| handoff-notebook | openai-runtime | openai-agents | PASS |
| strands-mcp | openai-runtime | strands | PASS |
| strands-a2a | openai-runtime | strands | PASS |
| strands-mcp | ollama-gpu | strands | PASS |
| strands-a2a | ollama-gpu | strands | PASS |
| strands-mcp | ollama-cloud | strands | PASS |
| strands-a2a | ollama-cloud | strands | PASS |
| refund-pause-resume | openai-runtime | native | PASS |
| studio-controller | openai-runtime | native | PASS |
| refund-pause-resume | openai-runtime | openai-agents | PASS |
| studio-controller | openai-runtime | openai-agents | PASS |
| refund-pause-resume | openai-runtime | strands | PASS |
| studio-controller | openai-runtime | strands | PASS |
| refund-pause-resume | ollama-gpu | native | PASS |
| studio-controller | ollama-gpu | native | PASS |
| refund-pause-resume | ollama-gpu | openai-agents | PASS |
| studio-controller | ollama-gpu | openai-agents | PASS |
| refund-pause-resume | ollama-gpu | strands | PASS |
| studio-controller | ollama-gpu | strands | PASS |
| refund-pause-resume | ollama-cloud | native | PASS |
| studio-controller | ollama-cloud | native | PASS |
| refund-pause-resume | ollama-cloud | openai-agents | PASS |
| studio-controller | ollama-cloud | openai-agents | PASS |
| refund-pause-resume | ollama-cloud | strands | PASS |
| studio-controller | ollama-cloud | strands | PASS |
| business:code_review | openai-runtime | native | PASS |
| business:customer_support | ollama-gpu | openai-agents | PASS |
| business:data_quality | ollama-cloud | strands | PASS |
| business:decision_intelligence | openai-runtime | openai-agents | PASS |
| business:incident_response | ollama-gpu | strands | PASS |
| business:meeting_action_center | ollama-cloud | native | PASS |
| business:prompt_security | openai-runtime | strands | PASS |
| business:quantitative_analysis | ollama-gpu | native | PASS |
| business:refund_resolution | ollama-cloud | openai-agents | PASS |
| business:research_synthesis | openai-runtime | native | PASS |
| business:retired_accountability_otc | ollama-gpu | openai-agents | PASS |
| business:claim_review | ollama-cloud | strands | PASS |
| business:scope_clarification | openai-runtime | openai-agents | PASS |
| business:semantic_calculation | ollama-gpu | strands | PASS |
| business:text_analysis | ollama-cloud | native | PASS |
| three-framework-interop | openai-runtime | native+openai-agents+strands | PASS |
| three-framework-interop | ollama-gpu | native+openai-agents+strands | PASS |
| three-framework-interop | ollama-cloud | native+openai-agents+strands | FAIL |
| strands-mcp | bedrock-runtime | strands | PASS |
| strands-a2a | bedrock-runtime | strands | PASS |
| refund-pause-resume | bedrock-runtime | native | PASS |
| studio-controller | bedrock-runtime | native | PENDIENTE (no ejecutado) |
| refund-pause-resume | bedrock-runtime | openai-agents | PASS |
| studio-controller | bedrock-runtime | openai-agents | PENDIENTE (no ejecutado) |
| refund-pause-resume | bedrock-runtime | strands | PASS |
| studio-controller | bedrock-runtime | strands | PENDIENTE (no ejecutado) |
| mandatory-null | bedrock-runtime | native | FAIL |
| mandatory-null | bedrock-runtime | openai-agents | FAIL |
| mandatory-null | bedrock-runtime | strands | FAIL |

Consumo: **148/150 solicitudes**, **USD 0.875040/5 reservados**. Reserva conservadora, no factura. [Contador](campaign-budget.json). La campaña anterior no se reinició ni modificó.

## Correcciones y límites

Build 01 queda conservado como intento anterior. Se corrigió en build 02 la proyección Strands que perdía campos de negocio cuando una Tool devolvía text. Tres regresiones con SDKs reales/Python verifican text, answer, evidence, nulos y un ok de negocio. Se repitieron pruebas sobre los nuevos bytes; la evidencia build 01 no los certifica.

El primer ejemplo conversacional tenía un esquema history abierto incompatible con Tools estrictas: se declaró Message con Pydantic. El ejemplo de controles tenía deadlines de 2/5 segundos insuficientes para imports en kernel frío; ahora usa 30/60. Las pruebas específicas de timeout/reintento conservan sus límites pequeños y sus negativos. Los intentos originales permanecen en attempts/ y notebook-runs/.

Las 15 pruebas de negocio online son proyecciones de sus Tools con entradas/oráculos exactos y asignación rotativa; no son todas las combinaciones ni una ejecución LM de todos los grafos originales. Los grafos deterministas completos están ejecutados offline. Studio online prueba controlador, historial y calculadora, no todos los recorridos de UI.

vLLM está aplazado por decisión del usuario. AWS IAM y ADA IAM, persistencia durable, recuperación tras reinicio, API RL completa y streaming público no quedan certificados. Un fallo obligatorio de negocio sigue bloqueando aceptación; un PASS básico no lo resuelve. CI Python 3.10–3.14 y promoción de artefactos estables siguen pendientes.

[Runtime/scheduler](../../../docs/RUNTIME_SCHEDULER_214.md) · [System/harness](../../../docs/SYSTEM_HARNESS_214.md) · [Ruta de aprendizaje](../../../docs/LEARNING_PATH_214.md) · [Inventario](../../../docs/NOTEBOOK_INVENTORY_214.md) · [RunResults/Memory/linaje](../../../docs/RUNRESULTS_LINEAGE_214.md).

## Repetición Bedrock posterior

[Formato, piloto y resultados](bedrock-recheck.md): autenticación recuperada; matriz básica, reembolso y MCP/A2A aprobados. El nulo obligatorio falla en los tres actores. Studio/Bedrock queda pendiente sin iniciar por saldo. Consumo nuevo: 19/21; total: 148/150 solicitudes, USD 0.875040 reservados. No se publicó.
