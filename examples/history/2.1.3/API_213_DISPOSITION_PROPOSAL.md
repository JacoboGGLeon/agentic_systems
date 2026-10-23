# API 2.1.3: inventario y propuesta de una sola gramática

Fecha: 2026-10-22. **Propuesta de diseño; no aplicada al SDK. Sin inferencia.**

La referencia del comportamiento existente sigue siendo el wheel candidato
`bb6c92e30ee3a3abe2d2c7a613106a8f3d0ec77773fce2ae4ead47df36f6610a`.
El árbol raíz aún corresponde al baseline 2.1.2. Ninguno se modifica con este
inventario. Los artefactos y resultados previos conservan su alcance original.

## Qué se inventarió

El [inventario legible](api_inventory_213/INVENTORY.md), el
[CSV por entrada, miembro y parámetro](api_inventory_213/inventory.csv) y el
[JSON con procedencia y cobertura estática](api_inventory_213/inventory.json)
enumeran 18 exports raíz, constructores, métodos propios y heredados del
proyecto, propiedades, campos, parámetros posicionales/keyword, valores por
defecto, anotaciones, tipos retornados y esquemas auxiliares. También enumeran
los símbolos de submódulos incluidos en el wheel y cruzan los 89 exports
estables del baseline 2.1.2. La herencia de Pydantic se registra aparte.

Son **3.270 filas de inventario**, incluidas 1.813 filas de parámetros: no son
3.270 operaciones públicas. Las filas mezclan superficie raíz, objetos
alcanzables y candidatos a implementación privada. Hay 94 módulos de librería
analizados; las plantillas del scaffolder se excluyen del inventario de SDK.

Se usó codebase-memory para localizar los tipos y contrastar su índice. Su
índice corresponde al baseline; el AST del wheel congelado decide qué existe
en la candidata. El auditor no importa Agentic Systems ni ejecuta callbacks,
proveedores, notebooks, loaders de Skills o servidores. Los métodos de
Pydantic se inspeccionan sin crear modelos. Los mapas JSON abiertos y las
opciones de SDK externos no equivalen a una lista finita de claves soportadas
por esta librería; esas fronteras quedan señaladas explícitamente.

## Criterio de conservación

Conservar una capacidad cuando tiene una responsabilidad distinta. Eliminar
otra ortografía o constructor para la misma responsabilidad. Hacer privados
los adaptadores, validadores, mutaciones del ejecutor y conversiones internas.
No trasladar silenciosamente una funcionalidad anterior a «fuera de alcance»:
una capacidad sin ruta equivalente debe quedar como brecha de release.

Una sola gramática no significa imponer `run` a un servidor ni `compile` a
una Skill. Significa usar la misma palabra para la misma operación, y una sola
fuente de configuración para cada responsabilidad.

## Decisiones de construcción y parámetros

Las firmas actuales completas están en el inventario. Esta tabla define los
parámetros de la **propuesta**, no una API que ya se pueda ejecutar.

