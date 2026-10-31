# Auditoría de los cuatro bloqueos — 2.1.4.dev8

## Dictamen

No conviene cerrar el release todavía. Hay defectos demostrados de traducción de políticas, normalización de respuestas y conservación de intentos; Studio añade una brecha de validación semántica y otra de empaquetado. No es correcto atribuir todos estos problemas a Qwen, Ollama o Strands.

Esta auditoría no modifica el SDK, no publica y no realiza inferencia. Usa el wheel dev8 instalado fuera del checkout, respuestas de servicio simuladas y evidencia histórica. vLLM GPU, AWS IAM y ADA IAM quedan fuera de alcance: pendientes de sus entornos, no fallos demostrados.

## Los cuatro problemas originales

| Ruta | Qué sabemos | Qué falta |
|---|---|---|
| Strands + Bedrock, `required` | Bug de Agentic Systems reproducido: la política llega al adaptador, pero sale como `auto`. El SDK de Strands sí admite la selección correcta. | Corregir propagación, probar todas las fases y repetir aceptación live. |
| Bedrock/Qwen, `amount:null` | La entrada histórica tenía la clave; el ToolUse recibido no. La validación local rechazó correctamente la omisión. La proyección estricta ya tiene 23 regresiones offline que pasan. | Repetir exactamente el caso online con el wheel final; no está cerrado. |
| Ollama cloud, System mixto | El fallo histórico ocurrió en el primer Agent native, después de ejecutar su Tool; los otros frameworks no llegaron a ejecutarse. Hay varias causas distintas que producen el mismo error local. | Capturar respuesta original y normalizada y repetir el escenario exacto. No hay causa histórica única demostrada. |
| Studio + Bedrock | Faltaba validación live. Además, los replays descubren aceptación de una respuesta aritmética contradictoria y una respuesta vacía mal normalizada en OpenAI Agents. | Corregir contratos de respuesta, reconstruir Studio y probar instalación, controlador y UI. |

## 1. Selección de Tools: el alcance es mayor que Strands

Captura de la petición Bedrock generada por cada adaptador, tanto síncrono como asíncrono:

| Política solicitada | native | OpenAI Agents | Strands |
|---|---|---|---|
| `auto` | `auto` | `auto` | `auto` |
| `required` | `any` | `any` | **`auto`** |
| `none` | **Tool llamada `none`** | **`auto`** | **`auto`** |

El origen de `required` está en `_configure_model` y la entrada a `ContractAwareBedrockModel.stream`: la configuración Bedrock no conserva la elección solicitada. El problema no está en LangGraph ni en la composición del System. La prueba anterior también muestra que, pasando `any` explícitamente al SDK, se serializa correctamente.

Bedrock dispone de las variantes `auto`, `any` y `tool`, sin una variante `none`; para desactivar las Tools de negocio hay que construir una petición sin ellas. [Contrato oficial ToolChoice](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolChoice.html).

También ensayamos una respuesta adversarial simulada que solicita una Tool registrada pese a `none`: los tres adaptadores la ejecutan, en sync y async. Son seis regresiones rojas. El único efecto fue añadir un número a una lista local; no hubo operación externa. Esto demuestra una ausencia de defensa de despacho, no un incidente real del proveedor. `tool_choice` no debe presentarse como una barrera de autorización.

**Corrección necesaria:** traducción común y explícita de selección; guardia antes de ejecutar; conservación de la elección por invocación; liberación de `required` cuando se cumplen las Tools obligatorias; aislamiento entre invocaciones y equivalencia sync/async. Deben respetarse presupuestos de Tools y plazos sin forzar llamadas indefinidamente. Todo cabe dentro de la API actual.

## 2. `amount:null`: no se debe inventar el dato

El caso histórico era:

```json
{"rows":[{"id":1,"amount":10},{"id":1,"amount":null}]}
```

La segunda fila del ToolUse recibido carecía de `amount`. `amount: int | None`, sin default, exige la presencia de la clave y permite su valor nulo. Ausencia, `null`, cero y la cadena `"null"` no son equivalentes. Botocore conserva el nulo cuando existe; no encontramos que el adaptador lo borre. La evidencia antigua no permite separar generación del modelo y procesamiento interno del servicio.

La corrección existente usa `toolSpec.strict` para modelos y esquemas admitidos, sin cambiar el esquema ni añadir valores. `bedrock_strict_tools` conserva restricciones no soportadas y no promete validación del servidor para ellas. Las 23 pruebas específicas cubren proyección, SDKs, nulabilidad y rechazo anterior a efectos.

La validación estructurada de Bedrock admite un subconjunto de JSON Schema, no todas las restricciones de Pydantic. Un default tampoco garantiza que el servicio rellene el dato. [Documentación de structured outputs](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html).

Hay cuatro controles distintos: validación local Pydantic; esquema estricto enviado al servicio; selección obligatoria de Tool; y comprobación de la Tool realmente observada. Ninguno sustituye a los demás. Además, un valor estructuralmente válido puede ser incorrecto: el cierre debe comparar los argumentos exactos con la entrada original.

