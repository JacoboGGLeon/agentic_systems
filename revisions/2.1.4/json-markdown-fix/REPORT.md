# Bedrock: JSON en Markdown corregido · 2.1.4.dev3

**Resultado: las dos combinaciones solicitadas pasan. Sin publicación.**

| Combinación | Modelo y autenticación | Respuesta real | Resultado |
| --- | --- | --- | --- |
| Bedrock + OpenAI Agents | qwen.qwen3-32b-v1:0, API key/bearer, us-east-2 | JSON dentro de Markdown | PASS, 120 MXN, approved |
| Bedrock + Strands | El mismo modelo, API key/bearer, us-east-2 | JSON dentro de Markdown | PASS, 120 MXN, approved |

Orquestación exclusivamente LangGraph. Mismo caso, instrucciones, modelo y
parámetros de generación de la prueba anterior; no hubo cambio de proveedor,
reintentos, pilotos ni evaluadores LM. Cada celda usó una solicitud. Ambas
conservaron el texto Markdown original y completaron pausa/reanudación sin
volver a consultar el modelo. Eval determinista comprobó el resultado real
capturado; también pasaron los invariantes de RunResult y linaje.

## Qué se corrigió

Los adaptadores usaban json.loads directamente sobre todo el texto. Ante un
bloque Markdown conservaban el resultado como `{"text": ...}`, que incumplía
el esquema de negocio. Una función común ahora decodifica un documento JSON
completo, opcionalmente envuelto en un único bloque `json` o sin etiqueta.
También se usa en el límite de contratos para mantener el criterio uniforme.

El cambio elimina formato, no repara datos: no extrae objetos entre prosa,
no elige entre bloques múltiples, no completa documentos truncados y no acepta
otra etiqueta de lenguaje. Las salidas estructuradas que ya son diccionarios
siguen siendo autoritativas. JSON Schema se comprueba después, con los mismos
campos requeridos, tipos y prohibición de propiedades adicionales. El texto y
las respuestas originales se conservan como evidencia.

## Regresiones offline

**120 pruebas aprobadas: 84 anteriores y 36 nuevas**, primero sobre fuente y
después sobre el wheel instalado sin modo editable. Guard offline con cero
intentos de conexión/proceso de aplicación; cero inferencias reales.

Las nuevas pruebas cubren:

- Las dos respuestas Qwen fallidas originales, reproducidas a través de los
  SDK reales y un transporte Bedrock simulado. Antes fallaban ambas; después
  alcanzan pausa, reanudan y producen 120 MXN con una sola llamada simulada.
- JSON puro, bloques json/sin etiqueta, mayúsculas, espacios y CRLF.
- Rechazo de prosa alrededor, bloques múltiples, cierre ausente, etiqueta
  incorrecta, JSON inválido, documentos concatenados y esquema incumplido.
- Conservación de datos estructurados autoritativos, texto original,
  respuestas crudas, contador de inferencias y linaje serializable.

Ruff y git diff --check satisfactorios. JUnit contiene el resultado del wheel
instalado. Las advertencias de deprecación de dependencias no son fallos.

## Artefacto y alcance de aceptación

Wheel nuevo: `candidate/agentic_systems-2.1.4.dev3-py3-none-any.whl`.

SHA-256: `83cf3dca623e57d335b02136e70e9fe13dc5dd0ffbc0cc633b8cdcbda430aab9`.

Wheel y sdist se construyeron en una carpeta nueva. Se contrastaron todos los
bytes del paquete con la fuente y de la instalación con el wheel. El wheel
dev2, sus intentos fallidos y sus informes permanecen intactos. La gramática
pública conserva las mismas 17 entradas; no se añaden flags ni constructores.

Esta evidencia acredita la suite offline y **estas dos celdas live del wheel
dev3**. No transfiere automáticamente la aceptación live dev2 de OpenAI,
native o Ollama al artefacto nuevo. Ollama Cloud/Qwen y vLLM siguen pendientes.
No se declara toda la matriz certificada ni se publica una versión.

## Presupuesto acumulado

| Concepto | Solicitudes | Reserva conservadora USD |
| --- | ---: | ---: |
| Antes de esta repetición | 17 | 0.085441 |
| Esta repetición, incluidos todos los intentos | 2 | 0.025498 |
| Acumulado | 19 de 20 | 0.110939 de 1 |
| Saldo | 1 | 0.889061 |

El contador persistente no se reinició. La repetición añadió un techo propio
de dos transmisiones; los controles permanecieron instalados hasta la salida
del proceso. El snapshot final se guardó después del cierre de trabajadores.
La reserva estima un máximo conservador por bytes/tokens y margen; no es una
factura ni descuenta fallos previos.

## Evidencia

- `regression-before.json` y fixture en tests/v214_graph/fixtures: reproducción
  de los fallos originales, sin inferencia.
- `offline-junit.xml`: las 120 pruebas sobre el wheel instalado.
- `live-plan.json`: caso, ruta, parámetros, SHA del wheel/aplicación/script y
  presupuesto congelados antes de inferencia.
- `live-results.json`: RunResults, resultado de Eval y linaje humano/agente de
  ambas combinaciones, incluidos los textos originales en Markdown.
- `budget-before.json`, `budget-after.json`: contador histórico conservado.
- `artifact.json`, `closeout.json`, `SHA256SUMS.json`: artefactos, alcance y hashes.