| Entrada única | Conservar / definir | Eliminar o sustituir |
|---|---|---|
| `tool` | Función; `name`, `description`, `input_schema`, `output_schema`, `metadata` | `input_model`, `output_model`, `input`, `output`; `strict=False` y conversión implícita de escalares |
| `skill` | `name`, `description`, `tools`, `instructions`, `version`, `metadata` | `prompts` con claves mágicas; `contracts` y `policy` almacenados sin aplicación; constructor público `Skill` |
| `load_skill` | `path` solamente; devuelve una Skill | `**kwargs` ignorados, identidad `load_skill(existing_skill)`, búsqueda ascendente implícita, `build()` alternativo y `register(system)` |
| `Action` | `name`, `target`, `input` como función opcional de transformación | Targets con protocolo ambiguo; admitir solamente función determinista, Tool o nombre de Tool de una Skill |
| `Agent` | `name`, exactamente uno de `flow` o `runtime`; `skills`, `backend`; en modo runtime: `framework`, `instructions`, `contract`, `policy` | Builders, bind, pipeline, registro implícito y parámetros de modelo silenciosamente ignorados en modo flow |
| `System` | `name`, `flow`, `backend` | `skills` heredado: las capacidades pertenecen a Agents; no otro registro de Tools en el coordinador |
| `Sequence` | `steps`, `name` opcional para trazas | Otra forma de expresar secuencia con plan, builder u operador |
| `Parallel` | `steps`, `join`, `name` opcional | Paralelismo que mezcla estado compartido o junta resultados mediante una política implícita |
| `Graph` | `nodes`, `edges`, `start`, `max_visits`, `name`; destinos fijos o función directa | `Route`, routers auxiliares, wrappers de nodo; inferir conexiones analizando el código de una condición |
| `Environment` | `name`, `unit`, `records`, `max_steps`; preservar el ciclo temporal con la extensión descrita abajo | `AgentStepGraph`, `DynamicAgentRouterGraph`, `PlannedAgentGraph` como otras formas públicas de construirlo |
| `Eval` | `name`, `unit`, `cases`; ampliar con `checks`, `judge`, `rubric` | Otro `Evaluator`, `run_eval`, métodos por framework o un juez oculto |
| `Limits` | `max_actions`, `timeout_s` de toda la ejecución | Usarlo como presupuesto monetario o duplicar en él los turnos internos del actor |
| `runtime` | `provider`, `model`, `region`, `endpoint`, `api_key`, `timeout_s`, `max_retries`, `max_tool_calls`, `max_turns`; añadir `max_tokens`, `backoff_s`, `max_concurrency` | `model_id`, `region_name`, constructor `RuntimeConfig`, `provider`, `scheduler`, selección `auto` y fallback |
| `framework` | `name`, `agent_kwargs`, `run_kwargs`; cuatro nombres exactos | Configuración alternativa con string/dict/constructor de implementación; normalizar silenciosamente aliases |
| `model_artifact` | `model`, `base_model`, `adapter_path`, `tokenizer`, `revision`, `quantization`, `metadata` | Otro constructor público `ModelArtifact`; diferentes nombres en la vista retornada |
| `model_server` | Un `artifact` y los parámetros explícitos de serving de la tabla siguiente | `**configuration` opaco, `spec`, `model`, `backend` alternativos y constructor público `VLLMServer` |
| `RunResult` | Tipo de resultado único; campos y operaciones de lectura definidos abajo | Otro output/response envelope público y mutaciones específicas de un proveedor |
| `__version__` | Identidad exacta de la distribución instalada | Usarlo como evidencia suficiente sin hash del artefacto |

Se conserva la forma actual de los flujos: tuplas de pasos, `nodes`, `edges`,
`start`, funciones de decisión y `END`. Esta propuesta no añade DSL, builders,
operadores de composición ni otro constructor de condiciones.

Un Agent con runtime puede ser un paso del flujo de otro Agent o System. Son
dos modos del mismo constructor, con exclusión explícita. `backend` implementa
un flujo; `framework` implementa el actor. Un backend no nativo sin flujo debe
rechazarse. Ninguna selección exterior modifica a los Agents anidados.

Los cinco proveedores y cuatro frameworks mantienen sus identidades exactas.
No se promete que todos los parámetros opcionales funcionen en cada SDK:
una combinación no soportada debe rechazarse con un error explícito. Bedrock
con `api_key` usa bearer; sin ella usa la cadena IAM documentada. AWS IAM y ADA
IAM necesitan evidencia de sus entornos; no requieren otra API de Agent.

## Métodos: contrato mínimo por objeto

