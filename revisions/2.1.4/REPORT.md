# API única y validación · 2.1.4.dev2

Implementada y validada offline, sin publicar. Toda composición usa StateGraph
de LangGraph. Se retiraron Sequence, Parallel, toolkit.Graph, backend y flow.
El scaffolder genera la misma gramática, sin una segunda implementación.

## Resultado medido

- 84 pruebas: cero fallos, errores y skips sobre el wheel no editable.
- Dos notebooks desde kernels Jupyter nuevos: 1 y 16 celdas de código.
- Guard de aplicación offline: cero intentos bloqueados observados y cero
  llamadas reales a modelos.
- Ruff sobre toda la distribución activa, tests, ejemplos y scripts; diff limpio.
- Tres implementaciones de actor con Python: native, OpenAI Agents y Strands.
  El orquestador es LangGraph para las tres. Los SDK conservan su bucle interno.
- Pruebas de barreras, reducers, ciclos, Command, nodos asíncronos, Context en
  Tools y Runtime, memoria, pausa/reanudación y proyecto generado por el CLI.
- Evidencia grande conservada fuera de todos los canales de checkpoint y
  ventana de 32 IDs tras 80 visitas; linaje de predecesores sin contaminación
  entre ramas concurrentes.
- Python 3.14.2; versiones de dependencias y fuentes exactas en validation.json.

## Recursos que faltaban

| Función | Input → proceso → output | Validación |
|---|---|---|
| load_skill | Carpeta pricing → build_skill y Tool quote consulta Context (16%) → 100 produce 116 MXN | Carga y ejecución reales, imports relativos, memoria y limpieza de módulos en fallo |
| model_artifact | Identidad de Qwen/Qwen2.5-0.5B-Instruct → declaración de procedencia → objeto inspeccionable | Configuración; sin descargar ni validar pesos; main es una referencia mutable |
| model_server | Artefacto y perfil custom → comando y endpoint quote-model → conexión vLLM declarada | Comando, endpoint y redacción; start/health/stop con proceso/transporte simulados |

No se inició GPU, vLLM real ni inferencia. El notebook separa el arranque GPU,
no ejecutado, de las celdas offline. load_skill sí ejecuta código Python local:
debe proceder de una fuente conocida. SKILL.md documenta y build_skill declara
la capacidad runtime.

## Context y estado

Context es un snapshot de dominio y fuentes. Se hereda en Agent, System y
Environment; rechaza claves en conflicto. Una Tool recibe `*, context:
toolkit.Context`; un nodo Python usa `runtime: Runtime[toolkit.Context]` y
consulta runtime.context. No se copia el objeto Context al estado del grafo.

data y sources delimitan el universo de trabajo; episodes aporta observaciones
seleccionadas de Memory; lineage aporta hasta ocho resúmenes de predecesores.
Las fuentes no recuperan documentos automáticamente. Los episodios y fallos
no se convierten en verdades automáticas.

El state contiene datos de trabajo y hasta 32 referencias recientes. Los
resultados y eventos completos se conservan en un almacén plano aparte. La
historia de Environment y las filas de Eval apuntan por execution_id; el árbol
RunResult se materializa al finalizar. No se promete tamaño constante de los
datos de negocio ni evidencia infinita: hacen falta Limits y retención.

## Caso integrado

R-17: total 240 MXN, albarán de adaptador y sensor, pero solo adaptador recibido.
Normalizar → clasificar con Python dentro del actor → precio y política en
ramas → barrera → decisión → pausa → aprobar con resume. Output: refund=120,
currency=MXN, missing_units=1, status=approved, fuentes y linaje.

Environment procesa dos pedidos y acumula 240 MXN. Eval comprueba el contrato.
No se presenta Python como comprensión de lenguaje natural ni se acredita un
modelo real con estas pruebas.

## Cobertura y alcance

El notebook principal invoca **17/17 funciones y constructores raíz**. Antes
eran 20; se retiraron tres constructores. Las tres funciones que faltaban ya se
ejercitan. No es cobertura del 100% de ramas, parámetros o infraestructura.

El vocabulario estándar de LangGraph se informa aparte: StateGraph, START,
END, Runtime, add_node, add_edge y add_conditional_edges. TypedDict es de Python.

La evidencia de dev1, incluida su campaña OpenAI de ocho solicitudes y reserva
USD 0.031772, está archivada en iterations/dev1/. No acredita este wheel. No se
añadieron llamadas ni se modificó o reinició el contador anterior.

Faltan validación live de este wheel, vLLM/GPU real, IAM/ADA, MCP/A2A remoto,
persistencia, streaming público y migración de Studio y del catálogo histórico
2.1.3. Cache/retry/error-handler de nodos se rechazan explícitamente hasta
integrarlos con la evidencia. Las continuaciones son locales al proceso;
los efectos previos a pause deben ir en otro nodo o ser idempotentes.

No hay publicación ni CI multiversión remota en esta iteración.

## Artefactos

Wheel: `agentic_systems-2.1.4.dev2-py3-none-any.whl`.
SHA-256: `3e618a64e013967cf654ca87b8283ca3c81ceef7b918805218e238196f638b56`.

- [Notebook principal](../../examples/common_graph/01_common_graph.ipynb).
- [Context/Memory](../../examples/context_memory_lineage/01_context_memory_lineage.ipynb).
- [Cobertura por ejemplo](../../docs/GRAMMAR_COVERAGE_214.md).
- [Gramática](../../docs/GRAMMAR_214.md) y [contratos](../../docs/CONTRACTS_214.md).
- validation.json: wheel, fuentes y dependencias.
- example-results.json: RunResults, memoria, linaje y recursos.
- kernel-notebooks.json y capturas: reproducción y vocabulario desde kernels nuevos.
- [Graph API de LangGraph](https://docs.langchain.com/oss/python/langgraph/graph-api):
  semántica de nodos, aristas, reducers y contexto reutilizada por esta integración.
