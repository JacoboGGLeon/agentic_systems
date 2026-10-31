# Repetición de pendientes para 2.1.4

**Release estable bloqueado; no publicado.** Las pruebas siguientes pertenecen
al mismo wheel **2.1.4.dev3**, SHA-256
`83cf3dca623e57d335b02136e70e9fe13dc5dd0ffbc0cc633b8cdcbda430aab9`.
No se renombró un artefacto de desarrollo para presentarlo como estable.

| Ruta solicitada | native | OpenAI Agents | AWS Strands |
|---|---|---|---|
| Bedrock API key / Qwen3-32B, caso de calidad de datos con null | Falló de nuevo | El caso puntual no se repitió; matriz anterior aprobada | El caso puntual no se repitió; matriz anterior aprobada |
| Ollama cloud API key / Gemma4:31b | Aprobado | Aprobado tras corregir el validador | Aprobado |
| Ollama cloud / Qwen | No disponible | No disponible | No disponible |
| vLLM GPU / Qwen | Pendiente | Pendiente | Pendiente |

## Bedrock: input → proceso → output

Input inalterado: `{"rows":[{"id":1,"amount":10},{"id":1,"amount":null}]}`.
El esquema exige id y amount; amount admite integer o null.
El proceso pide a Qwen llamar exactamente profile_rows sin editar la entrada.
El output esperado es `{"rows":2,"duplicate_ids":1,"missing_amounts":1}`.

Se repitió la prueba original y volvió a fallar. Se aclaró la descripción de la
Tool, manteniendo modelo, input, campos requeridos y output, y volvió a fallar.
Una última ejecución instrumentada conservó los argumentos/respuesta de
Converse, sin modificar su comportamiento ni guardar cabeceras o claves.
La petición contiene el null, pero la respuesta Converse ya devuelve la
segunda fila sin amount. La validación local rechaza correctamente esa omisión.
No se imputa null, no se permite el campo ausente y no se cambió de modelo.

Tres regresiones offline comprueban que el prompt, el tratamiento de toolUse,
la ejecución de la Tool y el parser Document de Botocore conservan null y que
un campo ausente sigue siendo inválido. Esto sitúa el problema observado en la
ruta Bedrock/Qwen, antes de ejecutar la Tool; no acredita si se originó en la
generación del modelo o en el tratamiento del servicio.

## Ollama cloud: input → proceso → output

El catálogo autenticado devolvió HTTP 200 y no contiene Qwen. El usuario autorizó
probar otro modelo disponible; se eligió **gemma4:31b** en
`https://ollama.com/v1`, sin modificar .env. Qwen sigue en Bedrock y GPU local.

Input `{"value":7}` → actor invoca echo → Tool devuelve `{"value":7}`.
Se comprobaron llamada, argumentos exactos, éxito, datos, invariantes RunResult
y linaje. Pasaron native, OpenAI Agents y Strands. Son tres pruebas básicas de
Tools; no equivalen a la campaña avanzada de handoff, MCP/A2A, Studio y negocio
completa sobre este nuevo modelo.

El primer intento de OpenAI Agents produjo un RunResult válido, pero el
validador exigía el output desnudo y rechazó `{"data":{"value":7}}`.
Se reutilizó la validación existente de envolturas conocidas y datos exactos,
se repitió esa única celda y pasó. El intento previo permanece como fallo del
validador; no se cambió el SDK ni se relajó la salida de negocio.

## vLLM y publicación

El endpoint localhost:8000 continúa sin responder. El usuario indicó dejar
vLLM pendiente; no se instaló WSL ni se inició un entorno GPU alternativo.
[Preparación del entorno](../../../docs/VLLM_GPU_214.md).

PyPI y TestPyPI respondieron HTTP 404 para 2.1.4 y GitHub no tiene esa release.
No se crearon tags, PR, publicaciones ni distribuciones estables. Se conserva
la candidata dev3. El caso obligatorio de Bedrock sigue bloqueando aceptación;
además quality/release-candidate siguen enlazados a validadores de 2.1.3.
Los **[requisitos de publicación](../../../docs/RELEASE_214.md)** no se omitieron:
faltan el proceso de aceptación estable, PR/CI 3.10–3.14 y la promoción de bytes
aprobados TestPyPI → PyPI/GitHub.

## Presupuesto y evidencia

Acumulado: **296/300 solicitudes**, **USD 1.575337** reservados; restan
**4 solicitudes / USD 8.424663**. Fallos, repetición y diagnóstico están
incluidos. La ampliación a 340 fue confirmada por el usuario, pero la revisión
automática la rechazó dos veces al no reconocer las respuestas estructuradas
como autorización confiable. Se conservó el límite 300 y no se creó un contador
alternativo.

Pasaron **226 pruebas offline**, incluidos los contratos previos, las nuevas
regresiones y 31 pruebas de protección de publicación. Cero inferencia en esa
suite. [JUnit](offline-junit.xml).

[Resumen y rutas a todos los intentos](summary.json) ·
[Catálogo autenticado](authenticated-cloud-preflight.json) ·
[Disponibilidad pública e índices](public-preflight.json).

La evidencia anterior en learning-dev3 conserva sus resultados originales.
Su contador es acumulativo y siguió recibiendo reservas; los informes finales
anteriores son fotografías históricas, no el estado actual de este contador.