| Objeto | Conservar como interfaz | Hacer interno o retirar |
|---|---|---|
| Tool | `run(input=None)`, `inspect()`; añadir `arun(input=None)` para la misma operación atómica | `run(input_payload, context)`, `info`, `describe`, `check`, acceso mutable a `function`; sin `compile` porque no posee flujo |
| Skill | Datos de identidad y capacidades; `inspect()` | `compose`, `composition`, `available_tools`, `tool`, `prompt`, `info`, `describe`, `check`; una aplicación combina capacidades con `Agent.skills=(a, b)` |
| Agent / System | `run(input=None, *, limits=Limits())`, `arun(...)`, `compile()`, `inspect()` | `pipeline`, `bind`, `invoke`, factories y adaptadores públicos de construcción |
| Preparado de Agent/System | `run`, `arun`, `inspect` con los mismos parámetros | Acceso mutable a `prepared`, ejecutores nativos, registros y contexto |
| Environment / Eval | `run(*, limits=Limits())`, `compile()`; completar `arun` e `inspect` con igual contrato | Inputs posicionales ignorados; otro selector de proveedor/framework/backend |
| Preparado de Environment/Eval | `run`, `arun`, `inspect` | `records_json`, `cases_json`, `unit.prepared` y mutación de la captura |
| Configuración runtime/framework/artefacto | Campos canónicos de solo lectura; `inspect()` sin valores secretos | `coerce`, validadores, `describe`, serializadores alternativos y acceso a otro scheduler editable |
| Servidor | `inspect`, `start`, `health`, `stop`; propiedades `endpoint`, `command` | `server.runtime(...)`, `running()` y `with server` como otro ciclo de inicio; inyección de proceso/reloj/espera pública |
| RunResult | `to_dict()`, `walk()`, `trace(mode='compact')`, `lineage(...)`, `check_invariants()` | `compact_trace`, `normalized` público, `native_result`, `from_bedrock_runtime`, `add_child`, `apply_validation`, `validate(contract)`, `should_retry`, `raise_if_inconsistent` |
| Memoria de linaje retornada | `to_dict`, `explain`, `to_prompt_context` y datos de pasos | Constructors `LineageMemory`, `LineageStep`, `lineage_memory`, `from_result`, `from_run_result`, renderers equivalentes y estimaciones que parecen facturación |
| Endpoint / salud / eventos / incidencias | Campos documentados, datos JSON | Constructores alternativos de implementación, validadores e interfaz heredada de Pydantic como otra API del SDK |

`normalized()` **no es un alias exacto** de `to_dict()`: genera otro esquema.
Se propone conservar esa proyección internamente donde la necesitan trazas y
linaje, y publicar un solo esquema estable de intercambio mediante `to_dict`.
La invariantes se verifican automáticamente en los límites de ejecución;
`check_invariants()` sigue disponible para auditar resultados importados.
Los errores de construcción se comunican mediante excepciones; los fallos de
ejecución y evaluación, mediante `RunResult.ok/errors` y su evidencia.

No basta con ocultar nombres en `__all__`. Los submódulos que siguen ofreciendo
constructores anteriores deben convertirse en implementación privada. Los tipos
retornados no deben volver a publicar coerciones, aliases ni métodos heredados
como contrato soportado. No hace falta duplicar el motor ni añadir una fachada
de compatibilidad; sí revisar las clases y rutas de importación efectivas.

## Contratos, políticas y payloads