**Estado:** corrección de petición y regresiones disponibles; aceptación online del caso exacto pendiente. No relajar el contrato, añadir defaults, sustituir nulos por ceros ni cambiar de modelo para declararlo resuelto.

## 3. Ollama: “empty model output” no identifica la causa

En el fallo histórico `three-framework-interop`, la primera Tool native produjo `value=43` y `trail=["native"]`. Después falló ese mismo Agent. No se alcanzaron OpenAI Agents ni Strands. Por tanto, el resultado no demuestra incompatibilidad entre los tres frameworks.

La evidencia antigua no conserva la respuesta cruda necesaria. El bucle native actual es idéntico al del wheel dev5 histórico comparado. Reproducimos, en sync y async, cuatro desenlaces después de una Tool correcta:

| Segunda respuesta simulada | Resultado |
|---|---|
| Texto final válido | Éxito |
| Respuesta realmente vacía | `empty_model_output` |
| Otra llamada estructurada a la Tool, ya sin presupuesto | El mismo `empty_model_output` |
| Texto no vacío interpretado como otra llamada a Tool | El mismo `empty_model_output` |

La Tool no se repite: ese control funciona. Pero el error pierde la distinción entre ausencia de respuesta y llamada rechazada; parte de la información de rechazo desaparece. No podemos reconstruir cuál de esas causas ocurrió históricamente.

