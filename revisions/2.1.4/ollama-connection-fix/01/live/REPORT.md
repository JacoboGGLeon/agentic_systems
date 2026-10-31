# Ollama native local/cloud: repetición online aprobada

Campaña nueva autorizada: máximo **USD 2 y 70 solicitudes**, sin publicación.
Se ejecutaron **58 solicitudes**, con **USD 0.493025 reservados conservadoramente**,
no factura. Quedan 12 solicitudes y USD 1.506975. No se reinició ni consumió saldo
de campañas anteriores; sus tres ledgers conservan los hashes iniciales.

Wheel local 2.1.4.dev8: SHA-256
`2fd51f0ade843d9d8d4ef19bfbfd08d5f2d116947a5fc0b2cbed5c4f8dff6b60`.
Se usa la instalación no editable fuera del checkout que pasó 544 pruebas offline.
No se modificaron estos bytes durante la campaña.

| Perfil | Resultado | Solicitudes |
|---|---|---:|
| Piloto Ollama local/native y cloud/native | 2/2 PASS | 2 |
| System local/native → cloud/native, sync | 2/2 PASS | 8 |
| Mismo System, public arun | 2/2 PASS | 8 |
| Notebook financiero original, Python | PASS | 0 |
| Notebook financiero original, mezcla de cuatro proveedores | PASS | 40 |
| Total | Todos los perfiles aprobados | 58 |

No hubo fallos de aceptación ni reintentos manuales. Se conservan todos los
perfiles/attempts; no se borran ni sustituyen los fallos de campañas anteriores.

## Regresión de coexistencia

Local mantiene Qwen3 4B (`qwen3:4b-instruct-2507-q4_K_M`) en
`http://127.0.0.1:11434/v1`; cloud mantiene Gemma4:31b en
`https://ollama.com/v1`. No se descargaron modelos ni se sustituyeron IDs.
El slug cloud es el mismo registrado en la campaña previa.

Se configura el entorno global con la conexión cloud deliberadamente. Local
declara endpoint y clave propios: debe usar su conexión sin modificar ese entorno.
Cada System procesa value=7 y luego value=11 con los mismos objetos compilados.
Los dos actores llaman su Tool y devuelven exactamente los datos de negocio:
`{value:7,local:7,cloud:7}` y `{value:11,local:11,cloud:11}`.

Los checks exigen dos eventos de Tools correctos por ejecución, invariantes,
roundtrip JSON y entorno inalterado. El linaje confirma ambos modelos con actor
native. No se ha cambiado a Strands para hacer pasar la conexión local.

El perfil async usa las APIs públicas System.arun y Agent.arun con nodos async.
No se presenta como una certificación de todos los transportes privados async
ni de paralelismo live; esos caminos tienen regresiones offline independientes.

## Notebook original restaurado

[Notebook ejecutado](../../../../../examples/financial_mixed/03_financial_system_native_local.executed.ipynb).

La aplicación sigue visible paso a paso en sus 13 celdas de código: Tools
Pydantic, Skills, Context, Memory, Graph de Agents/System, decisiones, Environment,
recompensa y Eval. El runner solo prepara entorno, contador, instalación y kernel.

| Capacidad | Runtime/proveedor | Actor observado |
|---|---|---|
| Comisión | OpenAI gpt-4.1-mini | native |
| Auditoría | Bedrock Qwen3-32B | Strands |
| Verificación local | Ollama local Qwen3 4B | **native** |
| Verificación final | Ollama cloud Gemma4:31b | OpenAI Agents |

Respecto a la versión que usaba Strands/local como workaround, solo se restaura
local_framework=native. Se mantienen modelos, endpoints, entradas, Tools y
oráculos. Python y mixed ejecutan el mismo hash de código:
`dd641c06046ebae0c6b9fbd821f8248cbffbf791171e7e9dc64cdedcfef6766e`.

- SINGLE/15000: fee=150, review, pending_review.
- PAY-001/5000: fee=50, approve, approved.
- Mismo pago repetido: review_duplicate, pending_review por Memory.
- Environment: processed=2, approved=1, reward=1.
- Eval: dos casos aprobados con Memory exterior intacta.

Se comparan datos de negocio y resúmenes, no IDs ni tiempos de ejecución.
Se conservan 20 Context recibidos por perfil, RunResults completos, human_results,
linaje y Memory antes/después de Eval. El state no contiene las trazas completas.
No se transfieren fondos; los cálculos y las reglas son deterministas.

## Evidencia y controles

- `plan.json` y `frozen-plan.json`: autorización, rutas, modelos, límites, hashes
  del wheel, notebook y workers. `verify.py` comprueba esos hashes al cerrar.
- `results/pilots.json`, `sync.json`, `async.json`: todos los intentos y resultados.
- Carpetas `*-python/` y `*-mixed/`: notebook ejecutado, result.json y evidence.json.
- `campaign-budget.json`: reserva persistente previa a cada envío HTTP/Botocore,
  incluyendo fallos/reintentos si los hubiera; no se descuentan reservas.
- Hooks activos hasta que salen los procesos y se cierra el kernel. Los saldos
  finales se leen después de esa salida, no solo al terminar la función.
- `summary.json`: comparación de negocio y actores efectivamente observados.
- `historical-ledgers.json`: hashes sin cambios de campañas previas.
- `historical-docs/`: documentos anteriores a esta actualización.
- `manifest.json`: hashes de la nueva evidencia; escaneo de claves configuradas
  en archivos y notebooks satisfactorio, sin imprimirlas.

La reserva usa las mismas tarifas conservadoras del perfil anterior (sin
descuentos y con margen), registradas por ruta. No es un cálculo de factura.
El contador se detiene al primer límite; no se solicitó ni utilizó más presupuesto.

## Qué se cierra y qué no

La regresión de conexión Ollama native queda validada offline y online para
estos casos y estos bytes. El notebook financiero original también queda repetido.
Esto no transfiere toda la aceptación live histórica al nuevo wheel ni certifica
la matriz completa del release. amount:null en Bedrock/Qwen, vLLM GPU, IAM/ADA,
UI completa de Studio y protocolos MCP/A2A permanecen fuera de esta campaña.
No se publicó en PyPI/GitHub ni se ejecutó CI remota.