| Superficie | Única representación propuesta |
|---|---|
| `Agent.contract` | Diccionario cerrado: `tool_expectation`, `completion`, `failure_policy`, `expected_output`, `expected_tool_outputs`; añadir `output_schema` solo tras implementar y probar structured output |
| `tool_expectation` | Diccionario: `all_of`, `any_of`, `allowed`, `forbidden`, `min_count`; `forbidden` es nuevo. Eliminar `exactly` como sugar de `all_of + allowed`, listas/coerciones y helpers `expect` |
| `completion` | Strings exactos `default`, `when_required_tools_satisfied`, `always_finalize`; retirar `when_contract_satisfied` y `required_tools_ok` |
| `failure_policy` | Strings exactos `allow`, `no_unresolved`, `fail_fast`; retirar equivalencias booleanas y el flag que reescribe la política |
| `Agent.policy` | `temperature`, `tool_choice`, `repair`, `max_repairs`, `finalize`, `trace`, `strict`; presupuestos de actor en runtime solamente |
| `RunResult` | `text`, `final`, `data`, `ok`, `messages`, `tool_events`, `raw_responses`, `usage`, `engine`, `model`, `mode`, `trace_schema_version`, `validation`, `errors`, `meta`, `execution_id`, `parent_execution_id`, `children` |
| `ToolEvent` | `id`, `name`, `input`, `output`, `ok`, `error`, `duration_ms`, `meta` |
| Incidencia de validación | `code`, `message`, `severity`, `path`, `meta`; conjunto: `ok`, `issues` |
| Caso de Eval | `name` opcional, `input`, `expected`; dentro de expected: `ok` y `data` exactos. Las comprobaciones adicionales van en `checks`, no en aliases de expected |
| Informe de Eval | Totales, passed/failed/pass_rate, casos, expectativas, resultados, incidencias, uso de candidato y juez separado; conservar reproducibilidad sin afirmar determinismo de un LLM |
| Memoria de linaje | `schema_version`, `name`, `question`, `goal`, `answer`, `ok`, `steps`, `usage`, `validation`, `tags`, `metadata`; cada paso conserva identidad, tipo, resumen, fuente y evidencia |

`text` es presentación textual, `final` es presentación estructurada y `data`
es salida de cómputo. No se fusionan por parecer similares. Los datos de uso
deben separar llamadas a modelos de ejecuciones deterministas de Tools: el
contador `usage.requests` de una Tool no acredita una solicitud de inferencia.
Los raw responses deben tener un contrato de serialización y redacción, sin
objetos SDK arbitrarios ni credenciales. Los secretos solo se describen con
indicadores de configuración; no se recuperan desde una vista pública.

`server.command` debe ser una vista redactada. El comando real que usa el
subproceso queda privado; no debe exponer `api_key` en diagnósticos o notebooks.
La vista de endpoint usa `url` y `model`: la conexión se configura con
`runtime(provider='vllm-runtime', endpoint=server.endpoint.url,
model=server.endpoint.model)`. No se añade otro factory de runtime al servidor.

`lineage` debe declarar sus keywords: `name`, `question`, `goal`, `tags`,
`metadata`, `max_tool_rows`. Los nombres y parámetros de presentación retenidos
de `explain`/`to_prompt_context` siguen enumerados en el inventario; no se añade
otra entrada funcional para reconstruir el mismo linaje.

## Serving: expansión de parámetros hoy ocultos en kwargs

`model_server(artifact, *, profile='fast', served_model_name=None,
host='127.0.0.1', port=8000, tool_call_parser='hermes', reasoning_parser=None,
enable_auto_tool_choice=True, api_key='vllm', startup_timeout_s=600.0,
log_path='vllm-server.log', binary='vllm', extra_args=(),
gpu_memory_utilization=None, max_model_len=None, max_num_seqs=None)`.

Son los parámetros efectivos de `vllm_server_spec` en este wheel, no una lista
tomada de otra versión de vLLM. `generation_config` existe en el spec interno
pero no se admite en esa función: no debe anunciarse como keyword del factory.
`extra_args` permite opciones nativas adicionales, pero debe rechazar las que
duplican parámetros gestionados. `profile` solo aporta defaults; un valor
explícito de GPU/contexto/concurrencia tiene precedencia documentada.

## Capacidades anteriores que no podemos dar por migradas