Una respuesta adicional después de devolver el resultado de una Tool es normal en un bucle de Tools; no es por sí misma un defecto. [Flujo oficial de Ollama](https://docs.ollama.com/capabilities/tool-calling). Bedrock también realiza síntesis final en esta ruta: no debemos prometer que acaba sin otra llamada.

**Corrección necesaria:** conservar forma original y normalizada, stop reason, llamadas rechazadas y causa específica; distinguir respuesta vacía de intento de Tool no autorizado o sin presupuesto. Si una etapa puede terminar con el resultado determinista, debe hacerlo por un contrato explícito, nunca con texto ficticio que convierta un fallo en éxito.

Los perfiles de Ollama cloud que pasaron recientemente usan otro challenge; no sustituyen este caso mixto histórico.

## 4. Errores adicionales en finalización

### Native Bedrock oculta una excepción de síntesis

`_synthesize_final_answer` captura cualquier excepción y devuelve `None`. Un replay produce: Tool correcta; fallo de síntesis; una tercera petición que permite terminar. Con `max_retries=0` y `repair=False`, el resultado acaba correcto, informa dos peticiones, pero hubo tres despachos simulados. La excepción no aparece en el resultado serializado.

Es una pérdida de evidencia y una continuación implícita. No implica que el contador externo de la campaña esté mal: ese contador intercepta antes del transporte y mantiene los intentos fallidos. Hay que registrar intentos antes de llamar, distinguir éxitos de intentos, preservar causas y propagar cancelaciones/controles. No asignar consumo conocido ficticio a una respuesta que nunca llegó.

### OpenAI Agents convierte vacío en texto JSON

`_output_text` convierte una cadena vacía en el texto `"\"\""`. Entonces el normalizador la trata como contenido no vacío. Con Bedrock y el SDK real sobre servicio simulado, Studio termina con `ok=True` y respuesta `"\"\""`. Native y Strands rechazan correctamente ese perfil.

Debe comprobarse la ausencia antes de renderizar JSON y mantener distintos los valores válidos `0`, `false`, estructuras y campos nulos. El helper es compartido; la demostración actual es Bedrock, no certifica el comportamiento de todos los proveedores. Esta es la séptima regresión roja.

## 5. Studio: contrato semántico y wheel

### El cálculo es correcto; la respuesta puede contradecirlo

En los tres frameworks, la Tool calcula 42, el asistente contesta 999 y Studio devuelve `ok=True`, incluida su validación de respuesta. La instrucción de usar evidencia no basta: se valida contenido/formato, pero no esa consistencia numérica.

Esto pertenece al contrato de la aplicación Studio, no a una suma mal ejecutada por la Tool. `RunResult.ok` significa cumplir los controles declarados, no una garantía universal de verdad. Los controles de Tool obligatoria y propagación de su fallo sí funcionan en los replays.

La respuesta debe vincular el valor y su evidencia mediante datos verificables; para esta aritmética basta un oráculo determinista. Una reparación, si se permite, debe conservar el intento original y consumir presupuesto explícitamente. El actor calculador de Studio usa selección automática actualmente: también debe revisarse junto con la corrección de políticas.

### El laboratorio del wheel está desactualizado

El wheel de Studio difiere del source actual en un archivo Python: `agentic_systems_studio/lab/probes.py`. Conserva `toolkit.Limits` y LangGraph como framework de actor. El source actual ya usa la gramática vigente.

Prueba instalada, sin inferencia: el laboratorio Python del wheel falla con `AttributeError: module 'agentic_systems' has no attribute 'Limits'`; el mismo perfil del source actual pasa. El controlador de conversación coincide con el source: no es correcto extender esta discrepancia a toda la aplicación.

Hay que reconstruir Studio desde el commit revisado y verificar todos sus entrypoints públicos instalados fuera del repositorio. Las pruebas de controlador/widget seleccionadas no cubrían este laboratorio.

## Evidencia y alcance de las pruebas

- SDK dev8 instalado fuera del checkout: SHA-256 `14148af530c14660b888479f6a2eabb4ef1bf74637b7cc3244422f447b547e23`.
- Studio observado: SHA-256 `fa6946066409ed4f56d49011690ea2cff20f46cc324b3732f2e511cea18c89e1`.
- `test_replays.py`, `offline-junit.xml` y `offline.log`: **68 ejecuciones, 61 pasan y 7 fallan; cero inferencias, cero intentos bloqueados por el guard offline**. Incluyen las 23 regresiones existentes de nulabilidad/esquemas estrictos.
- Las siete rojas son seis despachos adversariales bajo `none` y la respuesta vacía de OpenAI Agents. Algunas pruebas verdes documentan expresamente conducta defectuosa, como aceptar 999; esta suite es diagnóstico, no aceptación verde.
- Los JSON `policy-*`, `none-effect-*`, `ollama-*`, `studio-*`, `bedrock-synthesis-failure.json` y `studio-packaging-proof.json` conservan los replays. Los intentos previos están en `attempt-01/` y `attempt-02/`.
- La campaña live anterior conserva 294/300 solicitudes, de ellas 288 inferencias y seis consultas de metadatos; reserva conservadora USD 2.837193, no factura. **Quedan seis solicitudes; esta auditoría no consume ninguna.** Los hashes de ambos ledgers se contrastan con `baseline.json`.
- La matriz live anterior pasó 9/12 con `auto`; el seguimiento `required` pasó native y OpenAI Agents sobre Bedrock. Son 11/12 bajo configuraciones documentadas distintas, no una matriz uniforme aprobada.
- Los 469 tests anteriores y la cobertura del núcleo no equivalen a cobertura total: el porcentaje excluye `_engine` y templates. Los nuevos casos deben entrar en la suite canónica antes de aceptar los bytes corregidos.

## Orden de cierre propuesto

1. Corregir traducción y despacho de políticas, normalización de vacío y conservación de errores/intententos. Mantener la gramática; no introducir constructores ni fallbacks silenciosos.
2. Añadir regresiones canónicas sync/async: tres frameworks, tres selecciones, fases antes/después de Tool, agotamiento, reutilización/caché y llamada adversarial bajo `none`. Probar valores vacíos frente a `0`/`false`, nulabilidad exacta y efectos no repetidos.
3. Corregir el contrato de Studio y su paquete: cálculo correcto/contradictorio, Tool ausente, vacío, historial sin reejecución, errores y todos los entrypoints Python instalados. Completar UI/streaming y controles de presupuesto.
4. Construir artefactos nuevos, verificar payloads/hashes y repetir offline fuera del checkout. La aceptación del wheel anterior no se transfiere.
5. Solo entonces repetir servicios reales con modelos, casos y oráculos congelados; conservar fallos e intentos. No publicar hasta cerrar estos bloqueos.

### Presupuesto de una validación posterior — propuesta, no ejecución

Una campaña focalizada tendría aproximadamente 45 solicitudes nominales: challenge Strands/Bedrock 20, nulabilidad tres frameworks 6, System mixto Ollama 6, Studio Bedrock 9 y cuatro pilotos. Una reserva de **60 solicitudes** deja margen limitado para variación. No constituye aceptación completa de un wheel nuevo.

Para aceptación más amplia: 12 composiciones ×20 =240; 12 pilotos; interop en cuatro rutas ≈24; nulabilidad 6 y Studio Bedrock 9: **291 nominales**. Propondría hasta **350 solicitudes y USD 10** como campaña nueva, con reserva por despacho y parada al primer tope. La cifra monetaria debe recalcularse con modelos/precios y límites de salida antes de ejecutar. No está autorizada por este informe. Las seis solicitudes actuales son insuficientes para cerrar ambos alcances.

## Referencias de implementación

Revisar `_contracts._Policy`; `integrations/adapters/strands.py` (`_configure_model`, `ContractAwareBedrockModel.stream`); `providers/bedrock/converse.py` (`_map_tool_choice`); `integrations/adapters/bedrock_openai.py` (`_tool_choice`); `providers/bedrock/schema.py`; `providers/openai_runtime.py` (`_run_chat_loop`, `_finalize_run_result`); `providers/bedrock/direct.py` (`_synthesize_final_answer`); `integrations/adapters/openai_agents.py` (`_output_text`, `_normalize_result`), y Studio `conversation.py` y `lab/probes.py`.

La evidencia histórica de nulabilidad está en `revisions/2.1.4/contracts-dev5/bedrock-null-fix/`; la del System mixto en `contracts-dev5/online/20261027T040807454463-interop/results.json`; y la matriz actual en `grammar-dev8/live-matrix/01/`. Este informe distingue expresamente esos hechos live de los nuevos replays simulados.