| Capacidad | Situación actual | Propuesta y criterio de cierre |
|---|---|---|
| Evaluación semántica, rúbrica y hallazgos | Motor anterior presente; `Eval` nuevo solo compara ok/data | Conservar en el mismo `Eval`: `checks=()`, `judge=None`, `rubric=None`. No otro Evaluator. Juez como Agent existente; ver contrato abajo |
| Memoria de episodio que condiciona el siguiente paso, parada y reward | La nueva Environment conserva historia y contador processed; entrega registros independientes | Preservar memoria real con `memory=None`, `observe=None`, `update=None`, `stop=None` en el mismo Environment. Reward se calcula con un check de Eval sobre episodios. No anunciar equivalencia con Gym ni estado interactivo hasta probarlo |
| Evaluar un episodio completo | `Eval` nuevo recibe Agent/System, no Environment | Admitir Environment como unit mediante el mismo protocolo de ejecución; casos identifican records y memoria inicial, sin otro evaluador |
| Structured output de modelos | Había OutputSchema/output_schema y proyecciones; no hay ruta canónica nueva que pruebe equivalencia | Mantener como brecha explícita. Preferir `Agent.contract.output_schema` (propuesto) con validación portable; no retirar el comportamiento interno antes de la regresión correspondiente |
| Delegación y varios Agents | Composición determinista cubierta; adaptadores anteriores tienen detalles adicionales | System/Graph para coordinación portable. Handoffs/sesiones/guardrails/hooks/MCP/A2A se conservan como opciones identificadas del SDK cuando se soporten, sin presentarlas como capacidades portables ya migradas |
| ToolSet y composición de Skills con replace/keep | Motor de composición existente; registro nuevo falla ante identidades conflictivas | Mantener error explícito en conflictos. Selección/reemplazo se hace en la declaración de la aplicación; no conservar otras constructors/políticas de merge en el núcleo |
| Compatibilidad y diagnóstico | CLI doctor informa instalaciones, no ejecución real | Mantener datos del registry como implementación y producir informes de validación versionados; no convertir «instalado» en «certificado» |
| AWS/ADA credential helpers y Studio | Referencias anteriores y trabajo empresarial independiente | Fuera del núcleo de gramática. Instrucciones por entorno y futuras aplicaciones; ningún extra ADA ni wallet implícitos |

Las ampliaciones anteriores son diseño pendiente, no kwargs aceptados hoy.
Para Environment: `observe(record, memory) -> input`,
`update(memory, record, result) -> memory`, `stop(memory, result) -> bool`.
Sin callbacks, el registro sigue siendo el input y no hay memoria inyectada.
Cada `run` comienza un episodio nuevo con copia de la memoria inicial.

Para Eval: `check(result, case) -> {ok, issues}`. Un juez recibe input, expected,
resultado y evidencia de forma explícita. La rúbrica conserva criterios,
threshold, instrucciones, identificación de la Tool de certificación cuando
se exija y exigencia de hallazgos; la aceptación es AND entre
ejecución, comprobaciones deterministas y juez requerido. `judge=None` nunca
crea un proveedor. No aceptar un caso sin expectativa, check ni juez: aprobar
por no comprobar nada no demuestra corrección. La futura evidencia semántica
debe conservar el uso y todos los intentos; no se ejecuta en este trabajo.
No se conserva un bypass público `deterministic_authority` que reescriba el
veredicto del juez: una prueba determinista exhaustiva se declara como check
sin juez, con su alcance explícito. Los scores originales permanecen en evidencia.

## Orden de implementación propuesto

1. Congelar el inventario y cerrar estas decisiones. Las capacidades nuevas
   anteriores necesitan contrato y regresión antes de retirar su ruta antigua.
2. Quitar aliases, kwargs ignorados, coerciones públicas y submódulos alternativos;
   definir un esquema cerrado por diccionario. Cambiar parámetros internos y
   públicos a la vez, sin shim de compatibilidad.
3. Completar simetría run/arun/compile/inspect de los propietarios y capturas,
   separar límites de flujo/actor y validar parámetros por modo/proveedor.
4. Conservar o declarar explícitamente pendientes las capacidades sin equivalente.
   La revisión no está lista para release mientras se anuncie como migrado algo
   cuya equivalencia solo existe en esta propuesta.
5. Promover fuentes al build raíz; generar tutoriales, ejemplos, CLI, skill y
   Studio desde este contrato. Construir un nuevo wheel: cualquier modificación
   invalida la aceptación del artefacto anterior para esas modificaciones.
6. Ejecutar la [cobertura prevista](API_213_COVERAGE_PLAN.md) primero offline.
   La inferencia y los entornos GPU/IAM/ADA quedan en fases con autorización y
   evidencia separadas. Este inventario no publica ni cambia el runtime.
